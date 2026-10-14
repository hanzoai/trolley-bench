"""Rerun a spread of v1 prompts on a Clef release in float32 and compare with the bf16 grid rows.

  python run/clef_precision_check.py <snapshot dir> <model id> <out.json>

The card publishes no reference numbers, so this checks the one thing our port changes: bf16 on
MPS instead of the H200 it was tested on. Same release code; only the dtype differs.
"""
import json
import pathlib
import sys

import torch

path, mid, out = sys.argv[1], sys.argv[2], sys.argv[3]
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, path)
from joint_schema_model import load_release_model, systemone  # noqa: E402

cells = {c["id"]: c for c in json.loads((ROOT / "scenarios" / "cells-v1.json").read_text())["cells"]}
bf16 = {r["id"]: r["answers"] for r in map(json.loads, (ROOT / "results" / "raw" / f"{mid}.jsonl").read_text().splitlines())}
ids = [i for i in cells if i.split("|")[0] in ("switch", "footbridge", "ai_control", "self_copy", "developer")
       and i.split("|")[1] in ("c1", "v1", "w2") and int(i.split("|")[3]) in (0, 1, 5, 20)][:24]
model, processor = load_release_model(path, device="mps", dtype=torch.float32)
rows, diffs = [], []
for i in ids:
    c = cells[i]
    a = systemone(model, processor, {"model": mid, "state": c["state"], "questions": c["questions"]})["answers"]
    for q in c["questions"]:
        d = abs(a[q]["noul"] - bf16[i][q])
        diffs.append(d)
        rows.append({"id": i, "q": q, "fp32": a[q]["noul"], "bf16": bf16[i][q], "abs_diff": round(d, 4),
                     "same_side": (a[q]["noul"] > 0.5) == (bf16[i][q] > 0.5)})
res = {"model_id": mid, "prompts": len(ids), "answers": len(rows), "mean_abs_diff": round(sum(diffs) / len(diffs), 4),
       "max_abs_diff": round(max(diffs), 4), "choice_changes": sum(not r["same_side"] for r in rows), "rows": rows}
pathlib.Path(out).write_text(json.dumps(res, indent=1))
print(json.dumps({k: v for k, v in res.items() if k != "rows"}))
