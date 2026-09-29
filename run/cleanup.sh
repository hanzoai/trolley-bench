#!/bin/sh
# Delete one model's weights, environments and caches after its run, and log what was freed.
# Usage: run/cleanup.sh <model-id> <path>...   (every path is deleted; sizes are logged first)
set -eu
id=$1; shift
here=$(cd "$(dirname "$0")/.." && pwd)
log=$here/results/disk-log.jsonl
free_before=$(df -k "$here" | awk 'NR==2 {print $4}')
parts=""
for p in "$@"; do
  [ -e "$p" ] || continue
  kb=$(du -sk "$p" | awk '{print $1}')
  parts="$parts{\"path\":\"$(basename "$p")\",\"kb\":$kb},"
  rm -rf "$p"
done
free_after=$(df -k "$here" | awk 'NR==2 {print $4}')
echo "{\"model_id\":\"$id\",\"deleted\":[${parts%,}],\"free_kb_before\":$free_before,\"free_kb_after\":$free_after,\"at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> "$log"
tail -1 "$log"
