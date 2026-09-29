"""Start one local /v1/systemone server, wait for it, record its weights, run the grid, stop it.

  python run/drive.py <model-id> --port P --cwd DIR --code-repo URL --code-commit SHA --runtime TEXT -- <server command...>

The server runs with HF_HOME pointed at a task-only directory (inherited from the environment),
binds 127.0.0.1, and is stopped when the grid finishes or fails. The meta file records the server
command and, as server_env, the inherited variables that choose which weights it loads (see MODEL_ENV).
"""
import argparse
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Some servers take their model from the environment, not argv (decider reads DECIDER_MODEL), so the
# command alone does not say what was served; these are recorded, and --record-env adds more names
MODEL_ENV = {"HF_HOME", "HF_HUB_CACHE", "HF_HUB_OFFLINE", "HF_ENDPOINT", "TRANSFORMERS_OFFLINE"}
# Never record credentials, even when a name would otherwise match
SECRET = re.compile(r"TOKEN|KEY|SECRET|PASSWORD", re.I)
PROBE = {"state": "The sky is blue.", "questions": {"q": {"type": "noul", "instructions": "Is the sky blue?"}}}


def probe(url):
    req = urllib.request.Request(url, data=json.dumps(PROBE).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_id")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--code-repo", required=True)
    ap.add_argument("--code-commit", required=True)
    ap.add_argument("--runtime", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--cells", default="v1")
    ap.add_argument("--startup-timeout", type=int, default=3600)
    ap.add_argument("--record-env", action="append", default=[], metavar="NAME", help="another server variable to record; *_MODEL names are recorded anyway")
    # Everything after "--" is the server command
    split = sys.argv.index("--")
    a = ap.parse_args(sys.argv[1:split])
    cmd = sys.argv[split + 1:]
    url = f"http://127.0.0.1:{a.port}/v1/systemone"
    wanted = MODEL_ENV | set(a.record_env)
    server_env = {k: v for k, v in sorted(os.environ.items()) if (k in wanted or k.endswith("_MODEL")) and not SECRET.search(k)}
    logf = open(ROOT / "results" / "raw" / (f"{a.model_id}.server.log" if a.cells == "v1" else f"{a.model_id}-{a.cells}.server.log"), "w")
    t0 = time.time()
    srv = subprocess.Popen(cmd, cwd=a.cwd, stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        while True:
            if srv.poll() is not None:
                raise SystemExit(f"server exited with {srv.returncode}; see results/raw/{a.model_id}.server.log")
            try:
                first = probe(url)
                break
            except Exception:
                if time.time() - t0 > a.startup_timeout:
                    raise SystemExit("server did not answer in time")
                time.sleep(5)
        load_s = round(time.time() - t0)
        print(f"[{a.model_id}] server up after {load_s}s; probe {json.dumps(first)[:200]}", flush=True)
        weights = json.loads(subprocess.run([sys.executable, str(ROOT / "run" / "weights.py"), os.environ["HF_HOME"]], capture_output=True, text=True, check=True).stdout)
        meta = {"model_id": a.model_id, "code": {"repo": a.code_repo, "commit": a.code_commit}, "runtime": a.runtime, "server_command": cmd,
                "server_env": server_env, "startup_s_including_download": load_s, "probe_answer": first, "weights": weights["repos"]}
        mpath = ROOT / "results" / "meta" / (f"{a.model_id}.json" if a.cells == "v1" else f"{a.model_id}-{a.cells}.json")
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(meta, indent=1))
        run = [sys.executable, str(ROOT / "run" / "run_local.py"), "http", "--name", a.model_id, "--url", url, "--meta", str(mpath)]
        if a.limit:
            run += ["--limit", str(a.limit)]
        run += ["--cells", a.cells]
        rc = subprocess.run(run).returncode
        sys.exit(rc)
    finally:
        try:
            os.killpg(srv.pid, signal.SIGTERM)
            srv.wait(timeout=60)
        except Exception:
            try:
                os.killpg(srv.pid, signal.SIGKILL)
            except Exception:
                pass


if __name__ == "__main__":
    main()
