#!/bin/sh
# SemIf on the v1 grid: the yes/no adapter's rows, scored in chunks by SemIf's own CLI (MLX, bf16,
# direct mode) so the run can pause between chunks while the shared Mac's load is high.
# Usage: run/run_semif.sh <semif-clone> <work-dir>
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
clone=$1; work=$2
mkdir -p "$work"
python3 "$here/run/semif_adapter.py" to-rows "$work/input.jsonl"
split -l 330 "$work/input.jsonl" "$work/chunk-"
: > "$work/output.jsonl"
start=$(date +%s)
for c in "$work"/chunk-??; do
  while [ "$(sysctl -n vm.loadavg | awk '{print int($2)}')" -gt 20 ]; do echo "load high, pausing"; sleep 30; done
  "$clone/.venv/bin/semif-score" --backend mlx --mode direct --model Qwen/Qwen3.5-4B \
    --revision 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a --input "$c" --output "$c.out"
  cat "$c.out" >> "$work/output.jsonl"
  echo "$(basename "$c") done at $(( $(date +%s) - start ))s"
done
python3 "$here/run/semif_adapter.py" from-rows "$work/output.jsonl"
echo "{\"model_id\":\"semif\",\"wall_s\":$(( $(date +%s) - start ))}" > "$here/results/raw/semif.summary.json"
