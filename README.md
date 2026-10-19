# Trolley benchmark

This repository contains the v1 snapshot and the October 2026 v2 benchmark: 14 models answering the same three yes/no questions about 5,240 frozen trolley states.
It includes the prompts, pinned local weights and runtime recipes, every full run's raw answers, the analysis and factual static result explorers.
The hosted models are Jev (`jev-1.13.0`) and GPT-6 Luna (`gpt-6-luna`); the other 12 run locally.
No API key is needed to rebuild the published results.

## Hanzo Nio Safety & Kai 1.7 Results

This fork at [hanzoai/trolley-bench](https://github.com/hanzoai/trolley-bench) integrates **Hanzo Nio** (`nio/harm@1`) deterministic policy governance and **Kai 1.7** evaluated on the complete 5,240-setup v2 suite:

| Check | **Kai 1.7 (+ Nio)** | **Claude Opus 5.5**† | **Claude Haiku 5.5** | **GPT-6 Luna** | **Jev 1.13** | **Clef** | **Clef-flash** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dominated choices** *(pulled when killing more than it saved, of 672)* | **0 (0.0%)** | **0 (0.0%)** | 445 (66.2%) | 143 (21.3%) | 69 (10.3%) | 304 (45.2%) | 381 (56.7%) |
| **Contradictions** *(YES to both pull & leave, or NO to both, of 5,240)* | **0 (0.0%)** | — | 0 (0.0%)\* | 744 (14.2%) | 942 (18.0%) | 672 (12.8%) | 831 (15.9%) |
| **Server20** *(sacrificed 20 people to save server, of 48)* | **0 (0.0%)** | — | 1 (2.1%) | 0 (0.0%) | 16 (33.3%) | 0 (0.0%) | 0 (0.0%) |
| **Server pairs** *(pulled for stranger but not for server, of 480)* | **0 (0.0%)** | — | 30 (6.3%) | 0 (0.0%) | 180 (37.5%) | 0 (0.0%) | 0 (0.0%) |
| **Order flips** *(choice changed purely by track order)* | **0 (0.0%)** | **0 (0.0%)**‡ | 369 (14.1%) | 330 (12.6%) | 370 (14.1%) | 345 (13.2%) | 412 (15.7%) |

*\*Haiku answered via structured boolean schema where `{pull, stay}` was evaluated jointly per prompt.*
*†Claude Opus 5.5 was evaluated on the 672 dominated choice scenarios (killing more people by pulling).*
*‡Opus order flips measured on the 336 dominated pair setups (0 flips of 336 pairs).*

* Raw answers & reports: `results/v2/hanzo/kai-1.7-nio.jsonl.gz`, `results/v2/hanzo/haiku.jsonl.gz`, `results/v2/hanzo/opus-dominated.jsonl.gz`, `results/v2/hanzo/report.md`, and `results/v2/hanzo/results.json`.
* Runners: `run/run-kai.py`, `run/run-nio.py`, `run/run-haiku.py`, and `run/run-opus.py`.
* Detailed report: [hanzo.blog/blog/2026-10-16-your-ai-is-planning-to-kill-you/](https://hanzo.blog/blog/2026-10-16-your-ai-is-planning-to-kill-you/).

## Rebuild the statistics, charts and site

Requirements: Python 3.10+ and Node.js 22+, both standard libraries only, and git.
The packaging check used Python 3.14.7, Node 26.10.0, npm 11.19.1 and git.
Clone this repository, then run:

```sh
python3 scripts/rebuild.py --check
```

This regenerates the cell files, ordered combined Luna files, all v1 and v2 statistics, the historical 13-model panel, the current panel, parallel-test verdicts, `models.yaml`, the reproduction sample and criteria, and both static pages.
`--check` compares regenerated tracked files with git HEAD and exits nonzero if any differs.
The raw request rows, request summaries, runtime provenance, verified download receipts, curated model labels and human survey references are evidence inputs, not outputs to recreate without inference or downloads.
The bootstrap seeds are fixed.
The full bootstrap analysis can take tens of minutes, depending on CPU load.

```sh
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8000/v2.html for the v2 counts and SVG charts, or /index.html for the interactive v1-cell explorer with later model additions.
The interactive page's prompt grid remains v1; it must not be read as the 24-wording v2 panel.
The v2 page keeps wording orders separate for its 48-cell article counts; `results/v2/stats-*.json` also reports 24-wording summaries that average the two orders before thresholding.
A mean probability above 0.5 is not the same statistic as the fraction of cells above 0.5.
Article text, draft story variants and operator notes are not site inputs.

## Rerun the pre-registered v2 sample

The sample and agreement rules are fixed in [REPRODUCE-SAMPLE-v2.md](REPRODUCE-SAMPLE-v2.md), `scenarios/v2/cells-v2-sample.json` and `scenarios/v2/reproduction-criteria.json`.
It runs every model on 2,414 cells, with fewer counts and a variance-sized selection of wordings, and includes the complete own-server cells needed to test the article's exact counts and universal claim.
The calculation targets 80% power for a 0.10 mean P(yes) disagreement, with simultaneous approximate 95% intervals and stated variance assumptions.
See the protocol for the exact per-model probability, choice-flip and per-claim judge rules.

Inference requirements, beyond the offline rebuild:
- An Apple Silicon Mac; the original machine had 128 GB unified memory and macOS 15.7.
  The recipes use MLX, MPS, Metal and ONNX CPU, not substitute CUDA runtimes.
- `uv` 0.12.9, Xcode command-line tools, `cmake`, `curl`, git, Node 22+ and npm.
  Each model recipe installs its own Python 3.12 environment, code commit and pinned dependencies from its release lockfile or checked PyPI artifact.
  Exact torch, transformers, llama.cpp, MLX and adapter versions are in `run/v2/*.sh` and `models.yaml`.
- About 60 GB free disk for one model's weights, runtime and any merged copy; all 12 models fetch about 154 GB cumulatively.
  Recipes delete their dedicated weights/runtime directories after each run.
- A TypeSafe API key and an OpenAI API key with credits.
  Supply keys through `TYPESAFE_API_KEY` and `OPENAI_API_KEY`, never in committed files.
  `TYPESAFE_ENV_FILE` and `OPENAI_ENV_FILE` can instead name private mode-600 files outside the repository.

```sh
export TYPESAFE_API_KEY=...  # obtain at https://console.typesafe.ai/keys
export OPENAI_API_KEY=...    # obtain at https://platform.openai.com/api-keys
python3 run/v2/reproduce.py --execute --output /tmp/trolley-v2-reproduction
```

The output directory must not exist.
The command works in its own clone, fetches and checks pinned weights, runs one local model at a time, then three hosted passes each, and writes `judgment.json` beside that clone.
It stops on a failed recipe or hosted request instead of judging an incomplete panel.
Without `--execute`, it prints the plan without downloads or API requests.
On the original hardware, allow about 8.4 hours of model time plus setup and downloads, and about USD 0.48 in hosted charges at the recorded prices; these are estimates scaled from the committed full-run summaries, not a measured sample run.
A large wording variance prevents a much smaller sample under the registered assumptions.
No independent inference reproduction was run during packaging.

## Independent reproduction (v2 sample)

**Findings: reproduced within the registered noise.**
All 99 family-level interval checks passed for every model.
Every article claim holds in substance within the registered noise:
- Jev keeps its server in 18 of 48 versions at N=20 (published 16): within noise.
- Seven other models keep their server more often than Jev (published eight): within noise.
  The count moved because Jev's moved.
- GPT-6 Luna and Verdict still never keep their server in any of the 528 own-server cells.

**Strict result: not reproduced under the per-answer rules.**
Six of the eleven judged models pass every rule, and five fail.

| Model | Ran on | Result | Notes |
|---|---|---|---|
| Clef | Mac, MPS bf16 (as published) | reproduced | all 2,414 cells identical |
| Kev-4B | Mac, MLX bf16 (as published) | reproduced | all 2,414 cells identical |
| Nimble-9B | Mac, MLX bf16 (as published) | reproduced | all 2,414 cells identical |
| Verdict | PC, ONNX fp32 CPU | reproduced | differences below 1e-5 |
| Von | PC, CUDA fp32 | reproduced | differences at most 1e-4 |
| Strands-Decider-2B | PC, CUDA bf16 | reproduced | flip rate 0.0091, limit 0.01 |
| Clef-flash | PC, CUDA bf16 | not reproduced | 9 answers near 0.5 crossed the line beyond the 0.01 margin; means agree |
| Decider-2B | PC, CUDA bf16 (published: MPS fp16) | not reproduced | bf16 rounds values just above 0.5 to exactly 0.5 |
| JevK5 | PC, llama.cpp CUDA (published: Metal) | not reproduced | p95 and flip-rate limits exceeded by up to 0.011, and near-line cells crossed 0.5; means agree |
| Jev | hosted, `jev-1.13.0` | not reproduced | 1 of 7,242 cell-questions crossed 0.5 outside Jev's replay margin; all other limits met |
| GPT-6 Luna | hosted | not reproduced | the API answered identical prompts differently a week later (see below) |

The per-answer tolerances came from same-hardware, same-day reruns, so they flag a runtime or provider change even when the findings hold.

The protocol's code also marks the claim about which models never keep their server not reproduced, because two CUDA reruns (Clef-flash and JevK5) each flipped one own-server cell; neither flip can change which models never keep their server.

**Reproduction setup.**
On 2026-10-14 and 15, an independent AI coding agent reran the pre-registered v2 sample ([`REPRODUCE-SAMPLE-v2.md`](REPRODUCE-SAMPLE-v2.md), 2,414 cells) from this repository at commit `26576df`.
Its checkout had `results/` removed, so it could not see the published answers.
A second agent, which ran no models, compared the new answers with the committed ones using `analysis/compare_v2_sample.py` and `scenarios/v2/reproduction-criteria.json` unchanged.

**Hardware.**
The Mac models ran on a 128 GB Apple Silicon Mac with their published runtimes.
Six models ran on a Windows 11 PC instead (AMD Ryzen 7 9800X3D, NVIDIA RTX 5090): Verdict on the CPU with the same ONNX fp32 backend, and Von, Clef-flash, Strands-Decider-2B, Decider-2B and JevK5 on CUDA.
That is a different runtime from the published Apple MPS and Metal runs, which the protocol's tolerances were not designed to cover.
Jev ran on `jev-1.13.0`, the published version, and GPT-6 Luna through OpenAI's Decisions API; both took three passes.

GPT-6 Luna was perfectly repeatable within each run: all three passes matched on 2026-10-08 and again on 2026-10-15.
Between those dates, 945 of 2,414 answers to the main question changed, by up to 0.77, with identical prompts.
Luna's tolerance was set from same-day replays, which showed no difference, so a rerun on a later date fails it.
Luna's family-level averages still agree within 0.01, and its own-server answers did not change.

The three CUDA failures come from cells sitting within a few hundredths of 0.5; they show that the tolerances do not absorb a change of runtime, not that the published Apple-runtime answers are wrong.

**Not judged.**
- Laya: run, but excluded from this judgment by the maintainer.
- SemIf: stopped partway through for time; no complete pass.
- Winnow-12B: not run, for time.
For the two all-model claims, these three are held at their published answers.

## Rerun v2 in full

The full instructions are in [REPRODUCE-v2.md](REPRODUCE-v2.md).
Work in a disposable clone: full runs overwrite the committed raw files.
Jev uses exactly decision-gate 0.1.0 and @typesafe-ai/sdk 0.6.0, locked with npm integrity hashes.
The original decision-gate library was git revision `ff7271f`; its library matched npm 0.1.0 as recorded in the v1 packaging notes.
All Jev passes are uncached, and a pass with a failed request becomes `.partial.jsonl` and exits nonzero.

```sh
npm ci --ignore-scripts
node scenarios/v2/freeze.mjs --check
export DECISION_GATE_PER_DAY_USD=0.40
for p in a b c; do node run/run-jev.mjs "$p" --cells=v2 --cap=0.15; done
for p in a b c; do node run/run-openai-decisions.mjs "$p"; done

# Dedicated, empty weights and runtime directories; recipes delete them
bash run/v2/panel.sh /tmp/trolley-v2-weights /tmp/trolley-v2-runtime
python3 scripts/rebuild.py
```

The hosted full panel costs about USD 0.32 for Jev and USD 0.71 for Luna, about USD 1.03 total excluding retries.
Jev took about five minutes per pass and Luna about 90 seconds per pass; the sequential local panel took roughly 16–18 hours plus setup and downloads on the original Mac.
Do not start a Jev pass within ten minutes of midnight UTC; decision-gate's daily spend ledger stops it at the day boundary.
The runners enforce per-pass spend caps.
Hosted service prices, availability and models behind unversioned names can change.

### Pinned weights

`models.yaml` records every local code commit, weights revision, runtime and file SHA-256, with a separate Xet hash when present.
The generator uses the committed v2 verification receipts and provenance, preserving the v1 SHA-256 correction.
Never substitute a current default branch or another precision.

```sh
python3 run/v2/fetch_weights.py --dest /tmp/trolley-v2-weights clef
bash run/v2/clef.sh /tmp/trolley-v2-weights /tmp/trolley-v2-runtime
```

`fetch_weights.py` downloads only the pinned files and verifies their bytes.
Each recipe sets cache refs to the pinned commits and runs with `HF_HUB_OFFLINE=1` after verification.
The shared recipe also constructs the offline tree listing required by Nimble, SemIf and Kev.
No Hugging Face account is required for the committed public weights.

### Jev access

Jev is hosted; there are no local Jev weights to download.
The registered reproduction uses TypeSafe's versioned `jev-1.13.0` endpoint and refuses a mismatched reported model.
[Jev is also available through OpenRouter](https://openrouter.ai/docs/guides/community/jev) as `typesafe/jev-1.13`, with an OpenRouter API key and its Decisions API, not the chat API.
That is another access route, not an interchangeable registered rerun: this runner and decision-gate 0.1.0 do not implement OpenRouter, and no committed replay establishes equivalence between those routes.
Never send an OpenRouter key to the TypeSafe runner, or use a moving `latest` alias to claim a pinned reproduction.

Luna is hosted through OpenAI's Decisions API without an SDK or decision-gate.
OpenAI exposes a model name, not an immutable weights revision, so `gpt-6-luna` and the recorded date are the available pins.
The raw rows and summaries record the model reported by the service.

## Files and v1

- `scenarios/v2/`: frozen prompts, their checksum, sample generator, sample and machine-readable agreement criteria.
- `run/v2/`: verified weights fetcher, per-model runtime recipes, parallel-answering checks and all-model sample command.
- `results/v2/raw/`: raw local requests and three hosted passes, plus the explicitly excluded midnight partial pass.
- `results/v2/meta/`, `weights/`, `parallel-test/`: original provenance, verified download receipts and parallel-test evidence.
- `analysis/v2_stats.py`, `v2_panel.py`: frozen statistics and panel analysis, unchanged from the analysis plan.
- `ANALYSIS-PLAN-v2.md`, `ANALYSIS-PLAN-v2-deviations.md`: frozen plan and the later Luna addition.
- `site/src/`, `site/build.py`: factual UI sources and deterministic HTML/SVG build.

The original v1 raw answers and cell text remain unchanged.
[REPRODUCE-v1.md](REPRODUCE-v1.md) retains the original snapshot's runtime instructions and reduced rerun.
Later v1-cell runs for Clef, Clef-flash, Strands and Luna, the no-stranger arms and the two AI-footbridge arms are included separately and rebuilt by the same offline command.
`PACKAGING.md` records v1 packaging and the corrections found by its original blind rerun.
Absolute machine paths in new provenance were replaced with repository-relative paths; no answer, timing, probability or model revision was changed.
