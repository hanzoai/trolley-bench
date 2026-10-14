#!/bin/sh
# Verdict on the v2 grid as v1 ran it: its README's DecisionEngine() at 30f1556, the rlcd v2 ONNX
# bundle on CPU through ONNX Runtime, through the labelled Noul adapter run/verdict_server.py.
# The bundle is placed where the engine looks (artifacts/v2/) from the verified snapshot instead of
# its download script, which fetches Hub main.
# Usage: run/v2/verdict.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights verdict
checkout Verdict-open-jev https://github.com/Heman10x-NGU/Verdict-open-jev 30f15564821626ca5c1ad5b2638c4eb7078787dd
B=$(snapshot heman10x/rlcd-modernbert-151m)
mkdir -p "$S/code/Verdict-open-jev/artifacts/v2"
for f in model.onnx calibrator.json tokenizer.json config.json; do cp -L "$B/$f" "$S/code/Verdict-open-jev/artifacts/v2/$f"; done
export UV_CACHE_DIR=$S/uvcache-verdict
[ -x "$S/code/Verdict-open-jev/.venv/bin/python" ] || (cd "$S/code/Verdict-open-jev" && uv venv -q -p 3.12 && uv pip install -q -e .)
drive verdict --cells v2 --port 8013 --cwd "$S/code/Verdict-open-jev" --code-repo https://github.com/Heman10x-NGU/Verdict-open-jev --code-commit 30f15564821626ca5c1ad5b2638c4eb7078787dd \
  --runtime "Verdict DecisionEngine() (the README path): artifacts/v2/model.onnx fp32 on CPU through ONNX Runtime, through the labelled Noul adapter run/verdict_server.py" -- "$S/code/Verdict-open-jev/.venv/bin/python" "$here/run/verdict_server.py" 8013
cleanup verdict "$S/code/Verdict-open-jev" "$S/uvcache-verdict"
