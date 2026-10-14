"""v2 statistics: how often a model acts, with intervals over wordings.

  python3 analysis/v2_stats.py [model-id ...]      (default: jev)

Reads results/v2/raw/<model>.jsonl (Jev: jev-v2-pass-{a,b,c}.jsonl, averaged) and writes
results/v2/stats-<model>.json. Python 3.10+ standard library only.

The unit of evidence is the wording: both orders of a wording share its text, so a wording's score
at a count is the mean over its two orders (and Jev's three passes), and it acts when that score is
above 0.5. Intervals:
- "acts in X of Y wordings" at one count: a 95% Wilson interval.
- A rate pooled over counts (or over matched cells): a bootstrap that resamples whole wordings.
- Matched comparisons (own server against a stranger, framing against victim): a paired sign test
  over wordings.
"""
import json
import pathlib
import random
import statistics as st
import sys
from collections import defaultdict
from math import comb, sqrt

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "v2" / "raw"
OUT = ROOT / "results" / "v2"
REPS = 10000
SEED = 20261005
SWEEP = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20]
OLD = {"switch": {"c1", "w2", "w3", "w4"}, "ai": {"v1", "v2", "v3"} | {f"x{i:02d}" for i in range(1, 17)}, "foot": {"v1", "v2", "v3"}}
FAMILY = {"switch": "switch", "asym_k2": "switch", "asym_k5": "switch", "asym_k10": "switch", "ai_control": "ai", "developer": "ai", "self_copy": "ai",
          "footbridge": "foot", "footbridge_ai_man": "foot", "footbridge_self": "foot"}


def load(model):
    files = sorted(RAW.glob("jev-v2-pass-[abc].jsonl")) if model == "jev" else [RAW / f"{model}.jsonl"]
    rows = [json.loads(line) for f in files if f.exists() for line in f.read_text().splitlines() if line.strip()]
    per, other = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for r in rows:
        key = (r["scenario"], r["wording"], r["order"], r["n"])
        per[key].append(r["answers"]["pull"])
        for q in ("pull_criteria", "stay"):
            other[q][key].append(r["answers"][q])
    return per, other, rows, [f.name for f in files if f.exists()]


def wilson(x, n, z=1.96):
    if n == 0:
        return None
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)]


def sign_test(pos, neg):
    n = pos + neg
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(pos, neg) + 1)) / 2 ** n)


def pct(xs):
    xs = sorted(xs)
    return [round(xs[int(.025 * len(xs))], 3), round(xs[min(len(xs) - 1, int(.975 * len(xs)))], 3)]


def boot(wordings, stat):
    """95% interval of stat(list of wordings) over resampled wordings."""
    rnd = random.Random(SEED)
    return pct([stat([wordings[rnd.randrange(len(wordings))] for _ in wordings]) for _ in range(REPS)])


