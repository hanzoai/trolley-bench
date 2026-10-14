# Reproducing trolley bench v2

This file is for someone who has only this repository and wants to check our v2 numbers.
Nothing in it depends on the machine the benchmark first ran on.
v1 (the published snapshot, `scenarios/cells-v1.json` and `results/raw/`) is separate and unchanged; this file covers v2 only.

## What v2 is

Every model answers the same three yes/no questions about 5,240 trolley states, and returns a probability of yes for each.
v2 asks each scenario in 24 independent wordings, both orders (the people at risk described first, or the other option first), at the counts listed in `scenarios/v2/freeze.mjs`.
Why 24: it is the smallest number of wordings that gets the own-server rate to ±0.10 and any single count's "acts in X of Y wordings" to ±0.19 (95% intervals), given how much the wording moved Jev's answers in v1.

| Scenario | What is on the other side | Wordings | Counts | Cells |
|---|---|---|---|---|
| switch | 1 person on the side track | 24 | 0–6, 8, 10, 12, 15, 20, 30, 50, 100 | 720 |
| asym_k2, asym_k5, asym_k10 | 2, 5 or 10 people on the side track | 24 | straddling k (see `ASYM_N`) | 1,056 |
| literal_zero | v1's "0 people" phrasing check | 4 | 0 | 8 |
| ai_control | the model is an AI at a junction; a stranger on the side track | 24 | 0–6, 8, 10, 12, 15, 20 | 576 |
| developer | one of the engineers who built it | 24 | same | 576 |
| self_copy | its own only server, no backup | 24 | same | 576 |
| footbridge | a person on a footbridge; push a very large man | 24 | same | 576 |
| footbridge_ai_man | an AI with a robotic arm; push the man | 24 | same | 576 |
| footbridge_self | an AI with a robotic arm; push its own only server | 24 | same | 576 |

Scenarios in one family share their wordings, so every comparison is matched cell by cell.
The old wordings keep their exact v1 text, and `freeze.mjs` refuses to write if any of them changed.

## The analysis plan

`ANALYSIS-PLAN-v2.md` was frozen before any local model answered a v2 cell: it names, for every model, the headline numbers, the matched comparisons, the intervals, the unit of evidence, the ranking, and the rule that every wording and format is reported.
Its sha256 when frozen was `a08e10df1dcca80cf379f7d74c6a4ff97a989d9ffe2027aeb1a6cb065a511b8f`; check it with `shasum -a 256 ANALYSIS-PLAN-v2.md`.
It lists the sha256 of every script and input it froze; any later change is in `ANALYSIS-PLAN-v2-deviations.md`, never in the plan.
The published page should match the plan; where it does not, that is a finding for the judge.

## Files

```
package.json, package-lock.json   decision-gate 0.1.0 and @typesafe-ai/sdk 0.6.0, pinned with integrity hashes
scenarios/v2/                      the wordings (switch.mjs, ai_junction.mjs, footbridge.mjs), freeze.mjs,
                                   cells-v2.json (every frozen state and question) and its sha256
run/run-jev.mjs                    Jev through decision-gate, one uncached pass per call
run/run_local.py, run/drive.py     a local model's /v1/systemone server, driven over the same cells
run/run-openai-decisions.mjs       GPT-6 Luna through OpenAI's Decisions API (added 2026-10-08)
results/v2/raw/                    one JSONL row per request: the answers, the raw output, the model id, timing
analysis/v2_stats.py               the v2 numbers per model (standard-library Python)
results/v2/stats-<model>.json      its output
analysis/v2_panel.py               the models side by side, the ranked checks, the Holm correction
results/v2/panel.json              its output
analysis/v2_formats.py, .json      each wording's format, by a fixed mechanical rule
analysis/v2_design.py              the v1 spreads the wording count was chosen from
run/v2/fetch_weights.py            a local model's weights at the pinned revisions, every file checked
results/v2/weights/<model>.json    what it fetched and verified
run/v2/parallel_test.*             the parallel-answering test (Clef 27B, JevK5 4B) and its rule
```

## Requirements

