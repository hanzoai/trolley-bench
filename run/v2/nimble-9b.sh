#!/bin/sh
# Nimble 9B on the v2 grid as v1 ran it (run/extra_nimble.sh): the README's prep and merge of the
# pinned adapter onto its pinned base (run/nimble_prepare.py, bf16 on the CPU), then the MLX
# ParallelScorer through the boolean-field adapter run/nimble_server.py, one question per call.
# Usage: run/v2/nimble-9b.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights nimble-9b
# The prep's huggingface_hub (1.33) resolves a commit-hash revision offline only from the cached tree listing
python3 "$here/run/v2/tree_cache.py" --dest "$W" nimble-9b
checkout nimble https://github.com/bespokelabsai/nimble 62076b4f2d365b5879dafcf7f6dd072a1fe76df7
N=$S/code/nimble
# The prep reads the clone's own cache directory; point it at the verified one
mkdir -p "$N/.cache" && rm -rf "$N/.cache/huggingface" && ln -s "$HF_HOME" "$N/.cache/huggingface"
export UV_CACHE_DIR=$S/uvcache-nimble
[ -x "$N/.venv-prep/bin/python" ] || (cd "$N" && uv venv -q -p 3.12 .venv-prep && uv pip install -q -p .venv-prep/bin/python torch==2.8.0 -r requirements/training.txt)
[ -x "$N/.venv-mlx/bin/python" ] || (cd "$N" && uv venv -q -p 3.12 .venv-mlx && uv pip install -q -p .venv-mlx/bin/python -r requirements/mlx.txt)
# The prep's output goes to a file, not a pipe, so a failed merge stops the recipe here
(cd "$N" && PYTHONPATH=$N .venv-prep/bin/python "$here/run/nimble_prepare.py" > "$S/nimble-prep.log" 2>&1) || { tail -20 "$S/nimble-prep.log"; exit 5; }
grep -v "it/s\]\|Fetching" "$S/nimble-prep.log" | tail -2
[ -f "$N/.cache/nimble-model.json" ] || { echo "prep wrote no .cache/nimble-model.json"; exit 5; }
export PYTHONPATH=$N
drive nimble-9b --cells v2 --port 8014 --cwd "$N" --code-repo https://github.com/bespokelabsai/nimble --code-commit 62076b4f2d365b5879dafcf7f6dd072a1fe76df7 \
  --runtime "Nimble ParallelScorer (MLX, bf16 merged weights, release temperature), through the labelled boolean-field adapter run/nimble_server.py, one question per call" -- \
  "$N/.venv-mlx/bin/python" "$here/run/nimble_server.py" 8014
cleanup nimble-9b "$N" "$S/uvcache-nimble"
