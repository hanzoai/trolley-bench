"""Parallel-answering test: does answering N requests at once speed a local model up without
changing its answers? Run before the v2 panel; its rule decides each tested model's concurrency.

  python3 run/v2/parallel_test.py arm <model> <arm> --concurrency C --port P [--max-load L] -- <server command...>
  python3 run/v2/parallel_test.py compare <model>

`arm` starts the server (its own process group, bound to 127.0.0.1), waits for it, sends the fixed
sample with C requests in flight, stops the server, and writes results/v2/parallel-test/<model>/<arm>.jsonl
and .summary.json. The sample is 24 cells from each of the 10 v2 scenarios that sweep a count
(literal_zero left out), drawn with a fixed seed, so every arm and every model answers the same 240.

`compare` reads every arm against the two sequential arms, seq-a (the reference) and seq-b (the same
setup restarted, which measures the runtime's own run-to-run noise), and applies the rule fixed in
ANALYSIS-PLAN-v2.md. An arm is accepted for the panel when, over the 240 cells and all three questions:
- its mean |difference| from seq-a is at most max(0.002, 2 x seq-b's), and its largest at most
  max(0.01, 2 x seq-b's);
- no cell's choice (above or below 0.5) differs from seq-a unless both answers are within 0.01 of 0.5;
- and it answers the sample at least 1.3 times as fast as seq-a.
The fastest accepted arm is the one the panel uses; with none accepted, the model runs one at a time.
The rule applies only to the model tested: every other model runs one request at a time.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import random
import signal
import statistics as st
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "v2" / "parallel-test"
CELLS = ROOT / "scenarios" / "v2" / "cells-v2.json"
SEED = 20261006
PER_SCENARIO = 24
QUESTIONS = ("pull", "pull_criteria", "stay")


def sample():
    want = (CELLS.parent / "cells-v2.json.sha256").read_text().split()[0]
    raw = CELLS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != want:
        sys.exit("cells-v2.json does not match its committed sha256; run node scenarios/v2/freeze.mjs --check")
    cells = json.loads(raw)["cells"]
    rnd = random.Random(SEED)
    picked = []
    for s in sorted({c["scenario"] for c in cells} - {"literal_zero"}):
        picked += rnd.sample([c for c in cells if c["scenario"] == s], PER_SCENARIO)
    return picked


def post(url, body, timeout=900):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def wait_for_load(max_load):
    while os.getloadavg()[0] > max_load:
        print(f"load {os.getloadavg()[0]:.1f} > {max_load}: waiting", flush=True)
        time.sleep(30)


def arm(a, cmd):
    url = f"http://127.0.0.1:{a.port}/v1/systemone"
    d = OUT / a.model
    d.mkdir(parents=True, exist_ok=True)
    cells = sample()
    wait_for_load(a.max_load)
    log = open(d / f"{a.arm}.server.log", "w")
    srv = subprocess.Popen(cmd, cwd=a.cwd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    t0 = time.time()
    try:
        while True:
            if srv.poll() is not None:
                sys.exit(f"server exited with {srv.returncode}; see {d / (a.arm + '.server.log')}")
            try:
                post(url, {"state": cells[0]["state"], "questions": cells[0]["questions"]})
                break
            except Exception:  # noqa: BLE001 - not up yet
                if time.time() - t0 > 3600:
                    sys.exit("server did not answer within an hour")
                time.sleep(5)
        print(f"[{a.model} {a.arm}] server up after {time.time() - t0:.0f}s; {len(cells)} cells, {a.concurrency} in flight", flush=True)

        def one(c):
            t = time.perf_counter()
            out = post(url, {"state": c["state"], "questions": c["questions"]})
            return c, out, (time.perf_counter() - t) * 1000

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(a.concurrency) as pool:
            results = list(pool.map(one, cells))
        wall = time.perf_counter() - start
        extra = {}
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{a.port}/batches", timeout=10) as r:
                extra["server_batches"] = json.load(r)
        except Exception:  # noqa: BLE001 - only the batching server reports batches
            pass
    finally:
        try:
            os.killpg(srv.pid, signal.SIGTERM)
            srv.wait(timeout=60)
        except Exception:  # noqa: BLE001 - make sure it is gone
            os.killpg(srv.pid, signal.SIGKILL)
    with open(d / f"{a.arm}.jsonl", "w") as fh:
        for c, out, ms in results:
            fh.write(json.dumps({"id": c["id"], "answers": {q: out["answers"][q]["noul"] for q in c["questions"]}, "usage": out.get("usage"), "ms": round(ms, 1)}) + "\n")
    summary = {"model": a.model, "arm": a.arm, "concurrency": a.concurrency, "cells": len(results), "wall_s": round(wall, 2),
               "cells_per_s": round(len(results) / wall, 3), "median_ms": round(st.median(r[2] for r in results), 1),
               "server_command": cmd, "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **extra}
    (d / f"{a.arm}.summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "server_command"}), flush=True)


def load_arm(model, name):
    d = OUT / model
    rows = {json.loads(ln)["id"]: json.loads(ln) for ln in (d / f"{name}.jsonl").read_text().splitlines()}
    return rows, json.loads((d / f"{name}.summary.json").read_text())


def diff(a, b):
    ds, flips, near = [], 0, 0
    for i, ra in a.items():
        for q in QUESTIONS:
            x, y = ra["answers"][q], b[i]["answers"][q]
            ds.append(abs(x - y))
            if (x > .5) != (y > .5):
                if abs(x - .5) <= .01 and abs(y - .5) <= .01:
                    near += 1
                else:
                    flips += 1
    return {"mean_abs_diff": round(st.mean(ds), 5), "max_abs_diff": round(max(ds), 4), "choice_flips": flips, "choice_flips_within_0.01_of_line": near}


def compare(a):
    d = OUT / a.model
    ref, ref_s = load_arm(a.model, "seq-a")
    noise_rows, noise_s = load_arm(a.model, "seq-b")
    noise = diff(ref, noise_rows)
    mean_lim, max_lim = max(0.002, 2 * noise["mean_abs_diff"]), max(0.01, 2 * noise["max_abs_diff"])
    arms = {}
    for f in sorted(d.glob("*.summary.json")):
        name = f.name[: -len(".summary.json")]
        if name in ("seq-a", "seq-b"):
            continue
        rows, s = load_arm(a.model, name)
        dd = diff(ref, rows)
        speed = round(s["cells_per_s"] / ref_s["cells_per_s"], 2)
        ok = dd["mean_abs_diff"] <= mean_lim and dd["max_abs_diff"] <= max_lim and dd["choice_flips"] == 0 and speed >= 1.3
        arms[name] = {"concurrency": s["concurrency"], "speedup": speed, **dd, "accepted": ok}
    accepted = [n for n, v in arms.items() if v["accepted"]]
    best = max(accepted, key=lambda n: arms[n]["speedup"]) if accepted else None
    out = {"model": a.model, "rule": "ANALYSIS-PLAN-v2.md, parallel answering", "sample_cells": len(ref),
           "seq_a_cells_per_s": ref_s["cells_per_s"], "noise_seq_b_vs_seq_a": noise, "limits": {"mean_abs_diff": mean_lim, "max_abs_diff": round(max_lim, 4)},
           "arms": arms, "panel_uses": best or "seq (one request at a time)"}
    (d / "verdict.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "arm":
        split = sys.argv.index("--")
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("model")
        ap.add_argument("arm")
        ap.add_argument("--concurrency", type=int, required=True)
        ap.add_argument("--port", type=int, required=True)
        ap.add_argument("--cwd", default=".")
        ap.add_argument("--max-load", type=float, default=20.0)
        arm(ap.parse_args(sys.argv[1:split]), sys.argv[split + 1:])
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd", choices=["compare"])
        ap.add_argument("model")
        compare(ap.parse_args())


if __name__ == "__main__":
    main()