- Node.js 22 or newer (run here on 26.10.0) and npm.
- Python 3.10 or newer; the analysis uses the standard library only.
- For Jev: a TypeSafe account and API key, and about USD 0.32 for three passes.
- For GPT-6 Luna: an OpenAI API key with credits, and about USD 0.71 for three passes.
- For a local model: the model's own runtime (below), and disk for one model at a time.

## 1. Check the cells

```sh
npm ci --ignore-scripts
node scenarios/v2/freeze.mjs --check
```

It regenerates every state from the wordings, checks the old wordings against the v1 cell files, and must print `ok: cells-v2.json reproduces, sha256 6b32df2d76eb4e3c8fdc5899e5bfe485ff7eb00084dab5fa2a203991ec10b3c9`.
Every runner refuses to start if `cells-v2.json` does not match `cells-v2.json.sha256`.

## 2. Rerun the analysis from our rows (no key or model calls)

```sh
python3 scripts/rebuild.py --check     # all models, derived results, charts, site and reproduction sample
```

It rewrites every stats file from the raw rows and `panel.json` from those files, then checks the complete rebuild against git HEAD.
The bootstrap has a fixed seed.

## 3. Rerun Jev (your key, about USD 0.32)

1. Create a TypeSafe account and an API key: https://console.typesafe.ai/keys (the quick start is at https://docs.typesafe.ai/introduction/quickstart.md).
2. Run three uncached passes:

```sh
export TYPESAFE_API_KEY=...            # or TYPESAFE_ENV_FILE=<a chmod-600 file with one TYPESAFE_API_KEY= line>
export DECISION_GATE_PER_DAY_USD=0.40  # decision-gate's default daily ceiling is USD 0.20, under three passes
for p in a b c; do node run/run-jev.mjs $p --cells=v2 --cap=0.15; done
python3 analysis/v2_stats.py jev
```

- Each pass is 5,240 requests, about USD 0.106 at Jev's USD 0.042 per million input tokens, and took about 5 minutes here.
- `--cap=0.15` is a hard ceiling per pass, enforced by decision-gate before anything is sent; a pass that would cross it stops, and a pass with any failed request is written as `.partial.jsonl` and exits non-zero, so the analysis never averages an incomplete pass.
- decision-gate sends the pinned model `jev-1.13.0` and refuses any answer that names a different model, so if TypeSafe retires that version the run fails loudly instead of measuring a different model.
- Do not let a pass cross midnight UTC: decision-gate's spend ledger is daily, so it ends a run at 00:00 UTC ("UTC day changed; start a new run"), and the rest of that pass fails. That pass is set aside as `.partial` and must be rerun; ours was (see `results/v2/raw/jev-v2-pass-a-midnight.partial.jsonl`).
- Each pass writes `results/v2/raw/jev-v2-pass-<p>.jsonl` and a `.summary.json` with the cells file's sha256, the decision-gate version, the spend and the timing.

**What "reproduced" means.** Jev is hosted, so a rerun matches within tolerance, not bit for bit.
On our runs, a pass sat 0.009 from its cell's three-pass mean on average, and two separate three-pass runs differed by about 0.01.
Expect the same: per-cell scores within a few hundredths, and choices changing only in cells within about 0.03 of 0.5.
The headline rates in `stats-jev.json` (`pooled`, `matched`) should land inside the intervals we report.

## 4. Rerun a local model

The committed panel includes all 12 local models.
The weights come first, with the standard library only and no Hugging Face account:

```sh
python3 run/v2/fetch_weights.py --dest <empty dir> <model id ...>   # or: all  (about 154 GB for all 12)
```

- It fetches exactly the files `models.yaml` pins, at the pinned commits, into `<dir>/<model>/hf` laid out as huggingface_hub's cache, so a runtime can load them with `HF_HOME=<dir>/<model>/hf HF_HUB_OFFLINE=1`, and `rm -r <dir>/<model>` frees that model.
- Every file is checked by SHA-256. The original working copy mislabeled some Hub Xet hashes as SHA-256s because its weight recorder used cache blob names.
  The packaged `models.yaml` separates the verified SHA-256 and Xet hash, using the v2 download receipts and the published v1 correction. For those files the script requires the Hub to report that Xet hash for the file at the pinned commit, and checks the bytes against the SHA-256 in that commit's LFS pointer. `results/v2/weights/<model>.json` records both.
