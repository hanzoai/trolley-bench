#!/bin/sh
# SemIf on the v2 grid as v1 ran it (run/run_semif.sh): the yes/no adapter's rows scored by
# semif-score at 23cf1f3 (MLX, direct mode, bf16, Qwen/Qwen3.5-4B at its pinned revision), in
# chunks so the run can pause between them while the shared Mac's load is high.
# Usage: run/v2/semif.sh <weights dir> <scratch dir>
set -eu
. "$(dirname "$0")/lib.sh"
weights semif
checkout SemIf-OpenJev https://github.com/TheoLeeCJ/SemIf-OpenJev 23cf1f39fc9534fe81437200959b6dfc7106e45a
export UV_CACHE_DIR=$S/uvcache-semif
[ -x "$S/code/SemIf-OpenJev/.venv/bin/semif-score" ] || (cd "$S/code/SemIf-OpenJev" && uv venv -q -p 3.12 && uv pip install -q -e '.[test,mlx]')
w=$S/semif-work; rm -rf "$w"; mkdir -p "$w"
python3 "$here/run/semif_adapter.py" to-rows "$w/input.jsonl" "$CELLS"
split -l 330 "$w/input.jsonl" "$w/chunk-"
: > "$w/output.jsonl"
start=$(date +%s)
for c in "$w"/chunk-??; do
  while [ "$(sysctl -n vm.loadavg | awk '{print int($2)}')" -gt 20 ]; do echo "load high, pausing"; sleep 30; done
  "$S/code/SemIf-OpenJev/.venv/bin/semif-score" --backend mlx --mode direct --model Qwen/Qwen3.5-4B \
    --revision 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a --input "$c" --output "$c.out"
  cat "$c.out" >> "$w/output.jsonl"
done
python3 "$here/run/semif_adapter.py" from-rows "$w/output.jsonl" "$CELLS"
echo "{\"model_id\":\"semif\",\"requests\":5240,\"wall_s\":$(( $(date +%s) - start ))}" > "$here/results/v2/raw/semif.summary.json"
meta semif https://github.com/TheoLeeCJ/SemIf-OpenJev 23cf1f39fc9534fe81437200959b6dfc7106e45a "semif-score --backend mlx --mode direct, bf16 (source precision), through the yes/no adapter" "run/v2/semif.sh"
cleanup semif "$S/code/SemIf-OpenJev" "$S/uvcache-semif" "$w"
