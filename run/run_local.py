"""Run the frozen v1 cells against a local decision model, one request at a time.

  python run/run_local.py http --name kev-4b --url http://127.0.0.1:8009/v1/systemone --meta meta.json
  python run/run_local.py laya --name laya --meta meta.json

Rows match run-jev.mjs so one analysis reads both. The runner pauses while the machine's
one-minute load average is above --max-load, because this Mac is shared with other work.
"""
import argparse
import json
import os
import pathlib
import statistics
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"


def laya_engine():
    from laya import Router

    router = Router(preload=False)

    def ask(state, questions):
        # Pin the English checkpoint; the Router would pick it anyway for this text
        out = router.predict(state, questions, model="english")
        return {name: out["answers"][name]["noul"] for name in questions}, out["answers"]

    return ask


def http_engine(url):
    def ask(state, questions):
        body = json.dumps({"state": state, "questions": questions}).encode()
        req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as resp:
            out = json.load(resp)
        return {q: out["answers"][q]["noul"] for q in questions}, out["answers"]

    return ask


def wait_for_load(max_load, log):
    paused = 0.0
    while os.getloadavg()[0] > max_load:
        if not paused:
            log(f"load {os.getloadavg()[0]:.1f} > {max_load}: pausing")
        time.sleep(30)
        paused += 30
    if paused:
        log(f"resumed after {paused:.0f}s")
    return paused


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("engine", choices=["laya", "http"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--url")
    ap.add_argument("--meta", help="JSON file describing the model, its revision and weight hashes")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--max-load", type=float, default=20.0)
    ap.add_argument("--cells", default="v1", help="v1, extra for scenarios/cells-extra.json, or v2 for scenarios/v2/cells-v2.json")
    ap.add_argument("--concurrency", type=int, default=1, help="requests in flight; above 1 only where the parallel-answering test allows it")
    args = ap.parse_args()

    # v2 has its own directory and a committed sha256, checked before the first request
    cells_file = ROOT / "scenarios" / "v2" / f"cells-{args.cells}.json" if args.cells.startswith("v2") else ROOT / "scenarios" / f"cells-{args.cells}.json"
    if args.cells.startswith("v2"):
        import hashlib
        want = cells_file.with_suffix(".json.sha256").read_text().split()[0]
        if hashlib.sha256(cells_file.read_bytes()).hexdigest() != want:
            sys.exit("cells-v2.json does not match its committed sha256; run node scenarios/v2/freeze.mjs --check")
    frozen = json.loads(cells_file.read_text())
    cells = frozen["cells"][: args.limit] if args.limit else frozen["cells"]
    meta = json.loads(pathlib.Path(args.meta).read_text()) if args.meta else {}
    ask = laya_engine() if args.engine == "laya" else http_engine(args.url)
    log = lambda m: print(f"[{args.name} {time.strftime('%H:%M:%S')}] {m}", flush=True)

    # Warm up on the first cell so model load and compilation are not counted as request time
    t0 = time.perf_counter()
    ask(cells[0]["state"], cells[0]["questions"])
    warm_ms = (time.perf_counter() - t0) * 1000

    raw = ROOT / "results" / "v2" / "raw" if args.cells.startswith("v2") else RAW
    raw.mkdir(parents=True, exist_ok=True)
    out = raw / f"{args.name}{'' if args.cells in ('v1', 'v2') else '-' + args.cells}{'-limit' + str(args.limit) if args.limit else ''}.jsonl"
    rows, times, paused, failures = [], [], 0.0, 0
    started_wall = time.time()
    def one(cell):
        at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        t = time.perf_counter()
        try:
            answers, raw = ask(cell["state"], cell["questions"])
        except Exception as e:
            return cell, at, None, None, e
        return cell, at, answers, raw, (time.perf_counter() - t) * 1000

    load_pause = [0.0]

    def answered():
        # One at a time unless the parallel-answering test allowed more; rows keep the cells' order either way
        import concurrent.futures
        step = 25 * args.concurrency
        with concurrent.futures.ThreadPoolExecutor(args.concurrency) as pool:
            for start in range(0, len(cells), step):
                load_pause[0] += wait_for_load(args.max_load, log)
                if args.concurrency == 1:
                    yield from map(one, cells[start:start + step])
                else:
                    yield from pool.map(one, cells[start:start + step])

    with out.open("w") as fh:
        for i, (cell, at, answers, raw, ms) in enumerate(answered()):
            if answers is None:
                failures += 1
                log(f"failed {cell['id']}: {ms}")
                continue
            times.append(ms)
            where = {k: v for k, v in cell.items() if k not in ("state", "questions")}
            row = {"prompt_version": frozen["prompt_version"], "model_id": args.name, "pass": "a", **where, "answers": answers, "raw": raw, "ms": round(ms, 1), "at": at}
            fh.write(json.dumps(row) + "\n")
            rows.append(row)
            if i % 100 == 0:
                log(f"{i}/{len(cells)} median {statistics.median(times):.0f} ms")
    summary = {"model_id": args.name, "requests": len(cells), "answered": len(rows), "failures": failures, "warmup_ms": round(warm_ms),
               "median_ms": round(statistics.median(times), 1), "p95_ms": round(sorted(times)[int(0.95 * (len(times) - 1))], 1),
               "model_s": round(sum(times) / 1000, 1), "wall_s": round(time.time() - started_wall), "paused_for_load_s": paused + load_pause[0], "concurrency": args.concurrency,
               "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "meta": meta}
    out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "meta"}))


if __name__ == "__main__":
    sys.exit(main())
