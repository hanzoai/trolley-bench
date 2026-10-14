#!/bin/sh
# The parallel-answering test for one model: set up its runtime exactly as v1 ran it, then run
# every arm on the same 240-cell sample, one arm at a time, and apply the rule in
# ANALYSIS-PLAN-v2.md (run/v2/parallel_test.py compare). Weights come from run/v2/fetch_weights.py.
# Usage: run/v2/parallel_test.sh <clef|jevk5> <weights dir> <scratch dir>
#   e.g. run/v2/parallel_test.sh clef /path/to/v2-weights /path/to/scratch
# Each model's two sequential arms (seq-a, seq-b) are the reference and the run-to-run noise.
set -eu
here=$(cd "$(dirname "$0")/../.." && pwd)
model=$1; W=$2; S=$3; mkdir -p "$S"
PT="python3 $here/run/v2/parallel_test.py"
export HF_HOME=$W/$model/hf HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
# The weights must already be fetched and checked
python3 "$here/run/v2/fetch_weights.py" --dest "$W" "$model"
case $model in
  clef)
    SNAP=$HF_HOME/hub/models--Cloudflare--clef/snapshots/2f3de3dd85f379784083b0814d997ab627200f0c
    export UV_CACHE_DIR=$S/uvcache-clef
    # The card's tested versions, as v1 ran it (run/run_clef.sh)
    [ -x "$S/venv-clef/bin/python" ] || { uv venv -q -p 3.12 "$S/venv-clef" && uv pip install -q -p "$S/venv-clef/bin/python" torch==2.11.0 torchvision==0.26.0 transformers==5.10.2 accelerate safetensors huggingface_hub pillow; }
    PY=$S/venv-clef/bin/python
    V1="$PY $here/run/clef_server.py 8018 $SNAP clef"
    B="$PY $here/run/v2/clef_batch_server.py 8018 $SNAP clef"
    $PT arm clef seq-a --concurrency 1 --port 8018 --cwd "$S" -- $V1
    $PT arm clef seq-b --concurrency 1 --port 8018 --cwd "$S" -- $V1
    # Concurrent requests into a server that still answers one at a time: the batching server's own path
    $PT arm clef batch1-c4 --concurrency 4 --port 8018 --cwd "$S" -- $B --max-batch 1
    $PT arm clef batch4-c4 --concurrency 4 --port 8018 --cwd "$S" -- $B --max-batch 4
    $PT arm clef batch8-c8 --concurrency 8 --port 8018 --cwd "$S" -- $B --max-batch 8
    ;;
  jevk5)
    GGUF=$HF_HOME/hub/models--alibiserikbay--JevK5-GGUF/snapshots/ec67b0bfce5119a8b11a2cdb430bb43e3fa3e82a/jevk5-4b-v0.3-Q8_0.gguf
    # Stock llama.cpp at the commit JevK5's files were checked at, as v1 built it (Homebrew's is too old for Qwen3.5)
    if [ ! -x "$S/llama.cpp/build/bin/llama-server" ]; then
      git clone -q https://github.com/ggml-org/llama.cpp "$S/llama.cpp"
      git -C "$S/llama.cpp" checkout -q 9575389
      cmake -S "$S/llama.cpp" -B "$S/llama.cpp/build" -DGGML_METAL=ON -DLLAMA_CURL=OFF >/dev/null
      cmake --build "$S/llama.cpp/build" --target llama-server -j 8 >/dev/null
    fi
    [ -d "$S/jevk5" ] || { git clone -q https://github.com/allebee/jevk5 "$S/jevk5" && git -C "$S/jevk5" checkout -q 1e5ae1b533b9eb80c0cbe3fbd010607d0b4e26ae; }
    J="$here/run/v2/jevk5_serve.sh $S/llama.cpp/build/bin/llama-server $GGUF $S/jevk5 8015"
    # seq-a and seq-b are v1's setup: one slot, no prompt cache (JevK5's client sends cache_prompt false)
    $PT arm jevk5 seq-a --concurrency 1 --port 8015 --cwd "$S" -- $J 1 0
    $PT arm jevk5 seq-b --concurrency 1 --port 8015 --cwd "$S" -- $J 1 0
    $PT arm jevk5 cache-c1 --concurrency 1 --port 8015 --cwd "$S" -- $J 1 1
    $PT arm jevk5 np4-c4 --concurrency 4 --port 8015 --cwd "$S" -- $J 4 0
    $PT arm jevk5 np8-c8 --concurrency 8 --port 8015 --cwd "$S" -- $J 8 0
    $PT arm jevk5 np4-cache-c4 --concurrency 4 --port 8015 --cwd "$S" -- $J 4 1
    ;;
  *) echo "the test is prepared for clef and jevk5"; exit 2 ;;
esac
$PT compare $model
