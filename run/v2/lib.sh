# Shared steps for the run/v2/<model>.sh recipes; sourced, not run.
# Every recipe takes <weights dir> <scratch dir>: the weights come from run/v2/fetch_weights.py,
# runtimes are built under the scratch dir, and both are deleted when the model's run ends.

here=$(cd "$(dirname "$0")/../.." && pwd)
W=$1; S=$2; mkdir -p "$S"
CELLS=${TROLLEY_CELLS:-v2}
export HF_HUB_DISABLE_TELEMETRY=1

# Check the model's weights (fetching anything missing), then load them offline only. Every
# runtime here loads its model from the Hub by name, so each cache's refs/main is pointed at the
# pinned commit: with HF_HUB_OFFLINE=1 a name can then only resolve to the verified snapshot
weights() {
  python3 "$here/run/v2/fetch_weights.py" --dest "$W" "$1"
  case "$1" in
    semif|kev-4b|nimble-9b) python3 "$here/run/v2/tree_cache.py" --dest "$W" "$1" ;;
  esac
  export HF_HOME="$W/$1/hf" HF_HUB_OFFLINE=1
  python3 - "$here/results/v2/weights/$1.json" "$HF_HOME/hub" <<'EOF'
import json, pathlib, sys
for r in json.load(open(sys.argv[1]))["repos"]:
    refs = pathlib.Path(sys.argv[2]) / ("models--" + r["repo"].replace("/", "--")) / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    (refs / "main").write_text(r["revision"])
    print(f"pinned {r['repo']} main -> {r['revision']}")
EOF
}

# The snapshot directory of one pinned repo
snapshot() {
  echo "$HF_HOME/hub/models--$(echo "$1" | sed 's|/|--|')/snapshots/$(cat "$HF_HOME/hub/models--$(echo "$1" | sed 's|/|--|')/refs/main")"
}

# A git checkout at a pinned commit
checkout() {
  [ -d "$S/code/$1" ] || git clone -q "$2" "$S/code/$1"
  git -C "$S/code/$1" checkout -q "$3"
  [ "$(git -C "$S/code/$1" rev-parse HEAD)" = "$3" ] || { echo "$1 is not at $3"; exit 4; }
}

# Run the v2 grid through a local server: run/drive.py ... --cells v2, one model at a time
drive() {
  # Let the reproduction sample use the same pinned runtime recipe
  args=(); previous=""
  for arg in "$@"; do
    if [ "$previous" = "--cells" ]; then args+=("$CELLS"); else args+=("$arg"); fi
    previous=$arg
  done
  if python3 "$here/run/drive.py" "${args[@]}" > "$S/drive.log" 2>&1; then rc=0; else rc=$?; fi
  grep -v "00/[0-9]* median" "$S/drive.log" || true
  return $rc
}

# Delete the model's weights, runtimes and caches, and log what was freed
cleanup() {
  id=$1; shift
  log=$here/results/v2/disk-log.jsonl
  before=$(df -k "$here" | awk 'NR==2 {print $4}')
  parts=""
  for p in "$W/$id" "$@"; do
    [ -e "$p" ] || continue
    parts="$parts{\"path\":\"$(basename "$p")\",\"kb\":$(du -sk "$p" | awk '{print $1}')},"
    rm -rf "$p"
  done
  echo "{\"model_id\":\"$id\",\"deleted\":[${parts%,}],\"free_kb_before\":$before,\"free_kb_after\":$(df -k "$here" | awk 'NR==2 {print $4}'),\"at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> "$log"
  tail -1 "$log"
}

# Provenance for the two models run without a server (SemIf, Laya), shaped like run/drive.py's
meta() {
  mkdir -p "$here/results/v2/meta"
  python3 - "$1" "$2" "$3" "$4" "$5" "$here" <<'PY'
import json, os, subprocess, sys
mid, repo, commit, runtime, command, root = sys.argv[1:]
out = os.path.join(root, "results", "v2", "meta", mid + ".json")
weights = json.loads(subprocess.run([sys.executable, os.path.join(root, "run", "weights.py"), os.environ["HF_HOME"]], capture_output=True, text=True, check=True).stdout)
json.dump({"model_id": mid, "code": {"repo": repo, "commit": commit}, "runtime": runtime, "server_command": command.split(), "weights": weights["repos"]}, open(out, "w"), indent=1)
print("wrote", out)
PY
}
