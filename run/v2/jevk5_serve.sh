#!/bin/sh
# llama-server with the JevK5 GGUF and N parallel slots on 127.0.0.1, then the v2 /v1/systemone
# front; both share this process group, so the caller stops them together.
# Usage: run/v2/jevk5_serve.sh <llama-server> <gguf> <jevk5 clone> <port> <slots> <cache 0|1>
set -eu
here=$(cd "$(dirname "$0")" && pwd)
slots=$5
# v1 ran one slot with an 8,192-token context; each slot keeps that context
"$1" -m "$2" -c $((8192 * slots)) -np "$slots" -ngl 99 --host 127.0.0.1 --port 8096 &
until curl -sf http://127.0.0.1:8096/health >/dev/null; do sleep 2; done
JEVK5_CACHE_PROMPT=$6 PYTHONPATH="$3" exec python3 "$here/jevk5_server.py" "$4" http://127.0.0.1:8096
