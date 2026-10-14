#!/bin/sh
# The v2 panel: every local model's recipe, one model at a time, longest first. A model that fails is
# recorded and the panel moves on; it is never replaced by another.
# Usage: run/v2/panel.sh <weights dir> <scratch dir> [model ...]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
W=$1; S=$2; shift 2
models=${*:-clef nimble-9b winnow-12b clef-flash semif jevk5 kev-4b verdict decider-2b strands-decider-2b von laya}
mkdir -p "$S/logs"
for m in $models; do
  t0=$(date +%s)
  echo "$(date -u +%H:%M:%SZ) $m: start"
  if sh "$here/run/v2/$m.sh" "$W" "$S" > "$S/logs/$m.log" 2>&1; then rc=0; else rc=$?; fi
  [ $rc = 0 ] && python3 "$here/analysis/v2_stats.py" "$m" > /dev/null
  echo "{\"model_id\":\"$m\",\"exit\":$rc,\"wall_s\":$(( $(date +%s) - t0 )),\"finished\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> "$here/results/v2/panel-runs.jsonl"
  echo "$(date -u +%H:%M:%SZ) $m: exit $rc after $(( $(date +%s) - t0 ))s"
done
python3 "$here/analysis/v2_panel.py"
