#!/bin/sh
# Von 1.2 on the v2 grid as v1 ran it: von serve at fb6e7a9 from its own uv.lock, PyTorch MPS, fp32.
# Usage: run/v2/von.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights von
checkout von https://github.com/wfzyx/von fb6e7a937e4fc6b6e72b2ce5035edd56bc370e54
export UV_CACHE_DIR=$S/uvcache-von
(cd "$S/code/von" && uv sync -q --frozen)
drive von --cells v2 --port 8012 --cwd "$S/code/von" --code-repo https://github.com/wfzyx/von --code-commit fb6e7a937e4fc6b6e72b2ce5035edd56bc370e54 \
  --runtime "von serve (von-sdk at the commit), Von 1.2, PyTorch MPS, fp32 as released" -- "$S/code/von/.venv/bin/von" serve --host 127.0.0.1 --port 8012 --model von-1.2 --device mps
cleanup von "$S/code/von" "$S/uvcache-von"
