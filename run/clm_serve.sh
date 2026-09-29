#!/bin/sh
# CLM's own server on the local encoder: start clm_embedder.py, wait for it, then clm-serve with the
# pinned head, both bound to 127.0.0.1. drive.py stops the whole process group when the grid ends.
# Usage: run/clm_serve.sh <port> <encoder port> <Qwen3-8B snapshot> <head .pt> <venv python>
set -eu
port=$1; emb=$2; qwen=$3; ckpt=$4; py=$5
here=$(cd "$(dirname "$0")/.." && pwd)
"$py" "$here/run/clm_embedder.py" "$emb" "$qwen" &
until curl -sf "http://127.0.0.1:$emb/v1/models" >/dev/null; do sleep 2; done
exec "$(dirname "$py")/clm-serve" --host 127.0.0.1 --port "$port" --emb-url "http://127.0.0.1:$emb/v1/embeddings" \
  --emb-model qwen3-8b --ckpt "$ckpt" --device cpu --action-cache 0 --no-download --no-ui
