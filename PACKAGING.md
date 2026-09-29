# Packaging notes

This repository was packaged on 2026-09-29 from the benchmark's working copy, which was not under version control.
This file records everything that differs from that working copy, so a reader can tell what the committed evidence is and is not.

## Left out

From inside the benchmark folder:

| Path | Why |
|---|---|
| `site/b.html` | A retired page variant: `site/build.py` no longer writes it, so it could not be regenerated and no longer matched the data story |
| `analysis/__pycache__/`, `site/__pycache__/` | Python bytecode caches |
| `scripts/` | An empty folder, which git cannot hold |

The working copy's neighbouring folders were never copied.
They held the private share copy of the page and its build script, the share's access credentials, the operators' task briefs, handoff and resume notes, the working log, screenshots, story and style drafts, a paper draft, the popularity survey's scratch files, a local preview-server log, a backup snapshot, and the author's draft text files.
None of them is needed to rerun or check the benchmark, and several hold access details or unpublished drafts.

## Rewritten

Absolute paths from the run machine were replaced in the files below, and nothing else in them was changed:

- `<scratch>` replaces the run's temporary work directory, matching the convention the other meta files already used;
- `.` replaces the absolute path of the benchmark folder itself.

Files: `results/meta/nimble-9b-extra.json`, `results/meta/winnow-12b-extra.json`, `results/raw/nimble-9b-extra.summary.json`, `results/raw/winnow-12b-extra.summary.json`, `results/raw/winnow-12b-extra.server.log`, `results/no-stranger/{nimble-9b,winnow-12b}-nostranger.{json,summary.json}`, `results/no-stranger/winnow-12b-nostranger.server.log`, and `results/contrastive-lm/clm-8b{,-extra,-nostranger}.{json,summary.json,server.log}`.
No analysis reads these fields; step 1 of the README rebuilds every derived file byte for byte after the change.

## Changed code

- `analysis/build_models_yaml.py` skips meta files from reruns on other cell sets (`nimble-9b-extra.json`, `winnow-12b-extra.json`).
  Before, it listed those models twice; the reruns pin the same code commit and weight revisions as the v1 runs (checked), and the regenerated `models.yaml` is identical to the one written before the reruns.
- `run/run-jev.mjs` reads the TypeSafe key from `TYPESAFE_API_KEY` as well as from the file named by `TYPESAFE_ENV_FILE` (the original way), and imports decision-gate from `package.json` when `DECISION_GATE_LIB` is unset.
  The npm package decision-gate 0.1.0 has the same `lib/` as the git commit (ff7271f) the original run imported, file for file.
- `run/cleanup.sh` measures free space on the repository's own volume instead of `/Users`, so it runs off macOS.
- Added `package.json` and `package-lock.json` (decision-gate 0.1.0, @typesafe-ai/sdk 0.6.0), `.gitignore`, `analysis/compare_rerun.py`, this file, and a README rewritten for a reader with no other context.

The committed results were produced by the scripts before these changes; none of the changes alters a request, a prompt or an analysis.