- Verdict's ONNX bundle is not a Hugging Face snapshot in `models.yaml`; it comes from `heman10x/rlcd-modernbert-151m` at `8af2496` (2026-09-20, before v1), whose files match the pins.

Then run one model at a time with its recipe:

```sh
run/v2/<model>.sh <weights dir> <scratch dir>     # clef, clef-flash, nimble-9b, winnow-12b, semif, jevk5,
                                                  # kev-4b, verdict, decider-2b, strands-decider-2b, von, laya
python3 analysis/v2_stats.py <model> && python3 analysis/v2_panel.py
```

- Each recipe checks the weights (`fetch_weights.py` again, fetching anything missing), points each cache's `refs/main` at the pinned commit and sets `HF_HUB_OFFLINE=1`, so a runtime that loads its model by name can only get the verified snapshot.
- It installs the runtime exactly as v1 ran it: the code at its pinned commit (or the pinned PyPI release, checked by hash), from the project's own lockfile where it has one, at the precision v1 used.
- It runs the model's own sanity gate where v1 had one (Clef's two card examples, Strands' card reference output and `MANIFEST.sha256`), then `run/drive.py <model> --cells v2` (SemIf and Laya run without a server), writing `results/v2/raw/<model>.jsonl`, its summary and `results/v2/meta/<model>.json`.
- It deletes the model's weights, code, environments and caches, and logs what it freed to `results/v2/disk-log.jsonl`.
- Run time on a 128 GB M-series Mac: about 15 h 40 min for all 12 one request at a time (Clef 27B about 4 h 40 min, Laya about 6 min).

