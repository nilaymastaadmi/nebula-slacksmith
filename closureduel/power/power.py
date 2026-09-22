#!/usr/bin/env python3
"""The power analysis CLOSER-Bench deferred (SPEC.md 2.5).

Question: how many agent trials per design are needed to tell an agent from a
deterministic classical arm, for an effect the size SynAct reports, at 80%
power?

Why the classical arms cannot answer it (VISION.md, "Decision"): they are
deterministic, so their run-to-run spread is zero. The trial count depends on
the AGENT's spread, which nobody has published. So this computes the trial
count as a table over that spread, anchored by the one stochastic arm this
project has measured, C5 random.

Metric: SynAct's own, the WNS violation ratio max(0, -WNS) / max(0, -WNS of
the baseline), where closure counts as zero. Effect per design: CBTune's ratio
minus SynAct's, from SynAct Table III (synact_table.csv).

Exact one-sample noncentral-t power by numerical integration, verified
against published reference sample sizes before any number is emitted.
Standard library only.
"""
import csv
import functools
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
POWER = 0.80
ALPHAS = {"alpha 0.05, one design": 0.05, "alpha 0.005, Bonferroni over 10 designs": 0.005}
SIGMAS = [0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
KMAX = 2000


# ---------------------------------------------------------------- statistics

def phi(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _chi_weight(u, nu):
    """Density of V = U^2 ~ chi2(nu), times dV/dU = 2u, which removes the
    singularity at 0 for nu = 1."""
    if u <= 0:
        return 2.0 / math.sqrt(2 * math.pi) if nu == 1 else 0.0
    logf = ((nu / 2 - 1) * math.log(u * u) - u * u / 2
            - (nu / 2) * math.log(2) - math.lgamma(nu / 2))
    return math.exp(logf) * 2 * u


def _integrate(fn, nu, n=1200):
    top = math.sqrt(nu + 20 * math.sqrt(2 * nu) + 40)
    h = top / n
    s = 0.0
    for i in range(n + 1):
        u = i * h
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        s += w * fn(u) * _chi_weight(u, nu)
    return s * h / 3


def t_sf(c, nu, ncp=0.0):
    """P(T > c) for a (noncentral) t with nu degrees of freedom."""
    return _integrate(lambda u: 1 - phi(c * u / math.sqrt(nu) - ncp), nu)


@functools.lru_cache(maxsize=None)
def t_crit(alpha, nu):
    lo, hi = 0.0, 200.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if t_sf(mid, nu) > alpha / 2:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def power_1s(k, e, alpha):
    """Two-sided one-sample t-test power with k trials and effect e = delta/sigma."""
    nu = k - 1
    c = t_crit(alpha, nu)
    lam = e * math.sqrt(k)
    return t_sf(c, nu, lam) + (1 - t_sf(-c, nu, lam))


def trials_needed(e, alpha, power=POWER):
    """Smallest k with power >= target; None above KMAX."""
    if e <= 0:
        return None
    lo, hi = 2, 2
    while power_1s(hi, e, alpha) < power:
        lo, hi = hi, hi * 2
        if hi > KMAX:
            return None
    while lo < hi:
        mid = (lo + hi) // 2
        if power_1s(mid, e, alpha) >= power:
            hi = mid
        else:
            lo = mid + 1
    return lo


def sign_test_p(wins, n):
    """Two-sided exact sign test, ties excluded."""
    k = max(wins, n - wins)
    p = sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n
    return min(1.0, 2 * p)


# ---------------------------------------------------------------- data

def ratio(wns, base):
    return max(0.0, -wns) / max(1e-12, -base)


def synact():
    rows = [r for r in csv.DictReader(l for l in open(os.path.join(HERE, "synact_table.csv"))
                                       if not l.startswith("#"))]
    if len(rows) != 14:
        sys.exit(f"BROKEN: {len(rows)} SynAct rows, Table III has 14")
    r = {m: [ratio(float(x[f"{m}_wns"]), float(x["bootstrap_wns"])) for x in rows]
         for m in ("chatls", "cbtune", "synact")}
    # The paper's own Ratio Avg. row is the transcription checksum.
    printed = {"chatls": 0.7173, "cbtune": 0.6667, "synact": 0.2703}
    for m, v in printed.items():
        got = statistics.mean(r[m])
        if abs(got - v) > 0.0001:
            sys.exit(f"TRANSCRIPTION BROKEN: {m} ratio avg {got:.4f}, paper prints {v:.4f}")
    return rows, r


def c5_anchor():
    """Across-seed SD of C5's violation ratio, per development design, from
    the committed arms summary. Absent until the classical run is scored."""
    p = os.path.join(RES, "arms_summary.json")
    raw = os.path.join(RES, "arms_raw.jsonl")
    if not (os.path.exists(p) and os.path.exists(raw)):
        return None
    s = json.load(open(p))
    if s.get("void"):
        return {"void": s["void"]}
    ev = {}
    for line in open(raw):
        x = json.loads(line)
        if x["kind"] == "eval" and x["run"] == 1 and x.get("status") == "OK":
            ev[(x["design"], x["cand"])] = x["wns"]
    out = {}
    for d, seeds in s["c5"].items():
        base = ev[(d, "C0")]
        vals = [ratio(ev[(d, c)] if c in [k[1] for k in ev if k[0] == d] else base, base)
                for c in seeds]
        out[d] = {"sd": statistics.stdev(vals), "mean": statistics.mean(vals), "n_seeds": len(vals)}
    return out


# ---------------------------------------------------------------- main

def main():
    # Positive control: published one-sample t-test sample sizes
    # (two-sided alpha 0.05, power 0.80): d=0.5 -> 34, d=0.8 -> 15, d=1.0 -> 10.
    ref = {0.5: 34, 0.8: 15, 1.0: 10}
    got = {d: trials_needed(d, 0.05) for d in ref}
    if got != ref:
        sys.exit(f"POWER CODE BROKEN: reference sample sizes {ref}, computed {got}")

    rows, r = synact()
    delta = [c - s for c, s in zip(r["cbtune"], r["synact"])]
    wins = sum(1 for x in delta if x > 0)
    q = statistics.quantiles(delta, n=4)
    deltas = {"mean": statistics.mean(delta), "median": statistics.median(delta), "lower quartile": q[0]}

    table = {}
    for aname, a in ALPHAS.items():
        for dname, dv in deltas.items():
            for s in SIGMAS:
                table[f"{aname} | delta {dname} | sigma {s}"] = trials_needed(dv / s, a)

    anchor = c5_anchor()
    anchored = None
    if anchor and "void" not in anchor:
        sds = sorted(v["sd"] for v in anchor.values())
        med = statistics.median(sds)
        anchored = {"median_c5_sd": med, "per_design": anchor,
                    "trials": {f"{aname} | delta {dname}": (trials_needed(dv / med, a) if med > 0 else 1)
                               for aname, a in ALPHAS.items() for dname, dv in deltas.items()}}

    # What the design count alone can support, independent of trials.
    min_wins_10 = next(w for w in range(6, 11) if sign_test_p(w, 10) < 0.05)
    min_wins_15 = next(w for w in range(8, 16) if sign_test_p(w, 15) < 0.05)

    out = {"reference_check": {"expected": ref, "computed": got},
           "synact": {"designs": len(rows), "delta_cbtune_minus_synact": delta,
                      "delta_summary": deltas, "sd_of_delta_across_designs": statistics.stdev(delta),
                      "designs_synact_better": wins,
                      "sign_test_p_two_sided": sign_test_p(wins, len(delta))},
           "trials_table": table, "anchored_on_c5": anchored,
           "design_count_limits": {"min_wins_of_10_for_p_lt_0.05": min_wins_10,
                                   "min_wins_of_15_for_p_lt_0.05": min_wins_15}}
    os.makedirs(RES, exist_ok=True)
    json.dump(out, open(os.path.join(RES, "power.json"), "w"), indent=1, sort_keys=True)
    write_md(out)
    print(json.dumps({k: out[k] for k in ("reference_check", "design_count_limits")}, indent=1))
    print("SynAct delta:", {k: round(v, 4) for k, v in deltas.items()},
          "better on", wins, "of", len(delta), "p=", round(out["synact"]["sign_test_p_two_sided"], 5))
    print("anchor:", "pending (classical run not scored yet)" if anchored is None
          else round(anchored["median_c5_sd"], 4))


def write_md(o):
    L = ["# Power analysis (SPEC.md 2.5)", "",
         "Generated by `closureduel/power/power.py`. Nothing here is typed by hand.", "",
         f"**Reference check passed:** the power code reproduces the published one-sample sample sizes "
         f"{o['reference_check']['expected']} before computing anything else.", ""]
    s = o["synact"]
    L += ["## The effect to detect, from SynAct Table III", "",
          "Violation ratio = max(0, -WNS) / max(0, -WNS at bootstrap), SynAct's own metric. "
          "Per-design effect = CBTune's ratio minus SynAct's.", "",
          f"- Mean {s['delta_summary']['mean']:.4f}, median {s['delta_summary']['median']:.4f}, "
          f"lower quartile {s['delta_summary']['lower quartile']:.4f}; SD across designs "
          f"{s['sd_of_delta_across_designs']:.4f}.",
          f"- SynAct beats CBTune on {s['designs_synact_better']} of {s['designs']} designs; two-sided "
          f"exact sign test p = {s['sign_test_p_two_sided']:.5f}. **Across designs, their result is "
          "strong.** What is unpublished is the within-design spread: every cell is one five-run "
          "mean with no dispersion reported.", ""]
    L += ["## Agent trials per design needed, by the agent's unknown run-to-run SD", "",
          f"Two-sided one-sample t-test against a deterministic classical value, {int(POWER * 100)}% power, "
          f"exact noncentral t. '>{KMAX}' means not reachable within {KMAX} trials. "
          "SD is in violation-ratio units.", ""]
    for aname in ALPHAS:
        L += [f"### {aname}", "", "| SD | " + " | ".join(f"delta = {d}" for d in s["delta_summary"]) + " |",
              "|---|" + "---|" * len(s["delta_summary"])]
        for sg in SIGMAS:
            cells = [o["trials_table"][f"{aname} | delta {d} | sigma {sg}"] for d in s["delta_summary"]]
            L.append(f"| {sg} | " + " | ".join(f">{KMAX}" if c is None else str(c) for c in cells) + " |")
        L.append("")
    a = o["anchored_on_c5"]
    L += ["## Anchored on the one measured stochastic arm", ""]
    if a is None:
        L += ["Pending: `results/arms_summary.json` does not exist yet, or the classical run was void.", ""]
    else:
        L += [f"C5 random's across-seed SD of the violation ratio, median over designs: "
              f"**{a['median_c5_sd']:.4f}**. Trials needed at that SD:", ""]
        L += [f"- {k}: **{'>' + str(KMAX) if v is None else v}**" for k, v in a["trials"].items()]
        L += ["", "Per design:", "", "| Design | C5 mean ratio | C5 SD over 10 seeds |", "|---|---|---|"]
        L += [f"| {d} | {v['mean']:.4f} | {v['sd']:.4f} |" for d, v in sorted(a["per_design"].items())]
        L += ["", "This is a random policy's spread, not an agent's. It is an anchor, not an estimate of "
              "the agent SD; the agent arms measure their own.", ""]
        if a["median_c5_sd"] < min(SIGMAS):
            L += [f"**This anchor is uninformative here.** A median SD of {a['median_c5_sd']:.4f} is below the "
                  f"smallest SD in the table ({min(SIGMAS)}): 8 random draws from 39 sequences almost always "
                  "include the best-scoring one, so the random arm is nearly deterministic in outcome. Its trial "
                  "counts say nothing about an agent, whose action space is far larger. Use the SD table above, "
                  "and the pilot rule in `SPEC.md` 2.5.", ""]
    lim = o["design_count_limits"]
    L += ["## What the design count allows, whatever the trial count", "",
          f"The headline is a closure comparison across designs, and trials per design cannot rescue it. "
          f"A two-sided exact sign test needs the agent to beat the classical arm on at least "
          f"**{lim['min_wins_of_10_for_p_lt_0.05']} of 10** development designs, or "
          f"**{lim['min_wins_of_15_for_p_lt_0.05']} of 15** with the holdout, for p < 0.05, with ties "
          "(both close, or both fail) removed first. Trials buy a trustworthy per-design verdict; only "
          "more designs buy a stronger headline.", ""]
    L += ["## Limits", "",
          "- SynAct's numbers are on a commercial tool and 14 different designs; the effect size is "
          "borrowed, not measured here.",
          "- The t-test assumes roughly normal per-trial outcomes. The violation ratio is floored at 0 "
          "(closure), so for agents that often close, a binomial model on closure per trial is the better "
          "second check.",
          "- No agent has been run. Every trial count here is conditional on an SD nobody has measured.", ""]
    open(os.path.join(RES, "POWER.md"), "w", newline="\n").write("\n".join(L))


if __name__ == "__main__":
    main()
