"""Compare a rerun's rows with the committed ones, cell by cell.

  python3 analysis/compare_rerun.py results/raw/laya-limit50.jsonl
  python3 analysis/compare_rerun.py results/raw/jev-pass-r.jsonl
  python3 analysis/compare_rerun.py rerun.jsonl --ref results/raw/kev-4b.jsonl

Runners write into results/raw/, over the committed file when the name is the same, so by default
the reference is read from git (HEAD): the same path with any -limitN suffix dropped, or, for a Jev
pass, the mean of the three committed passes (jev-pass-a/b/c), which is what the page shows.
Reports, over the cells both sides answered: mean and largest absolute difference per question,
and how many answers land on the other side of 0.5 (a changed choice).
"""
import argparse
import json
import pathlib
import re
import statistics
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def rows(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def committed(path, rev):
    rel = pathlib.Path(path).resolve().relative_to(ROOT).as_posix()
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{rel}"], capture_output=True, text=True, check=True).stdout


def default_refs(path):
    p = pathlib.Path(path)
    jev = re.fullmatch(r"(jev(?:-[a-z]+)?-pass)-[^.]+\.jsonl", p.name)
    if jev:
        return [p.with_name(f"{jev.group(1)}-{x}.jsonl") for x in "abc"]
    return [p.with_name(re.sub(r"-limit\d+(?=\.jsonl$)", "", p.name))]


def mean_answers(ref_sets):
    by_id = {}
    for rs in ref_sets:
        for r in rs:
            by_id.setdefault(r["id"], []).append(r["answers"])
    return {i: {q: statistics.fmean(a[q] for a in ans) for q in ans[0]} for i, ans in by_id.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rerun")
    ap.add_argument("--ref", action="append", help="reference JSONL file(s) on disk; several are averaged")
    ap.add_argument("--rev", default="HEAD", help="git revision for the default reference")
    a = ap.parse_args()

    new = {r["id"]: r["answers"] for r in rows(pathlib.Path(a.rerun).read_text())}
    if a.ref:
        names = a.ref
        ref = mean_answers([rows(pathlib.Path(f).read_text()) for f in a.ref])
    else:
        names = [f"{a.rev}:{p.relative_to(ROOT) if p.is_absolute() else p}" for p in (pathlib.Path(x).resolve() for x in default_refs(a.rerun))]
        ref = mean_answers([rows(committed(p, a.rev)) for p in default_refs(a.rerun)])

    ids = [i for i in new if i in ref]
    if not ids:
        sys.exit("no cell ids in common with the reference")
    print(f"rerun {a.rerun}: {len(new)} cells; reference {', '.join(map(str, names))}: {len(ref)} cells; compared {len(ids)}")
    flips_total = 0
    for q in new[ids[0]]:
        d = [abs(new[i][q] - ref[i][q]) for i in ids]
        flips = sum((new[i][q] > 0.5) != (ref[i][q] > 0.5) for i in ids)
        flips_total += flips
        worst = max(ids, key=lambda i: abs(new[i][q] - ref[i][q]))
        print(f"  {q:14} mean |diff| {statistics.fmean(d):.4f}   max {max(d):.4f} ({worst})   changed choices {flips} of {len(ids)}")
    print(f"changed choices in all: {flips_total}")


if __name__ == "__main__":
    main()
