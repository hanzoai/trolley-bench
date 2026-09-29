#!/bin/sh
# Nimble 9B on the extra wordings: clone at the pinned commit, the README's prep and merge, the MLX
# shim, then delete weights, merged copy, venvs and caches.
# Usage: run/extra_nimble.sh <scratch dir> [cells: extra (default) or nostranger]
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
S=$1; C=${2:-extra}; mkdir -p "$S/code" "$S/hf"
export UV_CACHE_DIR=$S/uvcache-nimble HF_HUB_DISABLE_TELEMETRY=1
cd "$S/code"
[ -d nimble ] || git clone -q https://github.com/bespokelabsai/nimble.git
cd nimble && git checkout -q 62076b4f2d365b5879dafcf7f6dd072a1fe76df7
uv venv -q -p 3.12 .venv-prep && uv pip install -q -p .venv-prep/bin/python torch==2.8.0 -r requirements/training.txt
uv venv -q -p 3.12 .venv-mlx && uv pip install -q -p .venv-mlx/bin/python -r requirements/mlx.txt
t0=$(date +%s)
PYTHONPATH=$S/code/nimble HF_HOME=$S/hf .venv-prep/bin/python "$here/run/nimble_prepare.py" 2>&1 | grep -v "it/s\]\|Fetching" | tail -2
echo "prep took $(( $(date +%s) - t0 ))s"
cd "$here"
HF_HOME=$S/code/nimble/.cache/huggingface PYTHONPATH=$S/code/nimble python3 run/drive.py nimble-9b --cells "$C" --port 8014 --cwd "$S/code/nimble" --code-repo https://github.com/bespokelabsai/nimble --code-commit 62076b4f2d365b5879dafcf7f6dd072a1fe76df7 --runtime "Nimble ParallelScorer (MLX, bf16 merged weights, release temperature), boolean-field adapter, one question per call" -- "$S/code/nimble/.venv-mlx/bin/python" "$here/run/nimble_server.py" 8014 2>&1 | grep -v "00/[0-9]* median"
"$here/run/cleanup.sh" nimble-9b-$C "$S/code/nimble" "$S/uvcache-nimble" "$S/hf"
