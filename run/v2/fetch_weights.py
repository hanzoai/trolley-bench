"""Download one or more local models' weights at the revisions pinned in models.yaml and check
every file's SHA-256 against the pin, with the standard library only.

  python3 run/v2/fetch_weights.py --dest <dir> clef kev-4b ...    (or: all)

Each model gets its own Hugging Face cache, <dir>/<model>/hf, laid out as huggingface_hub lays it
out (blobs named by hash, snapshots/<revision>/ symlinks), so the run scripts can load it with
HF_HOME=<dir>/<model>/hf and HF_HUB_OFFLINE=1, and deleting that one directory frees the model.
Only the files models.yaml pins are fetched, and every byte is checked by SHA-256. Most large files'
pins in models.yaml are the Hub's Xet hashes rather than SHA-256 (v1's run/weights.py read the
cache's blob names as SHA-256, and huggingface_hub names Xet-stored blobs by Xet hash). For those,
the Hub must report that Xet hash for the file at the pinned commit, and the bytes must match the
SHA-256 in that commit's LFS pointer. A file that fails is kept as .mismatch and the model fails.
Interrupted downloads resume. A record per model goes to results/v2/weights/.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
HUB = "https://huggingface.co"
# Files models.yaml pins by hash alone; v1 took them from Verdict's README path, which reads the
# rlcd bundle from the Hub. This revision (2026-09-20) predates v1 and its files match the pins
FILE_SOURCES = {
    "heman10x/rlcd-modernbert-151m 2.0.0": ("heman10x/rlcd-modernbert-151m", "8af2496eb63c7fa66d7d234e1f62629380030eb4"),
}
# Made in the snapshot directory by v1's own run (Python's bytecode cache), not part of the repo
LOCAL_ONLY = re.compile(r"(^|/)__pycache__/")


def read_models():
    """Parse the generated models.yaml (its fixed shape, not general YAML)."""
    models, model, weight = {}, None, None
    for line in (ROOT / "models.yaml").read_text().splitlines():
        if m := re.match(r"  - id: (\S+)$", line):
            model = models.setdefault(m.group(1), [])
            weight = None
        elif m := re.match(r"      - repo: (\S+)$", line):
            weight = {"repo": m.group(1), "files": {}}
            model.append(weight)
        elif m := re.match(r"        revision: (\S+)$", line):
            weight["revision"] = m.group(1)
        elif m := re.match(r'          "(.+)": (?:\{sha256: )?([0-9a-f]{64})', line):
            weight["files"][m.group(1)] = m.group(2)
        elif m := re.match(r'      - file: "(\S+) \((.+)\)"$', line):
            repo, rev = FILE_SOURCES[m.group(2)]
            weight = {"repo": repo, "revision": rev, "files": {}, "path_prefix": m.group(1).rsplit("/", 1)[0]}
            model.append(weight)
            weight["files"][m.group(1).rsplit("/", 1)[1]] = None
        elif m := re.match(r"        sha256: ([0-9a-f]{64})$", line):
            name = next(iter(weight["files"]))
            weight["files"][name] = m.group(1)
    # One Hub repo per (repo, revision), so Verdict's four bundle files become one entry
    for mid, weights in models.items():
        merged = {}
        for w in weights:
            key = (w["repo"], w["revision"])
            if key in merged:
                merged[key]["files"].update(w["files"])
            else:
                merged[key] = {"repo": w["repo"], "revision": w["revision"], "files": dict(w["files"])}
        models[mid] = list(merged.values())
    return models


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"user-agent": "trolley-bench-fetch/2", **(headers or {})})
    return urllib.request.urlopen(req, timeout=120)


def tree(repo, rev):
    """Every file at the revision: path -> (size, LFS sha256 or None, git blob id, Xet hash or None)."""
    out, url = {}, f"{HUB}/api/models/{repo}/tree/{rev}?recursive=1"
    while url:
        with get(url) as resp:
            for f in json.load(resp):
                if f["type"] == "file":
                    out[f["path"]] = (f["size"], (f.get("lfs") or {}).get("oid"), f["oid"], f.get("xetHash"))
            nxt = re.search(r'<([^>]+)>;\s*rel="next"', resp.headers.get("link") or "")
            url = nxt.group(1) if nxt else None
    return out


def fetch(cache, repo, rev, path, size, blob_name, want, log):
    blobs, snap = cache / "blobs", cache / "snapshots" / rev
    blob, part, bad = blobs / blob_name, blobs / (blob_name + ".incomplete"), blobs / (blob_name + ".mismatch")
    link = snap / path
    # A file an earlier run set aside is checked again against the current rule
    if bad.exists() and not blob.exists():
        bad.rename(blob)
    if blob.exists() and blob.stat().st_size == size:
        got = sha256_file(blob)
        if got == want:
            place_link(link, blob)
            return {"file": path, "bytes": size, "sha256": got, "fetched": False}
        blob.unlink()
    blobs.mkdir(parents=True, exist_ok=True)
    url = f"{HUB}/{repo}/resolve/{rev}/{urllib.parse.quote(path)}"
    for attempt in range(8):
        have = part.stat().st_size if part.exists() else 0
        if have > size:
            part.unlink()
            have = 0
        try:
            if have < size:
                with get(url, {"range": f"bytes={have}-"} if have else None) as resp, open(part, "ab" if have else "wb") as out:
                    if have and resp.status != 206:
                        out.truncate(0)
                    while chunk := resp.read(8 << 20):
                        out.write(chunk)
            # A connection the CDN closes early can end the read without an error
            got_bytes = part.stat().st_size
            if got_bytes == size:
                break
            raise OSError(f"stream ended at byte {got_bytes} of {size}")
        except Exception as err:  # noqa: BLE001 - any network failure is retried from where it stopped
            log(f"  {path}: {err}; retry {attempt + 1} from byte {part.stat().st_size if part.exists() else 0}")
            time.sleep(5 * (attempt + 1))
    else:
        raise RuntimeError(f"{repo}@{rev} {path}: download failed")
    got = sha256_file(part)
    if got != want:
        part.rename(bad)
        raise RuntimeError(f"{repo}@{rev} {path}: sha256 {got} ({size} bytes), pinned {want}; kept as {blob_name}.mismatch for a look")
    part.rename(blob)
    place_link(link, blob)
    return {"file": path, "bytes": size, "sha256": got, "fetched": True}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(16 << 20):
            h.update(chunk)
    return h.hexdigest()


def place_link(link, blob):
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(os.path.relpath(blob, link.parent))


def fetch_model(mid, weights, dest, jobs):
    t0 = time.time()
    hf = dest / mid / "hf" / "hub"

    def log(msg):
        print(f"[{mid}] {msg}", flush=True)

    record = {"model_id": mid, "repos": [], "skipped": []}
    for w in weights:
        repo, rev = w["repo"], w["revision"]
        cache = hf / ("models--" + repo.replace("/", "--"))
        files = tree(repo, rev)
        (cache / "refs").mkdir(parents=True, exist_ok=True)
        tasks = []
        for path, want in sorted(w["files"].items()):
            if path not in files:
                if LOCAL_ONLY.search(path):
                    record["skipped"].append({"repo": repo, "file": path, "why": "made locally by v1's run, not in the repo"})
                    continue
                raise RuntimeError(f"{repo}@{rev}: pinned file {path} is not in the repo at that revision")
            size, lfs, oid, xet = files[path]
            pin = want
            if lfs and want != lfs:
                if want != xet:
                    raise RuntimeError(f"{repo}@{rev} {path}: pin {want} is neither the commit's LFS SHA-256 {lfs} nor the Hub's Xet hash {xet}")
                # The pin is the Hub's Xet hash for this file at this commit; check the bytes by the commit's SHA-256
                want = lfs
            # huggingface_hub names LFS blobs by SHA-256 and small git files by their git blob id
            tasks.append((path, size, lfs or oid, want, pin))
        log(f"{repo}@{rev[:10]}: {len(tasks)} files, {sum(t[1] for t in tasks) / 1e9:.2f} GB")
        with concurrent.futures.ThreadPoolExecutor(jobs) as pool:
            done = list(pool.map(lambda t: {**fetch(cache, repo, rev, t[0], t[1], t[2], t[3], log), "pin": t[4]}, tasks))
        record["repos"].append({"repo": repo, "revision": rev, "bytes": sum(d["bytes"] for d in done),
                                "files": {d["file"]: {"sha256": d["sha256"], "bytes": d["bytes"], **({"pin_is_xet_hash": d["pin"]} if d["pin"] != d["sha256"] else {})} for d in done},
                                "verified": "every file's SHA-256 matches models.yaml's pin, or the commit's LFS SHA-256 where the pin is the Hub's Xet hash for that file"})
    record["bytes"] = sum(r["bytes"] for r in record["repos"])
    record["seconds"] = round(time.time() - t0, 1)
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out = ROOT / "results" / "v2" / "weights" / f"{mid}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1) + "\n")
    log(f"ok: {record['bytes'] / 1e9:.2f} GB verified in {record['seconds']:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--dest", required=True, type=pathlib.Path)
    ap.add_argument("--jobs", type=int, default=4, help="files in flight per model")
    a = ap.parse_args()
    models = read_models()
    ids = [m for m in models if m != "jev"] if a.models == ["all"] else a.models
    failed = []
    for mid in ids:
        if mid not in models or not models[mid]:
            sys.exit(f"{mid}: no pinned weights in models.yaml")
        try:
            fetch_model(mid, models[mid], a.dest.resolve(), a.jobs)
        except Exception as err:  # noqa: BLE001 - report every model's failure, then exit non-zero
            print(f"[{mid}] FAILED: {err}", flush=True)
            failed.append(mid)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
