#!/bin/sh
# Start llama-server with the JevK5 GGUF on 127.0.0.1, then the /v1/systemone front; both share
# this process group, so run/drive.py stops them together.
# Usage: run/jevk5_serve.sh <llama-server> <gguf> <jevk5 clone> <port>
set -eu
here=$(cd "$(dirname "$0")" && pwd)
"$1" -m "$2" -c 8192 -ngl 99 --host 127.0.0.1 --port 8096 &
until curl -sf http://127.0.0.1:8096/health >/dev/null; do sleep 2; done
PYTHONPATH="$3" exec python3 "$here/jevk5_server.py" "$4" http://127.0.0.1:8096
