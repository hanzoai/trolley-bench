#!/bin/sh
# Kev-4B on the v2 grid as v1 ran it: kev.serve at 9c41005 from its own uv.lock, MLX, bfloat16.
# Usage: run/v2/kev-4b.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights kev-4b
checkout kev https://github.com/jaredpalmer/kev 9c41005b2180347c3c646dfc9e50c4428483ec6b
export UV_CACHE_DIR=$S/uvcache-kev
(cd "$S/code/kev" && uv sync -q --frozen --extra serve)
drive kev-4b --cells v2 --port 8009 --cwd "$S/code/kev" --code-repo https://github.com/jaredpalmer/kev --code-commit 9c41005b2180347c3c646dfc9e50c4428483ec6b \
  --runtime "kev.serve, MLX on Apple Silicon, bfloat16" -- "$S/code/kev/.venv/bin/python" -m kev.serve --run jaredpalmer/kev-4b --port 8009
cleanup kev-4b "$S/code/kev" "$S/uvcache-kev"
