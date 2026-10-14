#!/bin/sh
# AWS Strands Decider 2B on the v1 grid, the added wordings and the no-stranger cells, one model at a
# time: a venv with the pinned PyPI release, the pinned adapter and base, the model card's reference
# output as a gate, the three grids through its own server, then delete weights, venv and caches.
# Rows go to results/raw/ and results/meta/ beside the panel's.
# Usage: run/run_strands.sh <scratch dir>
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
S=$1; mkdir -p "$S/hf"
# strands-decider 0.1.0 on PyPI is byte-identical to strands-labs/strands-decider@fe39fad
WHEEL_SHA=cd8ee1c26937aeb4f6548d920b30b17012bd642e862e2c9f37acf2e6c9d3feeb
CODE=fe39fad9ec8ec355993f76b977348d915ec9cb65
REPO=StrandsAgents/strands-decider-2B-hobson-v19
REV=bb282d786bc251fd4e3068de3ada9ddbb38127cd
# provenance.json names this base revision; the loader reads the base by name, so it must still be main
BASE_REV=b1485b2fa6dfa1287294f269f5fb618e03d52d7c
export UV_CACHE_DIR=$S/uvcache-strands HF_HUB_DISABLE_TELEMETRY=1 HF_HOME=$S/hf
cd "$S"
uv venv -q -p 3.12 venv-strands
curl -sLo strands_decider-0.1.0-py3-none-any.whl https://files.pythonhosted.org/packages/py3/s/strands-decider/strands_decider-0.1.0-py3-none-any.whl
echo "$WHEEL_SHA  strands_decider-0.1.0-py3-none-any.whl" | shasum -a 256 -c -
uv pip install -q -p venv-strands/bin/python ./strands_decider-0.1.0-py3-none-any.whl
PY=$S/venv-strands/bin/python
t0=$(date +%s)
SNAP=$($PY -c "from huggingface_hub import snapshot_download as s; print(s('$REPO', revision='$REV'))")
$PY -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen3.5-2B-Base', revision='$BASE_REV')"
echo "download took $(( $(date +%s) - t0 ))s"
main=$($PY -c "from huggingface_hub import HfApi; print(HfApi().model_info('Qwen/Qwen3.5-2B-Base').sha)")
[ "$main" = "$BASE_REV" ] || { echo "Qwen3.5-2B-Base main moved to $main"; exit 4; }
# Every file against the repo's own MANIFEST.sha256
(cd "$SNAP" && $PY -m strands_decider.hf_export verify .)
# The model card's reference output for the v19 checkpoint: urgency 0.829, billing 0.846, score 1.10
$S/venv-strands/bin/strands-decider ask "$SNAP" --device mps \
  --state "Help! My payouts have been failing for 3 days! " \
  --choice "Which team should handle this?=billing,sales,retail" \
  --noul "Does this convey urgency?" \
  --score "How frustrated is the writer?=calm,frustrated,depressed" | tee "$here/results/meta/strands-decider-2b-card.txt"
python3 - "$here/results/meta/strands-decider-2b-card.txt" <<'EOF' || { echo "model card check failed; weights kept in $S for a look"; exit 3; }
import re, sys
t = open(sys.argv[1]).read()
noul = float(re.search(r"noul_0 noul = ([0-9.]+)", t).group(1))
billing = float(re.search(r"^\s+billing\s+([0-9.]+)", t, re.M).group(1))
score = float(re.search(r"score_0 score = ([0-9.]+)", t).group(1))
print("card 0.829 / 0.846 / 1.10, ours", noul, billing, score)
sys.exit(not (abs(noul - 0.829) <= 0.01 and abs(billing - 0.846) <= 0.01 and abs(score - 1.10) <= 0.02))
EOF
RT="Strands Decider 2B (hobson-v19): strands-decider serve (PyPI 0.1.0 = strands-labs/strands-decider@fe39fad), PyTorch MPS, bfloat16 as configured (hobson_config.json), LoRA adapter and pointer head on Qwen3.5-2B-Base; native Noul, all questions in one call"
cd "$here"
for C in v1 extra nostranger; do
  python3 run/drive.py strands-decider-2b --cells $C --port 8016 --cwd "$S" --code-repo https://github.com/strands-labs/strands-decider --code-commit $CODE --runtime "$RT" -- \
    $S/venv-strands/bin/strands-decider serve "$SNAP" --host 127.0.0.1 --port 8016 --device mps 2>&1 | grep -v "00/[0-9]* median"
done
"$here/run/cleanup.sh" strands-decider-2b "$S/venv-strands" "$S/uvcache-strands" "$S/hf" "$S/strands_decider-0.1.0-py3-none-any.whl"
