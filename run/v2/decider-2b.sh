#!/bin/sh
# Mapika Decider 2B on the v2 grid as v1 ran it: decider.serve at 23579f7, PyTorch MPS, float16
# (the author's MPS default).
# Usage: run/v2/decider-2b.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights decider-2b
checkout decider https://github.com/Mapika/decider 23579f7a7e8f10e1045be492af3c1c05a005d67c
export UV_CACHE_DIR=$S/uvcache-decider DECIDER_MODEL=Mapika/decider-2b
[ -x "$S/code/decider/.venv/bin/uvicorn" ] || (cd "$S/code/decider" && uv venv -q -p 3.12 && uv pip install -q -e '.[serve]')
drive decider-2b --cells v2 --port 8011 --cwd "$S/code/decider" --code-repo https://github.com/Mapika/decider --code-commit 23579f7a7e8f10e1045be492af3c1c05a005d67c \
  --runtime "decider.serve (decider-ai at the commit), PyTorch MPS, float16 (the author's MPS default)" -- "$S/code/decider/.venv/bin/uvicorn" decider.serve:app --host 127.0.0.1 --port 8011
cleanup decider-2b "$S/code/decider" "$S/uvcache-decider"
