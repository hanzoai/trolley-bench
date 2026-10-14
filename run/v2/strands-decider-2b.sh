#!/bin/sh
# AWS Strands Decider 2B on the v2 grid as v1 ran it (run/run_strands.sh): the pinned PyPI wheel
# (byte-identical to strands-labs/strands-decider@fe39fad), the adapter and its base loaded offline,
# the repo's own MANIFEST.sha256 and the model card's reference output as gates.
# Usage: run/v2/strands-decider-2b.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
WHEEL_SHA=cd8ee1c26937aeb4f6548d920b30b17012bd642e862e2c9f37acf2e6c9d3feeb
CODE=fe39fad9ec8ec355993f76b977348d915ec9cb65
weights strands-decider-2b
SNAP=$(snapshot StrandsAgents/strands-decider-2B-hobson-v19)
export UV_CACHE_DIR=$S/uvcache-strands
if [ ! -x "$S/venv-strands/bin/strands-decider" ]; then
  uv venv -q -p 3.12 "$S/venv-strands"
  curl -sLo "$S/strands_decider-0.1.0-py3-none-any.whl" https://files.pythonhosted.org/packages/py3/s/strands-decider/strands_decider-0.1.0-py3-none-any.whl
  echo "$WHEEL_SHA  $S/strands_decider-0.1.0-py3-none-any.whl" | shasum -a 256 -c -
  uv pip install -q -p "$S/venv-strands/bin/python" "$S/strands_decider-0.1.0-py3-none-any.whl"
fi
(cd "$SNAP" && "$S/venv-strands/bin/python" -m strands_decider.hf_export verify .)
"$S/venv-strands/bin/strands-decider" ask "$SNAP" --device mps --state "Help! My payouts have been failing for 3 days! " \
  --choice "Which team should handle this?=billing,sales,retail" --noul "Does this convey urgency?" \
  --score "How frustrated is the writer?=calm,frustrated,depressed" > "$S/card.txt"
python3 - "$S/card.txt" <<'PY' || { echo "model card check failed"; exit 3; }
import re, sys
t = open(sys.argv[1]).read()
noul = float(re.search(r"noul_0 noul = ([0-9.]+)", t).group(1))
billing = float(re.search(r"^\s+billing\s+([0-9.]+)", t, re.M).group(1))
score = float(re.search(r"score_0 score = ([0-9.]+)", t).group(1))
print("card 0.829 / 0.846 / 1.10, ours", noul, billing, score)
sys.exit(not (abs(noul - 0.829) <= 0.01 and abs(billing - 0.846) <= 0.01 and abs(score - 1.10) <= 0.02))
PY
# One request at a time: two concurrent requests crashed this server with a Metal assertion on 2026-10-02
drive strands-decider-2b --cells v2 --port 8016 --cwd "$S" --code-repo https://github.com/strands-labs/strands-decider --code-commit $CODE \
  --runtime "Strands Decider 2B (hobson-v19): strands-decider serve (PyPI 0.1.0 = strands-labs/strands-decider@fe39fad), PyTorch MPS, bfloat16 as configured, LoRA adapter and pointer head on Qwen3.5-2B-Base; native Noul, all questions in one call" -- \
  "$S/venv-strands/bin/strands-decider" serve "$SNAP" --host 127.0.0.1 --port 8016 --device mps
cleanup strands-decider-2b "$S/venv-strands" "$S/uvcache-strands" "$S/strands_decider-0.1.0-py3-none-any.whl" "$S/card.txt"
