"""Describe every snapshot in a task-only HF_HOME: repo, revision, and each file's SHA-256.

LFS files are stored under their SHA-256 in the Hub cache, so the blob name is the hash; small
git files are hashed here. Usage: python run/weights.py <HF_HOME> > meta-weights.json
"""
import hashlib
import json
import os
import pathlib
import sys

hub = pathlib.Path(sys.argv[1]) / "hub"
repos = []
for repo in sorted(hub.glob("models--*")):
    for snap in sorted((repo / "snapshots").glob("*")):
        files = {}
        for f in sorted(snap.rglob("*")):
            if f.is_dir():
                continue
            blob = pathlib.Path(os.path.realpath(f))
            h = blob.name if len(blob.name) == 64 else hashlib.sha256(blob.read_bytes()).hexdigest()
            files[str(f.relative_to(snap))] = {"sha256": h, "bytes": blob.stat().st_size}
        repos.append({"repo": repo.name[len("models--"):].replace("--", "/"), "revision": snap.name,
                      "bytes": sum(v["bytes"] for v in files.values()), "files": files})
print(json.dumps({"repos": repos}, indent=1))
