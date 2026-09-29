"""Describe every snapshot in a task-only HF_HOME: repo, revision, and each file's hashes; or check a rerun's.

  python3 run/weights.py <HF_HOME> > meta-weights.json
  python3 run/weights.py --check results/meta/decider-2b.json [--ref FILE] [--rev HEAD]

Each file gets "sha256", the SHA-256 of its bytes, which is what the Hub lists as the LFS oid, and,
for files the Hub stores in Xet, "xet_hash" when the local cache reveals it. The Hub cache names a
large file's blob after the download's etag, which is the SHA-256 on some huggingface_hub setups and
the Xet hash on others (the Xet backend, hf_xet), so the blob name is never taken as the SHA-256:
every file is hashed here, and a 64-character blob name that differs from it is the Xet hash.

--check compares a rerun's meta file with the committed one: every file the committed run recorded
must be present at the same revision with the same SHA-256. By default the reference is the same
path at git HEAD, with any -sample suffix dropped (a sample run uses the v1 run's weights).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 24):
            h.update(chunk)
    return h.hexdigest()


def describe(hf_home):
    hub = pathlib.Path(hf_home) / "hub"
    repos = []
    for repo in sorted(hub.glob("models--*")):
        for snap in sorted((repo / "snapshots").glob("*")):
            files = {}
            for f in sorted(snap.rglob("*")):
                if f.is_dir():
                    continue
                blob = pathlib.Path(os.path.realpath(f))
                entry = {"sha256": sha256(blob)}
                if re.fullmatch(r"[0-9a-f]{64}", blob.name) and blob.name != entry["sha256"]:
                    entry["xet_hash"] = blob.name
                entry["bytes"] = blob.stat().st_size
                files[str(f.relative_to(snap))] = entry
            repos.append({"repo": repo.name[len("models--"):].replace("--", "/"), "revision": snap.name,
                          "bytes": sum(v["bytes"] for v in files.values()), "files": files})
    return {"repos": repos}


def check(path, ref, rev):
    new = json.loads(pathlib.Path(path).read_text())
    if ref:
        name, old = ref, json.loads(pathlib.Path(ref).read_text())
    else:
        p = pathlib.Path(path).resolve()
        rel = p.with_name(p.name.replace("-sample", "", 1)).relative_to(ROOT).as_posix()
        name = f"{rev}:{rel}"
        old = json.loads(subprocess.run(["git", "-C", str(ROOT), "show", name], capture_output=True, text=True, check=True).stdout)
    have = {(w["repo"], w["revision"]): w["files"] for w in new.get("weights", [])}
    bad = checked = 0
    for w in old.get("weights", []):
        files = have.get((w["repo"], w["revision"]))
        if files is None:
            print(f"MISSING  {w['repo']}@{w['revision']}: not in the rerun (another revision, or not downloaded)")
            bad += 1
            continue
        for f, v in w["files"].items():
            checked += 1
            got = files.get(f)
            if got is None:
                print(f"MISSING  {w['repo']}@{w['revision'][:8]} {f}")
                bad += 1
            elif got["sha256"] != v["sha256"] or ("xet_hash" in got and "xet_hash" in v and got["xet_hash"] != v["xet_hash"]):
                print(f"DIFFERS  {w['repo']}@{w['revision'][:8]} {f}: sha256 {got['sha256']} against {v['sha256']}")
                bad += 1
        extra = sorted(set(files) - set(w["files"]))
        if extra:
            print(f"extra    {w['repo']}@{w['revision'][:8]}: {len(extra)} file(s) the committed run did not fetch ({', '.join(extra[:5])}{', ...' if len(extra) > 5 else ''})")
    print(f"{'OK' if not bad else 'MISMATCH'}: {checked - bad} of {checked} committed files match {name} by SHA-256")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hf_home", nargs="?")
    ap.add_argument("--check", metavar="META", help="a rerun's results/meta file to check against the committed one")
    ap.add_argument("--ref", help="reference meta file on disk instead of the committed one")
    ap.add_argument("--rev", default="HEAD", help="git revision for the default reference")
    a = ap.parse_args()
    if a.check:
        sys.exit(check(a.check, a.ref, a.rev))
    if not a.hf_home:
        ap.error("give HF_HOME, or --check META")
    print(json.dumps(describe(a.hf_home), indent=1))


if __name__ == "__main__":
    main()
