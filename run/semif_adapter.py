"""SemIf has no Noul: each Noul becomes a two-option question (yes / no) and P(yes) is read back.

  python run/semif_adapter.py to-rows <out.jsonl>              one SemIf input row per (cell, question)
  python run/semif_adapter.py from-rows <semif-output.jsonl>   writes results/raw/semif.jsonl

The options are bare "Yes." / "No." when the Noul has no criteria, and the criteria text when it
does. SemIf's own output rows (logits, revision, prompt and file hashes) go to results/raw/semif-raw.jsonl.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"


def options(q):
    crit = q.get("criteria") or {}
    return [{"id": "yes", "description": crit.get("true", "Yes.")}, {"id": "no", "description": crit.get("false", "No.")}]


def cells():
    return json.loads((ROOT / "scenarios" / "cells-v1.json").read_text())


def to_rows(out):
    with open(out, "w") as fh:
        for cell in cells()["cells"]:
            state = cell["state"] if isinstance(cell["state"], str) else json.dumps(cell["state"])
            for name, q in cell["questions"].items():
                fh.write(json.dumps({"id": f"{cell['id']}#{name}", "state": state, "question": q["instructions"], "options": options(q)}) + "\n")


def from_rows(output):
    frozen = cells()
    preds = [json.loads(l) for l in pathlib.Path(output).read_text().splitlines() if l.strip()]
    by_id = {p["id"]: p for p in preds}
    rows = []
    for cell in frozen["cells"]:
        answers, raw, ms = {}, {}, 0.0
        for name in cell["questions"]:
            p = by_id[f"{cell['id']}#{name}"]
            answers[name] = dict(zip(p["option_ids"], p["probabilities"]))["yes"]
            raw[name] = {"option_ids": p["option_ids"], "probabilities": p["probabilities"], "option_logits": p.get("option_logits")}
            ms += p["total_seconds"] * 1000
        where = {k: v for k, v in cell.items() if k not in ("state", "questions")}
        rows.append({"prompt_version": frozen["prompt_version"], "model_id": "semif", "pass": "a", **where, "answers": answers, "raw": raw, "ms": round(ms, 1)})
    (RAW / "semif.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (RAW / "semif-raw.jsonl").write_text("".join(json.dumps(p) + "\n" for p in preds))
    print(len(rows), "rows")


if __name__ == "__main__":
    to_rows(sys.argv[2]) if sys.argv[1] == "to-rows" else from_rows(sys.argv[2])
