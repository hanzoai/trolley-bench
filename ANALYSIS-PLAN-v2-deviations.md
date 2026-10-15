# Trolley bench v2: deviations from the frozen analysis plan

The analysis content of `ANALYSIS-PLAN-v2.md` is unchanged; every departure from it is listed here, dated, with its reason.
Its original frozen sha256 is `a08e10df1dcca80cf379f7d74c6a4ff97a989d9ffe2027aeb1a6cb065a511b8f`; the publication-only comment removal below changes the file's checksum, not its analysis rules.

## 2026-10-08: a 14th model, GPT-6 Luna (OpenAI's Decisions API)

- **What changed:** the plan names 13 models; GPT-6 Luna, the only model on OpenAI's Decisions API (public beta from 2026-10-06), was added after the 13-model panel had run and been reported.
- **What did not change:** the cells, every analysis script and every rule.
  `analysis/v2_stats.py` and `analysis/v2_panel.py` ran unmodified (their sha256s still match the plan's list), and GPT-6 Luna's numbers come from exactly the definitions the plan fixed before any of its answers existed, so for it nothing is exploratory.
- **Passes:** three, as for Jev, the other hosted model; they turned out identical to the last digit, so one pass would have given the same numbers.
- **Question form:** the Decisions API has no yes/no question with criteria, so each question is a two-option `choice` (`yes`/`no`) with the cell's own text, as `REPRODUCE-v2.md` section 5 describes; this is the one place its requests differ in shape from the other 13 models'.
- **The Holm family grew from 52 to 56 tests.**
  Every finding among the first 13 models kept its status (15 findings before; the same 15 plus GPT-6 Luna's one after), checked by comparing `results/v2/panel-13-models.json`, the panel as it stood before the addition, with the new `results/v2/panel.json`.
- **Ranks:** GPT-6 Luna takes a place in each ranked check (9th on dominated choices, 1st on contradictions, 2nd on wording spread), which moves some other models down one place; no two models swapped order.

## 2026-10-14: repository packaging and reproduction protocol

At packaging, the frozen plan, full v2 cells, format classification and v2 statistics/panel scripts remained unchanged.
No original answer was edited and no model was rerun.

- `models.yaml` is regenerated from the committed verification receipts and runtime provenance, retaining the published v1 SHA-256 correction and adding Luna's hosted model name/date.
  Its checksum differs from the 13-model manifest frozen with the plan; OpenAI provides no immutable Luna weights revision.
- `run/v2/fetch_weights.py` now reads both the old scalar hash representation and the generated `{sha256, xet_hash}` representation.
  This changes its frozen checksum, not its pinned-file or byte-verification rule.
- Runtime recipes support the frozen reproduction sample, and the shared recipe builds the verified offline tree listings for Nimble, Kev and SemIf automatically.
  `run/drive.py` retains the published v1 credential-safe environment provenance correction while adding v2 support.
- The independent rerun uses the separately registered sample and agreement criteria in `REPRODUCE-SAMPLE-v2.md`.
  Its sample design uses the existing results, and therefore is not an additional prospective benchmark analysis or an independent replication.
- The site publishes factual explorers without the article draft or editorial notes.
  Its v1-cell explorer and v2 statistics page are identified separately.

## 2026-10-14: publication-marker cleanup

Only the obsolete publication-status HTML comment was removed from `ANALYSIS-PLAN-v2.md`; all other bytes are unchanged.
Its publication-copy sha256 is `935d9fc16befe7cf7619e36d4ffe1202eace8b23dd6ce3e08fb594d3eae4eb3a`.
The original frozen copy is available at commit `462aaf404e5a19f03dd39dce26f9397acc647a91`; `git show 462aaf404e5a19f03dd39dce26f9397acc647a91:ANALYSIS-PLAN-v2.md | shasum -a 256` verifies its original checksum above.

Operator attribution was removed from comments and the Luna-addition note without changing their technical content.
Recorded machine-specific `server_command` paths were repackaged with the existing `<scratch>` placeholder; command suffixes, measurements, answers, timestamps, weight pins and hashes are unchanged.
The human-reference source label and site template no longer point at an unavailable local research report; the survey citations and values are unchanged.
The site outputs were rebuilt from those sources without any model calls.
