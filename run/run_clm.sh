#!/bin/sh
# CLM-8B (Contrastive-LM) on the v1 grid, the added wordings and the no-stranger cells, one model at a
# time: clone at the pinned commit, a venv without vLLM, the pinned Qwen3-8B and head, a check against
# the README's quickstart numbers, the three grids, then delete weights, venv and caches.
# Outputs go to results/contrastive-lm/, apart from the published results.
# Usage: run/run_clm.sh <scratch dir>
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
S=$1; mkdir -p "$S/code" "$S/hf"
CODE=bb42c6c5bf914fd449bed2f6ca65be80602cb1f7
QWEN_REV=b968826d9c46dd6066d109eabc6255188de91218
HEAD_REV=e939398d4556fcd9400c76fa8c5a513202f42b0a
export UV_CACHE_DIR=$S/uvcache-clm HF_HUB_DISABLE_TELEMETRY=1 HF_HOME=$S/hf
OUT=$here/results/contrastive-lm; mkdir -p "$OUT"
cd "$S/code"
[ -d CLM ] || git clone -q https://github.com/Contrastive-LM/CLM.git
cd CLM && git checkout -q $CODE
# The package's own dependencies minus vLLM, which needs an NVIDIA GPU; the encoder is clm_embedder.py
uv venv -q -p 3.12 .venv && uv pip install -q -p .venv/bin/python torch==2.8.0 transformers==4.57.1 numpy requests fastapi uvicorn huggingface_hub
uv pip install -q -p .venv/bin/python --no-deps -e .
t0=$(date +%s)
QWEN=$(.venv/bin/python -c "from huggingface_hub import snapshot_download as s; print(s('Qwen/Qwen3-8B', revision='$QWEN_REV'))")
CKPT=$(.venv/bin/python -c "from huggingface_hub import hf_hub_download as d; print(d('Contrastive-LM/CLM-v0.1-8B', 'CLM_v0.1-8B.pt', revision='$HEAD_REV'))")
echo "download took $(( $(date +%s) - t0 ))s"
SERVE="sh $here/run/clm_serve.sh 8015 8091 $QWEN $CKPT $S/code/CLM/.venv/bin/python"
RT="CLM-8B: clm-serve (FastAPI, heads on CPU) over Qwen3-8B last-token embeddings from transformers on MPS in bfloat16 (run/clm_embedder.py, in place of the vLLM pooling server); native Noul, all questions in one call, each scored on its own"
cd "$here"
# Check this encoder against the model card before the grids. The card's tides ranking (0.993, no
# question text, so no prompt layout involved) is the reference; the README's quickstart numbers
# (urgency 0.41022, billing 0.93878) are recorded but not gated on: their token counts (38 and 106)
# do not fit the pinned code's prompt layout (55 and 98), so they look like an older layout's output
sh -c "$SERVE" > "$S/check.log" 2>&1 & pid=$!
until curl -sf http://127.0.0.1:8015/v1/models >/dev/null; do sleep 3; kill -0 $pid 2>/dev/null || { cat "$S/check.log"; exit 1; }; done
curl -s http://127.0.0.1:8015/v1/systemone -H 'content-type: application/json' -d '{"state":"Customer: my invoice was charged twice and nobody answers the phone!","questions":{"urgency":{"type":"noul","instructions":"Is this urgent?"},"department":{"type":"choice","instructions":"Which team should handle this?","criteria":{"billing":"Charges, invoices, refunds","technical":"Bugs and outages"}},"frustration":{"type":"score","instructions":"How frustrated is the customer?","criteria":["Calm","Frustrated","Very angry"]}}}' > "$OUT/readme-quickstart.json"
curl -s http://127.0.0.1:8015/v1/systemone -H 'content-type: application/json' -d '{"state":"What causes tides on Earth?","questions":{"rank":{"type":"choice","criteria":{"0":"The Moon'"'"'s gravitational pull.","1":"Photosynthesis in plants.","2":"Because the Earth is round."}}}}' > "$OUT/card-tides.json"
pkill -f "clm_embedder.py 8091" || true; pkill -f "clm-serve --host 127.0.0.1 --port 8015" || true; sleep 5
python3 -c "
import json, sys
q = json.load(open('$OUT/readme-quickstart.json'))['answers']
p = json.load(open('$OUT/card-tides.json'))['answers']['rank']['probabilities']['0']
print('quickstart (README 0.41022, 0.93878, 1.98386):', round(q['urgency']['noul'], 5), round(q['department']['probabilities']['billing'], 5), round(q['frustration']['score'], 5))
print('tides (model card 0.993):', round(p, 5))
sys.exit(abs(p - 0.993) > 0.002)
" || { echo "model card check failed; weights kept in $S for a look"; exit 3; }
for C in v1 extra nostranger; do
  python3 run/drive.py clm-8b --cells $C --port 8015 --cwd "$S/code/CLM" --code-repo https://github.com/Contrastive-LM/CLM --code-commit $CODE --runtime "$RT" -- sh $here/run/clm_serve.sh 8015 8091 $QWEN $CKPT $S/code/CLM/.venv/bin/python 2>&1 | grep -v "00/[0-9]* median"
  sfx=$([ $C = v1 ] && echo "" || echo "-$C")
  for f in results/raw/clm-8b$sfx.jsonl results/raw/clm-8b$sfx.summary.json results/raw/clm-8b$sfx.server.log results/meta/clm-8b$sfx.json; do [ -e $f ] && mv $f "$OUT/"; done
done
"$here/run/cleanup.sh" clm-8b "$S/code/CLM" "$S/uvcache-clm" "$S/hf"
