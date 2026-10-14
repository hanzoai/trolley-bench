"""Write huggingface_hub's cached tree listing (hub/models--<repo>/trees/<commit>.json) for a fetched
model, listing exactly the files run/v2/fetch_weights.py fetched and verified.

  python3 run/v2/tree_cache.py --dest <weights dir> <model> ...

huggingface_hub 1.31-1.33 answer snapshot_download(repo, revision=<commit hash>) from the cache only
when that listing exists; with HF_HUB_OFFLINE=1 and no listing they raise OfflineModeIsEnabled even
though every file is on disk (revision=None resolves through refs/main and is unaffected). Their own
downloads write the listing; fetch_weights.py does not. The listing names only the verified files, so
a runtime asking for a file outside the pins still fails offline instead of fetching it.
Standard library only; the listing's per-file fields come from the Hub's tree at the pinned commit.
"""
import argparse
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]


def hub_tree(repo, rev):
    out, url = {}, f"https://huggingface.co/api/models/{repo}/tree/{rev}?recursive=1"
    while url:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"user-agent": "trolley-bench-fetch/2"}), timeout=120) as r:
            for f in json.load(r):
                if f["type"] == "file":
                    out[f["path"]] = f
            nxt = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("link") or "")
            url = nxt.group(1) if nxt else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--dest", required=True, type=pathlib.Path)
    a = ap.parse_args()
    for mid in a.models:
        for r in json.loads((ROOT / "results" / "v2" / "weights" / f"{mid}.json").read_text())["repos"]:
            tree = hub_tree(r["repo"], r["revision"])
            files = {}
            for path, mine in sorted(r["files"].items()):
                f = tree[path]
                lfs = f.get("lfs")
                # The verified bytes must be the commit's: its LFS SHA-256, or the git blob for small files
                if lfs and lfs["oid"] != mine["sha256"]:
                    raise SystemExit(f"{r['repo']} {path}: fetched {mine['sha256']}, commit says {lfs['oid']}")
                entry = {"size": f["size"], "blob_id": f["oid"]}
                if lfs:
                    entry |= {"lfs_sha256": lfs["oid"], "lfs_size": lfs["size"]}
                if f.get("xetHash"):
                    entry["xet_hash"] = f["xetHash"]
                files[path] = entry
            out = a.dest.resolve() / mid / "hf" / "hub" / ("models--" + r["repo"].replace("/", "--")) / "trees" / f"{r['revision']}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"format_version": 1, "files": files}, indent=1) + "\n")
            print(f"[{mid}] {r['repo']}@{r['revision'][:7]}: {len(files)} files listed")


if __name__ == "__main__":
    main()
