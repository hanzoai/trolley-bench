"""Label every v2 wording with its format, by a fixed mechanical rule on the rendered state, so
results can be reported per format without anyone choosing the groups after seeing them.

  python3 analysis/v2_formats.py          (writes analysis/v2_formats.json)
  python3 analysis/v2_formats.py --check  (fails if the committed file differs)

Rules, first match wins, applied to every cell of the wording (a wording must get one label):
- json:      the state is sent as an object, not text
- yaml:      a line "key:" with nothing after it, followed by an indented line
- list:      a line starting "- ", "## " or "Option <number>."
- key-value: three or more lines of the form "Label: value"
- prose:     everything else, including one-paragraph "Main track: 5 people." styles
"""
import json
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
CELLS = ROOT / "scenarios" / "v2" / "cells-v2.json"
OUT = ROOT / "analysis" / "v2_formats.json"
FAMILY = {"switch": "switch", "asym_k2": "switch", "asym_k5": "switch", "asym_k10": "switch", "literal_zero": "switch",
          "ai_control": "ai", "developer": "ai", "self_copy": "ai",
          "footbridge": "foot", "footbridge_ai_man": "foot", "footbridge_self": "foot"}


def label(state):
    if not isinstance(state, str):
        return "json"
    lines = state.split("\n")
    if any(re.match(r"^[^\s:][^:]*:\s*$", a) and b.startswith("  ") for a, b in zip(lines, lines[1:])):
        return "yaml"
    if any(re.match(r"^(- |## |Option \d+\.)", ln) for ln in lines):
        return "list"
    if sum(bool(re.match(r"^[A-Za-z][^:]{0,40}: \S", ln)) for ln in lines) >= 3:
        return "key-value"
    return "prose"


def build():
    seen = defaultdict(set)
    for c in json.loads(CELLS.read_text())["cells"]:
        seen[(FAMILY[c["scenario"]], c["wording"])].add(label(c["state"]))
    mixed = {f"{f}/{w}": sorted(v) for (f, w), v in seen.items() if len(v) > 1}
    if mixed:
        sys.exit(f"wordings with more than one format across their cells: {mixed}")
    out = defaultdict(dict)
    for (f, w), v in sorted(seen.items()):
        out[f][w] = next(iter(v))
    return {"rule": "analysis/v2_formats.py", "families": out}


if __name__ == "__main__":
    text = json.dumps(build(), indent=1) + "\n"
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text() == text else "v2_formats.json does not match the rule's output")
    OUT.write_text(text)
    d = json.loads(text)["families"]
    for f, ws in d.items():
        counts = defaultdict(list)
        for w, lab in ws.items():
            counts[lab].append(w)
        print(f, {k: f"{len(v)}: {' '.join(v)}" for k, v in sorted(counts.items())})
