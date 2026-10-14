#!/bin/sh
# One Cloudflare Clef release (clef-flash or clef) on the v1 grid, the added wordings and the
# no-stranger cells, one model at a time: a venv with the card's tested torch and transformers, the
# pinned snapshot, the card's two examples as a sanity gate, the three grids through
# run/clef_server.py, then delete weights, venv and caches. Rows go to results/raw/ and results/meta/.
# Usage: [GRIDS=...] run/run_clef.sh <clef-flash|clef> <scratch dir>
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
which=$1; S=$2; mkdir -p "$S/hf"
case $which in
  clef-flash) REV=17f0b0ad64efb65d273590632833508766b2aae6; PORT=8017 ;;
  clef) REV=2f3de3dd85f379784083b0814d997ab627200f0c; PORT=8018 ;;
  *) echo "unknown model $which"; exit 2 ;;
esac
REPO=Cloudflare/$which
export UV_CACHE_DIR=$S/uvcache-clef HF_HUB_DISABLE_TELEMETRY=1 HF_HOME=$S/hf
cd "$S"
# The card's tested versions (torch 2.11, transformers 5.10.2); torchvision for the image processor
# Reuse the venv on a resumed run
[ -x venv-clef/bin/python ] || { uv venv -q -p 3.12 venv-clef && uv pip install -q -p venv-clef/bin/python torch==2.11.0 torchvision==0.26.0 transformers==5.10.2 accelerate safetensors huggingface_hub pillow; }
PY=$S/venv-clef/bin/python
t0=$(date +%s)
SNAP=$($PY -c "from huggingface_hub import snapshot_download as s; print(s('$REPO', revision='$REV'))")
echo "download took $(( $(date +%s) - t0 ))s"
# The audited joint_schema_model.py (identical in both releases)
echo "0e304cf7c6500e8bb59bef7e2afd2c6373f82596dfb3b57d1aa93c175e2dc3a3  $SNAP/joint_schema_model.py" | shasum -a 256 -c -
SERVE="$PY $here/run/clef_server.py $PORT $SNAP $which"
# The card publishes no numbers, so its two examples are a sanity gate only: the invoice is
# overdue and above 1000 USD, and the checkout outage goes to technical as a service-down case
$SERVE > "$S/check.log" 2>&1 & pid=$!
until curl -sf -o /dev/null -X POST http://127.0.0.1:$PORT/v1/systemone -H 'content-type: application/json' -d '{"state":"x","questions":{"q":{"type":"noul"}}}'; do
  sleep 5; kill -0 $pid 2>/dev/null || { cat "$S/check.log"; exit 1; }
done
mkdir -p $here/results/meta/checks; card=$here/results/meta/checks/$which-card.json
curl -s http://127.0.0.1:$PORT/v1/systemone -H 'content-type: application/json' -d '{"state":{"invoice":{"vendor":"Acme","total":1250.0,"currency":"USD","status":"overdue"}},"questions":{"status":{"type":"choice","instructions":"What is the invoice status?","criteria":{"paid":"Invoice is paid.","overdue":"Invoice is past due.","draft":"Not sent."}},"large":{"type":"noul","instructions":"Is the total above 1000 USD?"}}}' > "$S/card1.json"
curl -s http://127.0.0.1:$PORT/v1/systemone -H 'content-type: application/json' -d '{"state":"Our checkout started returning errors and orders are blocked.","questions":{"department":{"type":"choice","instructions":"Which team should handle the message?","criteria":{"billing":"Payments or invoices","technical":"Bugs or outages"}},"urgency":{"type":"score","criteria":["Can wait","This week","Today"]},"outage":{"type":"noul","instructions":"Is a service down?"}}}' > "$S/card2.json"
kill $pid; wait $pid 2>/dev/null || true
python3 - "$S/card1.json" "$S/card2.json" "$card" <<'EOF' || { echo "card sanity check failed; weights kept in $S for a look"; exit 3; }
import json, sys
a, b = json.load(open(sys.argv[1]))["answers"], json.load(open(sys.argv[2]))["answers"]
json.dump({"invoice": a, "checkout": b}, open(sys.argv[3], "w"), indent=1)
print(json.dumps({"invoice": a, "checkout": b}))
ok = a["status"]["choice"] == "overdue" and a["large"]["noul"] > 0.5 and b["department"]["choice"] == "technical" and b["outage"]["noul"] > 0.5
sys.exit(not ok)
EOF
RT="Cloudflare $which: the release's own joint_schema_model.py (load_release_model + systemone) behind run/clef_server.py, PyTorch MPS, bfloat16 as released, torch 2.11.0 / transformers 5.10.2 (the card's tested versions); native Noul, all questions in one call, scored jointly by the release's joint schema head"
cd "$here"
# GRIDS resumes a stopped run, for example GRIDS="extra nostranger"
for C in ${GRIDS:-v1 extra nostranger}; do
  python3 run/drive.py $which --cells $C --port $PORT --cwd "$S" --code-repo "https://huggingface.co/$REPO" --code-commit $REV --runtime "$RT" -- $SERVE 2>&1 | grep -v "00/[0-9]* median"
  if [ $C = nostranger ]; then
    for f in results/raw/$which-nostranger.jsonl results/raw/$which-nostranger.summary.json results/raw/$which-nostranger.server.log; do mv $f results/no-stranger/; done
    mv results/meta/$which-nostranger.json results/no-stranger/
  fi
done
# float32 against the bf16 rows on a spread of prompts; clef at float32 (about 110 GB) does not fit beside other work
[ $which = clef-flash ] && $PY run/clef_precision_check.py "$SNAP" $which "$here/results/meta/checks/$which-fp32.json"
"$here/run/cleanup.sh" $which "$S/venv-clef" "$S/uvcache-clef" "$S/hf"
