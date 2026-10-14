#!/bin/sh
# Winnow-12B on the v2 grid as v1 ran it: winnow-server at 77d1458 (its build pins and checks the
# patched llama.cpp commit and patches), Metal, apple-silicon profile, text-only, BF16 GGUF.
# Usage: run/v2/winnow-12b.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights winnow-12b
GGUF=$(snapshot EldanRing/Winnow-12B)/gguf/Winnow-12B-BF16.gguf
checkout winnow-inference https://github.com/EldanRing/winnow-inference 77d14580c6732ca2f3745750c1dc1fd446d8bcee
(cd "$S/code/winnow-inference" && python3 scripts/build.py --jobs 8)
drive winnow-12b --cells v2 --port 8091 --cwd "$S/code/winnow-inference" --code-repo https://github.com/EldanRing/winnow-inference --code-commit 77d14580c6732ca2f3745750c1dc1fd446d8bcee \
  --runtime "winnow-server (patched llama.cpp 911f6cd), Metal, apple-silicon profile, text-only, BF16 GGUF" -- \
  python3 scripts/serve.py --profile apple-silicon --text-only --model "$GGUF" --host 127.0.0.1 --port 8091
cleanup winnow-12b "$S/code/winnow-inference"
