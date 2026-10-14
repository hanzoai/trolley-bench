#!/bin/sh
# Laya, the untuned baseline, on the v2 grid as v1 ran it: laya 0.3.20 from PyPI, Router(preload=False)
# with the English checkpoint, PyTorch MPS, in process (run/run_local.py's laya engine).
# Usage: run/v2/laya.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights laya
export UV_CACHE_DIR=$S/uvcache-laya
[ -x "$S/venv-laya/bin/python" ] || { uv venv -q -p 3.12 "$S/venv-laya" && uv pip install -q -p "$S/venv-laya/bin/python" laya==0.3.20; }
meta laya "https://pypi.org/project/laya/0.3.20/ (github.com/NandhaKishorM/laya)" "laya==0.3.20 from PyPI" "laya Router(preload=False).predict(..., model='english'), PyTorch MPS, shipped checkpoint without fine-tuning" "run/run_local.py laya --name laya --cells v2"
"$S/venv-laya/bin/python" "$here/run/run_local.py" laya --name laya --cells "$CELLS" --meta "$here/results/v2/meta/laya.json"
cleanup laya "$S/venv-laya" "$S/uvcache-laya"