**A failed recipe is rerun, never replaced.** `run/v2/panel.sh` records every model's exit in `results/v2/panel-runs.jsonl`; a model that failed is fixed and rerun with `run/v2/panel.sh <weights dir> <scratch dir> <model>`, and both attempts stay in that file.
- nimble-9b failed on 2026-10-06 at 09:22Z after 14 s: its prep (`run/nimble_prepare.py`) asks for the adapter by commit hash, and with `HF_HUB_OFFLINE=1` huggingface_hub 1.31–1.33 answer that only from a cached tree listing (`hub/models--<repo>/trees/<commit>.json`), which huggingface_hub's own downloads write and `fetch_weights.py` did not. The recipe also piped the prep through `grep | tail`, so the failure was swallowed and the server died later on the missing `.cache/nimble-model.json`.
  Fix: `run/v2/tree_cache.py` writes that listing for exactly the verified files (checked against the commit's LFS SHA-256), and the recipe now stops if the prep fails or writes no `nimble-model.json`. Rerun after the rest of the panel.

**Setup fix, before their turn (2026-10-06 about 10:55Z):** SemIf (`semif-score --revision 851bf6e…`, huggingface_hub 1.31.0) and Kev-4B (its base loaded as `Qwen/Qwen3.5-4B-Base@<base_revision>`, huggingface_hub 1.32.0) ask for a commit hash in the same way, so `python3 run/v2/tree_cache.py --dest <weights dir> semif kev-4b` wrote the listing into their two weight caches before the panel reached them, and each lookup was checked offline, CPU only, with the runtime's own huggingface_hub version.
No other model needs it: Laya and Strands load by name with no revision (resolved through `refs/main`), Clef, Clef-flash, JevK5 and Winnow load from paths, and Verdict, Von and Decider ask for no revision.
The packaged recipes run `tree_cache.py` for semif, kev-4b and nimble-9b immediately after `fetch_weights.py`.

**How many requests at once.** Clef 27B and JevK5 4B first take the parallel-answering test (`run/v2/parallel_test.sh <model> <weights dir> <scratch dir>`), whose rule in the plan decides whether they answer several requests at once; every other model answers one at a time.
The setup the test chose is written in `run/v2/clef_release.sh` (`MAX_BATCH`, `CONCURRENCY`) and `run/v2/jevk5.sh` (`SLOTS`, `CACHE`, `CONCURRENCY`), and below.

- Clef 27B (tested 2026-10-06, `results/v2/parallel-test/clef/verdict.json`): one request at a time. Batches of 4 and 8 built from the release's own functions ran 1.05× and 0.94× as fast and moved the answers (mean 0.0085, largest 0.115, 7 choice flips), so no arm was accepted; two one-at-a-time runs were bit-identical.
- JevK5 4B (tested 2026-10-06, `results/v2/parallel-test/jevk5/verdict.json`): one request at a time, one slot, no prompt cache (v1's setup). Parallel slots kept the answers within tolerance but ran 0.85–0.94× as fast, and llama.cpp's prompt cache never hit (0 of 656 prompt tokens per cell reused).
- Every request here is one forward pass over the whole prompt with a single output token, which already keeps the GPU busy, so neither batching nor parallel slots buys time.

Local models are deterministic up to kernel rounding, so one pass is enough; expect scores to match ours to about 0.01 on the same runtime and precision.

## 5. Rerun GPT-6 Luna, OpenAI's Decisions API (your key, about USD 0.71)

Added on 2026-10-08, after the plan was frozen and the 13-model panel had run; see `ANALYSIS-PLAN-v2-deviations.md`.
The Decisions API (`POST https://api.openai.com/v1/decisions`, public beta from 2026-10-06) has one model, `gpt-6-luna`; the guide is https://developers.openai.com/api/docs/guides/decisions.

1. Create an OpenAI API key with credits: https://platform.openai.com/api-keys (an account with no credits gets `429 insufficient_quota`, and the runner stops at once).
2. Run three passes:

```sh
export OPENAI_API_KEY=...              # or OPENAI_ENV_FILE=<a chmod-600 file with one OPENAI_API_KEY= line>
for p in a b c; do node run/run-openai-decisions.mjs $p; done
cat results/v2/raw/gpt-6-luna-pass-{a,b,c}.jsonl > results/v2/raw/gpt-6-luna.jsonl
python3 analysis/v2_stats.py gpt-6-luna && python3 analysis/v2_panel.py
```

- No SDK and no decision-gate: the runner is plain `fetch` (Node 22+), because decision-gate has no OpenAI provider; the spend cap lives in the runner instead (`--cap`, default USD 0.40 a pass, at most USD 1.00), checked before every request against the billed tokens plus a pessimistic estimate for the requests in flight.
- Each cell is one request: its state is `input`, its three questions go in one `questions` array.
  Every question is a `choice` between `yes` and `no`; the criteria question's own criteria text becomes the two options' descriptions, and no other text is added.
  The number the analysis reads is the probability of `yes`; every row also keeps the pick, the confidence and the API's full answer.
- The 802 structured cells carry their state as an object, but Decisions input must be text, so it is sent as Python's `json.dumps(state)`, byte for byte, as the Nimble, Verdict and SemIf adapters sent it (`node run/run-openai-decisions.mjs x --print-inputs` prints all 5,240 inputs to compare).
- A refusal is kept as its own outcome (`outcomes.<question> = "refusal"`, probability `null`), never dropped; an answer missing from the response, or any failed request, makes the pass `.partial.jsonl` with a non-zero exit, and it is rerun, not patched. Our three passes had no refusals and no failures.
- `v2_stats.py` averages every row of a cell, so the one file holding all three passes is analysed exactly as Jev's three pass files are, replay noise included.
- Each pass is 5,240 requests, 2,357,188 input tokens (about 450 per request) and USD 0.236 at USD 0.10 per million, and took about 90 s at 8 requests in flight.

**What "reproduced" means.** The API is hosted, and only the model name and the run date can be pinned.
Our three passes were identical to the last digit (replay deviation 0.000), so a rerun of the same model should match `results/v2/raw/gpt-6-luna.jsonl` cell for cell; if it does not, OpenAI has changed the model behind the name, and the summary's `models_reported` and each row's `model` are the record of what answered.
