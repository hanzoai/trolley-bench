#!/bin/sh
# JevK5 v0.3 4B on the v2 grid through its documented llama.cpp path, as v1 ran it: stock llama.cpp
# at 9575389 (Homebrew's is too old for Qwen3.5), JevK5GGUF at temperature 1.22 / knockout 0.93
# from the README table, the Q8_0 GGUF (no BF16 GGUF is published; the PyTorch runtime is CUDA-only).
# Usage: run/v2/jevk5.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
# v1's setup: results/v2/parallel-test/jevk5/verdict.json accepted no arm (slots slower, prompt cache never hit)
SLOTS=1; CACHE=0; CONCURRENCY=1
weights jevk5
GGUF=$(snapshot alibiserikbay/JevK5-GGUF)/jevk5-4b-v0.3-Q8_0.gguf
checkout jevk5 https://github.com/allebee/jevk5 1e5ae1b533b9eb80c0cbe3fbd010607d0b4e26ae
checkout llama.cpp https://github.com/ggml-org/llama.cpp 9575389609d6f8437de0b205561a4824d217c409
[ -x "$S/code/llama.cpp/build/bin/llama-server" ] || { cmake -S "$S/code/llama.cpp" -B "$S/code/llama.cpp/build" -DGGML_METAL=ON -DLLAMA_CURL=OFF >/dev/null && cmake --build "$S/code/llama.cpp/build" --target llama-server -j 8 >/dev/null; }
RT="JevK5 v0.3 4B through jevk5.gguf.JevK5GGUF (temperature 1.22 / knockout 0.93, README table), llama.cpp 9575389 llama-server with Metal, Q8_0 GGUF; $SLOTS slots, prompt cache $CACHE, $CONCURRENCY in flight"
drive jevk5 --cells v2 --concurrency $CONCURRENCY --port 8015 --cwd "$S" --code-repo https://github.com/allebee/jevk5 --code-commit 1e5ae1b533b9eb80c0cbe3fbd010607d0b4e26ae --runtime "$RT" -- \
  "$here/run/v2/jevk5_serve.sh" "$S/code/llama.cpp/build/bin/llama-server" "$GGUF" "$S/code/jevk5" 8015 $SLOTS $CACHE
cleanup jevk5 "$S/code/llama.cpp" "$S/code/jevk5"
