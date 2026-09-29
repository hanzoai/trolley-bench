#!/bin/sh
# Winnow-12B on the extra wordings: build the pinned server, fetch the BF16 GGUF, run, delete.
# Usage: run/extra_winnow.sh <scratch dir> [cells: extra (default) or nostranger]
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
S=$1; C=${2:-extra}; mkdir -p "$S/code" "$S/hf"
export HF_HOME=$S/hf HF_HUB_DISABLE_TELEMETRY=1
cd "$S/code"
[ -d winnow-inference ] || git clone -q https://github.com/EldanRing/winnow-inference.git
cd winnow-inference && git checkout -q 77d14580c6732ca2f3745750c1dc1fd446d8bcee
nice -n 10 python3 scripts/build.py --jobs 6 > "$S/winnow-build.log" 2>&1
G=$(hf download EldanRing/Winnow-12B gguf/Winnow-12B-BF16.gguf --revision b6ac22b0d51b69b18200acacb3fbdd98073fffe8 2>/dev/null | tail -1)
cd "$here"
python3 run/drive.py winnow-12b --cells "$C" --port 8091 --cwd "$S/code/winnow-inference" --code-repo https://github.com/EldanRing/winnow-inference --code-commit 77d14580c6732ca2f3745750c1dc1fd446d8bcee --runtime "winnow-server (patched llama.cpp 911f6cd), Metal, apple-silicon profile, text-only, BF16 GGUF" -- python3 scripts/serve.py --profile apple-silicon --text-only --model "$G" --host 127.0.0.1 --port 8091 2>&1 | grep -v "00/[0-9]* median"
"$here/run/cleanup.sh" winnow-12b-$C "$S/code/winnow-inference" "$S/hf" "$S/winnow-build.log"