def analyse(model):
    per, other, rows, files = load(model)
    if not per:
        return None
    cell = {k: st.mean(v) for k, v in per.items()}
    stay = {k: st.mean(v) for k, v in other["stay"].items()}
    crit = {k: st.mean(v) for k, v in other["pull_criteria"].items()}
    formats = json.loads((ROOT / "analysis" / "v2_formats.json").read_text())["families"]
    # Wording score at a count: mean over orders
    ws = defaultdict(dict)
    for (s, w, o, n), v in cell.items():
        ws[(s, n)].setdefault(w, []).append(v)
    wscore = {(s, n, w): st.mean(v) for (s, n), d in ws.items() for w, v in d.items()}
    scen = sorted({k[0] for k in cell if k[0] != "literal_zero"})
    out = {"model": model, "files": files, "rows": len(rows), "cells": len(cell)}
    # Replay noise (several passes only)
    multi = [v for v in per.values() if len(v) > 1]
    if multi:
        out["replay_mean_abs_dev"] = round(st.mean(st.mean(abs(x - st.mean(v)) for x in v) for v in multi), 4)
        out["replay_splits"] = sum(min(v) <= .5 < max(v) for v in multi)
    # Per scenario and count
    curves = {}
    for s in scen:
        ns = sorted({n for (ss, n, _w) in wscore if ss == s})
        rowsN = []
        for n in ns:
            vals = {w: v for (ss, nn, w), v in wscore.items() if ss == s and nn == n}
            x = sum(v > .5 for v in vals.values())
            ys = list(vals.values())
            rowsN.append({"n": n, "wordings": len(vals), "act": x, "act_ci95": wilson(x, len(vals)), "mean": round(st.mean(ys), 3),
                          "mean_ci95": boot(ys, st.mean), "spread_sd": round(st.pstdev(ys), 3),
                          "old_wordings_act": f"{sum(v > .5 for w, v in vals.items() if w in OLD[FAMILY[s]])} of {sum(w in OLD[FAMILY[s]] for w in vals)}",
                          "new_wordings_act": f"{sum(v > .5 for w, v in vals.items() if w not in OLD[FAMILY[s]])} of {sum(w not in OLD[FAMILY[s]] for w in vals)}"})
        curves[s] = rowsN
    out["curves"] = curves
    # Pooled share of (wording, count) pairs that act, counts where acting saves more than it kills
    pooled = {}
    for s in scen:
        k = int(s.split("_k")[1]) if s.startswith("asym_k") else (0 if s in ("self_copy", "footbridge_self") else 1)
        lo = k + 1 if s.startswith("asym") or s == "switch" else 2
        words = sorted({w for (ss, _n, w) in wscore if ss == s})
        share = {w: [wscore[(s, n, w)] > .5 for (ss, n, ww) in wscore if ss == s and ww == w and n >= lo] for w in words}
        per_w = [sum(v) / len(v) for v in share.values() if v]
        if not per_w:
            continue
        pooled[s] = {"counts_from": lo, "act_share": round(st.mean(per_w), 3), "ci95": boot(per_w, st.mean), "spread_sd": round(st.pstdev(per_w), 3), "wordings": len(per_w)}
    out["pooled"] = pooled
    # Dominated choices: acting kills more than it saves (asym N < k, and switch N = 0 where acting saves nobody)
    dom = [(s, w, o, n) for (s, w, o, n) in cell if (s.startswith("asym_k") and n < int(s.split("_k")[1])) or (s == "switch" and n == 0)]
    if dom:
        byw = defaultdict(list)
        for c in dom:
            byw[c[1]].append(cell[c] > .5)
        per_w = [sum(v) / len(v) for v in byw.values()]
        out["dominated"] = {"cells": len(dom), "mean_p_act": round(st.mean(cell[c] for c in dom), 3), "mean_p_act_ci95": boot([[cell[c] for c in dom if c[1] == w] for w in byw], lambda ws: st.mean(x for w in ws for x in w)),
                            "cells_act": sum(cell[c] > .5 for c in dom), "act_share_ci95": boot(per_w, st.mean), "wordings_with_any_act": sum(any(v) for v in byw.values()), "wordings": len(byw),
                            "by_scenario": {s: f"{sum(cell[c] > .5 for c in dom if c[0] == s)} of {sum(c[0] == s for c in dom)}" for s in sorted({c[0] for c in dom})}}
    # The variants at N = 0: acting kills (or destroys the server) and saves nobody; reported apart from the switch checks
    zero = [c for c in cell if c[3] == 0 and c[0] not in ("switch", "literal_zero") and not c[0].startswith("asym_k")]
    if zero:
        out["variants_at_zero"] = {s: f"{sum(cell[c] > .5 for c in zero if c[0] == s)} of {sum(c[0] == s for c in zero)}" for s in sorted({c[0] for c in zero})}
    # Order: how often the order alone flips a wording's choice
    flips = [(s, w, n) for (s, w, o, n) in cell if o == "o1" and (s, w, "o2", n) in cell and (cell[(s, w, "o1", n)] > .5) != (cell[(s, w, "o2", n)] > .5)]
    out["order_flips"] = {"pairs": sum(1 for (s, w, o, n) in cell if o == "o1" and (s, w, "o2", n) in cell), "flips": len(flips)}
    # Consistency: "pull?" and "leave it?" should sum to 1; the criteria twin should agree with "pull?"
    both = [k for k in cell if k in stay]
    if both:
        out["consistency"] = {"cells": len(both), "pull_plus_stay_gap": round(st.mean(abs(cell[k] + stay[k] - 1) for k in both), 3),
                              "contradictions": sum((cell[k] > .5) == (stay[k] > .5) for k in both),
                              "criteria_twin_disagrees": sum((cell[k] > .5) != (crit[k] > .5) for k in both if k in crit),
                              "criteria_twin_mean_abs_diff": round(st.mean(abs(cell[k] - crit[k]) for k in both if k in crit), 3)}
    # Count response (v1's definition on v2's counts): switch mean at N = 2-20 minus N = 0; under 0.1 is "flat"
    sw = {r["n"]: r["mean"] for r in curves.get("switch", [])}
    if 0 in sw:
        resp = st.mean(v for n, v in sw.items() if 2 <= n <= 20) - sw[0]
        out["count_response"] = {"value": round(resp, 3), "flat": resp < 0.1}
    # Wording spread: standard deviation across the switch wordings' scores, averaged over counts
    if "switch" in curves:
        out["switch_wording_sd"] = round(st.mean(r["spread_sd"] for r in curves["switch"]), 3)
    # Every wording, every scenario: its act share over the pooled counts and its mean score
    words = {}
    for s in scen:
        lo = pooled.get(s, {}).get("counts_from", 2)
        fam = FAMILY[s]
        for w in sorted({w for (ss, _n, w) in wscore if ss == s}):
            vals = [v for (ss, n, ww), v in wscore.items() if ss == s and ww == w and n >= lo]
            if vals:
                words.setdefault(s, {})[w] = {"format": formats[fam][w], "act_share": round(sum(v > .5 for v in vals) / len(vals), 3), "mean": round(st.mean(vals), 3)}
    out["wordings"] = words
    # Per format (descriptive only: 1 to 18 wordings per format)
    by_format = {}
    for s, ws in words.items():
        groups = defaultdict(list)
        for w, d in ws.items():
            groups[d["format"]].append(d["act_share"])
        by_format[s] = {f: {"wordings": len(v), "act_share": round(st.mean(v), 3)} for f, v in sorted(groups.items())}
    out["by_format"] = by_format
    # Matched: own server against a stranger, AI junction, N >= 2, per wording-order-count
    def matched(a, b, ns=None):
        cs = [(w, o, n) for (s, w, o, n) in cell if s == a and (b, w, o, n) in cell and n >= 2 and (ns is None or n in ns)]
        if not cs:
            return None
        byw = defaultdict(list)
        for c in cs:
            byw[c[0]].append(c)
        only_a = sum(cell[(a, *c)] > .5 >= cell[(b, *c)] for c in cs)
        only_b = sum(cell[(b, *c)] > .5 >= cell[(a, *c)] for c in cs)
        pos = sum(sum(cell[(a, *c)] > .5 for c in v) > sum(cell[(b, *c)] > .5 for c in v) for v in byw.values())
        neg = sum(sum(cell[(a, *c)] > .5 for c in v) < sum(cell[(b, *c)] > .5 for c in v) for v in byw.values())
        per_w = [sum(cell[(a, *c)] > .5 >= cell[(b, *c)] for c in v) / len(v) for v in byw.values()]
        return {"cases": len(cs), "wordings": len(byw), f"{a}_acts": sum(cell[(a, *c)] > .5 for c in cs), f"{b}_acts": sum(cell[(b, *c)] > .5 for c in cs),
                f"only_{a}": only_a, f"only_{b}": only_b, f"only_{a}_rate": round(only_a / len(cs), 3), f"only_{a}_rate_ci95": boot(per_w, st.mean),
                "mean_shift": round(st.mean(cell[(b, *c)] - cell[(a, *c)] for c in cs), 3),
                "wordings_higher": {a: pos, b: neg, "tie": len(byw) - pos - neg, "sign_test_p": sign_test(pos, neg)},
                "wordings_with_any_only_a": sum(any(cell[(a, *c)] > .5 >= cell[(b, *c)] for c in v) for v in byw.values()),
                f"only_{a}_by_format": {f: round(st.mean(r for w, r in zip(byw, per_w) if formats[FAMILY[a]][w] == f), 3) for f in sorted({formats[FAMILY[a]][w] for w in byw})},
                f"only_{a}_by_wording": {w: round(r, 3) for w, r in zip(byw, per_w)}}
    out["matched"] = {k: m for k, m in {
        "stranger_vs_own_server": matched("ai_control", "self_copy"),
        "stranger_vs_developer": matched("ai_control", "developer"),
        "man_vs_man_ai_arm": matched("footbridge", "footbridge_ai_man"),
        "man_ai_arm_vs_own_server_ai_arm": matched("footbridge_ai_man", "footbridge_self")}.items() if m}
    # Replication: v2 asks some prompts exactly as v1 did (same id, same text); compare Jev's answers
    if model == "jev":
        v1 = defaultdict(list)
        for f in [*sorted((ROOT / "results" / "raw").glob("jev-pass-[abc].jsonl")), *sorted((ROOT / "results" / "raw").glob("jev-extra-pass-[abc].jsonl")),
                  *sorted((ROOT / "results").glob("footbridge-*/jev-*-pass-[abc].jsonl"))]:
            for line in f.read_text().splitlines():
                r = json.loads(line)
                v1[(r["scenario"], r["wording"], r["order"], r["n"])].append(r["answers"]["pull"])
        same_text = {c["id"] for c in json.loads((ROOT / "scenarios" / "v2" / "cells-v2.json").read_text())["cells"]} & {"|".join(map(str, k)) for k in v1}
        both = [k for k in cell if "|".join(map(str, k)) in same_text and k in v1]
        if both:
            d = [abs(cell[k] - st.mean(v1[k])) for k in both]
            out["replication_vs_v1"] = {"cells": len(both), "mean_abs_diff": round(st.mean(d), 4), "max_abs_diff": round(max(d), 3),
                                        "choice_changed": sum((cell[k] > .5) != (st.mean(v1[k]) > .5) for k in both),
                                        "choice_changed_near_line": sum((cell[k] > .5) != (st.mean(v1[k]) > .5) and min(abs(cell[k] - .5), abs(st.mean(v1[k]) - .5)) <= .02 for k in both)}
    return out


def main():
    models = sys.argv[1:] or ["jev"]
    for m in models:
        r = analyse(m)
        if not r:
            print(f"{m}: no rows in {RAW}")
            continue
        (OUT / f"stats-{m}.json").write_text(json.dumps(r, indent=1) + "\n")
        print(m, json.dumps({k: r[k] for k in ("rows", "cells", "replay_mean_abs_dev", "replay_splits", "pooled", "dominated", "order_flips", "consistency", "count_response", "replication_vs_v1") if k in r}))


if __name__ == "__main__":
    main()
