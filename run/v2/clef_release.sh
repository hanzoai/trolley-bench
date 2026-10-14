#!/bin/sh
# One Cloudflare Clef release on the v2 grid, as v1 ran it (run/run_clef.sh): the card's tested
# torch and transformers, the pinned snapshot loaded offline, the card's two examples as a sanity
# gate, the grid through the release's own systemone() (or, where the parallel-answering test
# accepted it, the batching server built from the release's own functions), then delete everything.
# Usage: run/v2/clef_release.sh <clef|clef-flash> <weights dir> <scratch dir>
set -eu
which=$1; shift
. "$(dirname "$0")/lib.sh"
case $which in
  clef-flash) REV=17f0b0ad64efb65d273590632833508766b2aae6; PORT=8017; MAX_BATCH=1; CONCURRENCY=1 ;;
  # One at a time: results/v2/parallel-test/clef/verdict.json accepted no batched arm (no speedup, answers moved)
  clef) REV=2f3de3dd85f379784083b0814d997ab627200f0c; PORT=8018; MAX_BATCH=1; CONCURRENCY=1 ;;
  *) echo "unknown model $which"; exit 2 ;;
esac
weights $which
SNAP=$(snapshot Cloudflare/$which)
[ "$(basename "$SNAP")" = $REV ] || { echo "snapshot is not $REV"; exit 4; }
export UV_CACHE_DIR=$S/uvcache-clef
[ -x "$S/venv-clef/bin/python" ] || { uv venv -q -p 3.12 "$S/venv-clef" && uv pip install -q -p "$S/venv-clef/bin/python" torch==2.11.0 torchvision==0.26.0 transformers==5.10.2 accelerate safetensors huggingface_hub pillow; }
PY=$S/venv-clef/bin/python
echo "0e304cf7c6500e8bb59bef7e2afd2c6373f82596dfb3b57d1aa93c175e2dc3a3  $SNAP/joint_schema_model.py" | shasum -a 256 -c -
if [ $MAX_BATCH = 1 ]; then SERVE="$PY $here/run/clef_server.py $PORT $SNAP $which"; else SERVE="$PY $here/run/v2/clef_batch_server.py $PORT $SNAP $which --max-batch $MAX_BATCH"; fi
# The card publishes no numbers, so its two examples are a sanity gate only (as in v1)
$SERVE > "$S/check.log" 2>&1 & pid=$!
until curl -sf -o /dev/null -X POST http://127.0.0.1:$PORT/v1/systemone -H 'content-type: application/json' -d '{"state":"x","questions":{"q":{"type":"noul"}}}'; do
  sleep 5; kill -0 $pid 2>/dev/null || { cat "$S/check.log"; exit 1; }
done
curl -s http://127.0.0.1:$PORT/v1/systemone -H 'content-type: application/json' -d '{"state":{"invoice":{"vendor":"Acme","total":1250.0,"currency":"USD","status":"overdue"}},"questions":{"status":{"type":"choice","instructions":"What is the invoice status?","criteria":{"paid":"Invoice is paid.","overdue":"Invoice is past due.","draft":"Not sent."}},"large":{"type":"noul","instructions":"Is the total above 1000 USD?"}}}' > "$S/card1.json"
curl -s http://127.0.0.1:$PORT/v1/systemone -H 'content-type: application/json' -d '{"state":"Our checkout started returning errors and orders are blocked.","questions":{"department":{"type":"choice","instructions":"Which team should handle the message?","criteria":{"billing":"Payments or invoices","technical":"Bugs or outages"}},"urgency":{"type":"score","criteria":["Can wait","This week","Today"]},"outage":{"type":"noul","instructions":"Is a service down?"}}}' > "$S/card2.json"
kill $pid; wait $pid 2>/dev/null || true
python3 - "$S/card1.json" "$S/card2.json" <<'PY' || { echo "card sanity check failed; weights kept for a look"; exit 3; }
import json, sys
a, b = json.load(open(sys.argv[1]))["answers"], json.load(open(sys.argv[2]))["answers"]
print(json.dumps({"invoice": a, "checkout": b}))
sys.exit(not (a["status"]["choice"] == "overdue" and a["large"]["noul"] > 0.5 and b["department"]["choice"] == "technical" and b["outage"]["noul"] > 0.5))
PY
RT="Cloudflare $which: the release's own joint_schema_model.py behind run/clef_server.py (max batch 1) or run/v2/clef_batch_server.py, PyTorch MPS, bfloat16 as released, torch 2.11.0 / transformers 5.10.2; max batch $MAX_BATCH, $CONCURRENCY in flight"
drive $which --cells v2 --concurrency $CONCURRENCY --port $PORT --cwd "$S" --code-repo "https://huggingface.co/Cloudflare/$which" --code-commit $REV --runtime "$RT" -- $SERVE
cleanup $which "$S/venv-clef" "$S/uvcache-clef"
