#!/usr/bin/env python3
"""Score the classical arms from results/arms_raw.jsonl, per PREREGISTRATION.md.

Every number in results/RESULTS_classical.md is generated here from the raw
rows; nothing in that file is typed by hand. Bounds are asserted where each
quantity is computed. Pure standard library, Python 3.7+.

    python3 closureduel/arms/score.py
"""
import collections
import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import select_holdout  # noqa: E402

RES = os.path.join(ROOT, "results")
# Overrides exist only to test the scorer on a scratch file without touching results/.
RAW = os.environ.get("ARMS_RAW", os.path.join(RES, "arms_raw.jsonl"))
OUT = os.environ.get("ARMS_OUT", RES)
TOKENS = ("buffer", "upsize", "dnsize")
SEEDS = range(1, 11)
DRAWS = 8
C2, C3, BOTH = "S:buffer", "S:upsize+dnsize", "S:buffer+upsize+dnsize"


def die(msg):
    sys.exit("SCORE BROKEN: " + msg)


def load():
    rows = [json.loads(l) for l in open(RAW)]
    if not rows:
        die("raw file is empty")
    return rows


def committed():
    """Scored run 4 of the transfer study, development designs only."""
    req, ver = {}, {}
    p = os.path.join(REPO, "experiments/drrtl_transfer/results/summary.tsv")
    lines = open(p).read().splitlines()
    hdr = lines[0].split("\t")
    for ln in lines[1:]:
        f = dict(zip(hdr, ln.split("\t")))
        # Failed designs carry a label (e.g. NO_PATH) in this column, not a number.
        try:
            req[f["design"]] = float(f.get("required_ns", ""))
        except ValueError:
            pass
    p = os.path.join(REPO, "experiments/drrtl_transfer/results_reclassified/summary.tsv")
    lines = open(p).read().splitlines()
    hdr = lines[0].split("\t")
    for ln in lines[1:]:
        f = dict(zip(hdr, ln.split("\t")))
        ver[f["design"]] = f["new_verdict"]
    return req, ver


def main():
    rows = load()
    tiers = {d: t for t, ms in select_holdout.TIERS.items() for d in ms}
    dev = [d for d in tiers if d not in select_holdout.SEALED]
    if len(dev) != 10:
        die(f"{len(dev)} development designs")

    seen = {r["design"] for r in rows}
    leaked = seen & set(select_holdout.SEALED)
    if leaked:
        die(f"holdout designs in the raw rows: {sorted(leaked)} - the study is VOID")

    design = {r["design"]: r for r in rows if r["kind"] == "design" and r.get("status") == "OK"}
    failed_designs = sorted(r["design"] for r in rows if r["kind"] == "design" and r.get("status") != "OK")
    ev = collections.defaultdict(dict)
    for r in rows:
        if r["kind"] == "eval":
            ev[(r["design"], r["cand"])][r["run"]] = r
    cec = {(r["design"], r["cand"]): r for r in rows if r["kind"] == "cec"}

    # ---- determinism (P10): both runs present, byte-identical, same metrics
    nondet, incomplete = [], []
    for (d, c), runs in ev.items():
        if set(runs) != {1, 2}:
            incomplete.append((d, c))
            continue
        a, b = runs[1], runs[2]
        if a.get("status") != b.get("status") or (a.get("status") == "OK" and any(
                a.get(k) != b.get(k) for k in ("net_sha256", "wns", "tns", "area", "flops", "cells"))):
            nondet.append((d, c))

    def r1(d, c):
        return ev.get((d, c), {}).get(1)

    # ---- legality, per SPEC.md 2.1 and the registration
    def legal(d, c):
        r = r1(d, c)
        if r is None:
            return False, "MISSING"
        if r.get("build") != "OK":
            return False, "SYNTH_FAIL" if r.get("build") in ("SYNTH_FAIL", "FLOW_FAIL") else "TOOL_ERROR"
        if r.get("status") != "OK":
            return False, "TOOL_ERROR"
        if c != "C0":
            k = cec.get((d, c))
            if k is None:
                return False, "CEC_MISSING"
            if k["cec"] == "NOT_PROVEN":
                return False, "CEC_FAIL"
            if k["cec"] != "PROVEN":
                return False, "CEC_UNRESOLVED"
        c0 = r1(d, "C0")
        if r["ports"] != c0["ports"]:
            return False, "ILLEGAL_EDIT"
        if r["area"] > 1.20 * c0["area"]:
            return False, "ILLEGAL_EDIT"
        return True, "LEGAL"

    def outcome(d, c):
        ok, why = legal(d, c)
        r, c0 = r1(d, c), r1(d, "C0")
        o = {"cand": c, "legal": ok, "why": why}
        if r and r.get("status") == "OK":
            assert r["area"] > 0 and r["flops"] >= 0 and r["cells"] > 0, (d, c, r)
            o.update(wns=r["wns"], tns=r["tns"], area=r["area"], flops=r["flops"], cells=r["cells"],
                     gain=round(r["wns"] - c0["wns"], 3), wall_s=r["wall_s"])
        o["closed"] = bool(ok and o.get("wns", -1) >= 0)
        if not ok:
            o["cls"] = why
        elif o["closed"]:
            o["cls"] = "CLOSED"
        elif c != "C0" and o["gain"] <= 0:
            o["cls"] = "NO_IMPROVEMENT"
        else:
            o["cls"] = "IMPROVED" if c != "C0" else "BASELINE"
        return o

    def seq_label(seq):
        return "S:" + "+".join(seq)

    seqs = [seq_label(s) for L in (1, 2, 3) for s in __import__("itertools").product(TOKENS, repeat=L)]
    if len(seqs) != 39:
        die(f"{len(seqs)} sequences")

    table, c5dist = {}, {}
    for d in dev:
        if d not in design:
            continue
        c0 = r1(d, "C0")
        if c0 is None or c0.get("status") != "OK":
            continue
        arms = {"C0": outcome(d, "C0"), "C1": outcome(d, "C1"),
                "C2": outcome(d, C2), "C3": outcome(d, C3)}
        # C4: the committed choose_physical policy, with the legality bar.
        v = design[d]["verdict"]
        cur, path = arms["C0"], []
        if v in ("FANOUT_DOMINATED", "MIXED"):
            b = outcome(d, C2)
            kept = b["legal"] and b.get("wns", -1e9) > cur["wns"]
            path.append(f"buffer {'kept' if kept else 'reverted'}")
            if kept:
                cur = b
            s = outcome(d, BOTH if kept else C3)
            if s["legal"] and s.get("wns", -1e9) > cur["wns"]:
                cur = s
                path.append("sizing kept")
            else:
                path.append("sizing reverted")
        elif v == "DEPTH_DOMINATED":
            s = outcome(d, C3)
            if s["legal"] and s.get("wns", -1e9) > cur["wns"]:
                cur = s
                path.append("sizing kept")
            else:
                path.append("sizing reverted")
        else:
            path.append(f"verdict {v}: no route, C0 kept")
        c4 = dict(cur)
        c4["route"] = "; ".join(path)
        arms["C4"] = c4
        # C5: 8 draws per seed, best legal by WNS, C0 if none legal (registered wording).
        per_seed = []
        for seed in SEEDS:
            rng = random.Random(f"{d}:{seed}")
            best = None
            for _ in range(DRAWS):
                L = rng.choice([1, 2, 3])
                c = seq_label(tuple(rng.choice(TOKENS) for _ in range(L)))
                o = outcome(d, c)
                if o["legal"] and (best is None or o["wns"] > best["wns"]):
                    best = o
            per_seed.append(best if best is not None else dict(arms["C0"], cand="C0 (no legal draw)"))
        c5dist[d] = per_seed
        # C*: the lever-space ceiling, reported, never an arm.
        legal_all = [outcome(d, c) for c in seqs]
        legal_all = [o for o in legal_all if o["legal"]]
        arms["C*"] = max(legal_all, key=lambda o: o["wns"]) if legal_all else None
        arms["oracle_C2_C3"] = max([o for o in (arms["C2"], arms["C3"]) if o["legal"]],
                                   key=lambda o: o["wns"], default=None)
        table[d] = {"tier": tiers[d], "verdict": v, "period": design[d]["period"],
                    "required": design[d]["required"], "arms": arms}

    n = len(table)
    closed = {a: sum(1 for d in table if table[d]["arms"][a]["closed"]) for a in ("C0", "C1", "C2", "C3", "C4")}
    for a, k in closed.items():
        assert 0 <= k <= n, (a, k)
    c5_counts = [sum(1 for d in table if c5dist[d][i]["closed"]) for i in range(len(SEEDS))]
    assert all(0 <= k <= n for k in c5_counts)
    cstar = sum(1 for d in table if table[d]["arms"]["C*"] and table[d]["arms"]["C*"]["wns"] >= 0)

    # ---- predictions, evaluated by code
    creq, cver = committed()
    fanout = [d for d in table if table[d]["tier"] == "FANOUT"]
    depth = [d for d in table if table[d]["tier"] == "DEPTH"]
    p2 = [d for d in table if d in creq and abs(table[d]["required"] - creq[d]) <= 0.001]
    p3 = [d for d in table if "wns" in table[d]["arms"]["C1"]
          and abs(table[d]["arms"]["C1"]["wns"] - table[d]["arms"]["C0"]["wns"]) < 0.05]
    p5 = statistics.median([table[d]["arms"]["C2"].get("gain", 0.0) for d in depth]) if depth else None
    p6 = [d for d in depth if table[d]["arms"]["C3"].get("gain", 0) > 0]
    cand_cec = [k for k in cec.values() if k["cand"].startswith("S:")]
    p9_bad = [(k["design"], k["cand"], k["cec"]) for k in cand_cec if k["cec"] != "PROVEN"]
    p11 = [d for d in table if cver.get(d) == table[d]["verdict"]]
    uniform_best = max(closed["C2"], closed["C3"])
    preds = [
        ("P1", "C0 closes 0 of 10", closed["C0"] == 0, f"C0 closes {closed['C0']} of {n}"),
        ("P2", "container required == committed within 0.001 ns on >= 9 of 10", len(p2) >= 9,
         f"{len(p2)} of {n} match; differ: {sorted(set(table) - set(p2))}"),
        ("P3", "C1 moves WNS < 0.05 ns on >= 8 of 10", len(p3) >= 8, f"{len(p3)} of {n}"),
        ("P4", "C2 closes >= 2 of the FANOUT designs",
         sum(table[d]["arms"]["C2"]["closed"] for d in fanout) >= 2,
         f"{sum(table[d]['arms']['C2']['closed'] for d in fanout)} of {len(fanout)}"),
        ("P5", "C2 median WNS gain on DEPTH within +/-0.05 ns", p5 is not None and abs(p5) <= 0.05,
         f"median {p5}"),
        ("P6", "C3 improves WNS on >= 4 of the 5 DEPTH designs", len(p6) >= 4, f"{len(p6)} of {len(depth)}"),
        ("P7", "C4 closes >= max(C2, C3) applied uniformly", closed["C4"] >= uniform_best,
         f"C4 {closed['C4']}, C2 {closed['C2']}, C3 {closed['C3']}"),
        ("P8", "C5 median seed closes >= C4", statistics.median(c5_counts) >= closed["C4"],
         f"C5 median {statistics.median(c5_counts)} (range {min(c5_counts)}-{max(c5_counts)}), C4 {closed['C4']}"),
        ("P9", "every C2-C5 candidate that synthesises is CEC PROVEN", not p9_bad,
         f"{len(cand_cec) - len(p9_bad)} of {len(cand_cec)} PROVEN; not: {p9_bad[:6]}"),
        ("P10", "every candidate byte-identical across two runs", not nondet and not incomplete,
         f"{len(ev) - len(nondet) - len(incomplete)} of {len(ev)} identical; non-det {nondet[:6]}; incomplete {incomplete[:6]}"),
        ("P11", "classifier verdict == committed corrected verdict on 10 of 10", len(p11) == n == 10,
         f"{len(p11)} of {n}; differ: {sorted((d, table[d]['verdict'], cver.get(d)) for d in set(table) - set(p11))}"),
    ]

    gate = json.load(open(os.path.join(RES, "cec_gate_test.json")))
    void = []
    if closed["C0"] != 0:
        void.append("P1 failed: a C0 closes, so the period construction is broken")
    if not gate.get("gate_can_fail"):
        void.append("the CEC gate was not shown failing")
    if nondet:
        void.append(f"{len(nondet)} candidates are non-deterministic and were not reclassified")
    if n != 10:
        void.append(f"only {n} of 10 designs produced a baseline; failed: {failed_designs}")

    c4_vs_c5 = closed["C4"] >= statistics.median(c5_counts)
    c4_oracle = sum(1 for d in table if table[d]["arms"]["oracle_C2_C3"] and
                    table[d]["arms"]["C4"].get("wns", -1e9) >= table[d]["arms"]["oracle_C2_C3"]["wns"])

    cec_by_design = collections.defaultdict(collections.Counter)
    for k in cec.values():
        cec_by_design[k["design"]][k["cec"]] += 1
    seqc = [k for k in cec.values() if k["cand"].startswith("S:")]
    sizing = [k for k in seqc if "buffer" not in k["cand"]]
    cec_pattern = {
        "not_proven_total": sum(1 for k in seqc if k["cec"] != "PROVEN"),
        "not_proven_with_buffer": sum(1 for k in seqc if k["cec"] != "PROVEN" and "buffer" in k["cand"]),
        "sizing_only_total": len(sizing),
        "sizing_only_proven": sum(1 for k in sizing if k["cec"] == "PROVEN"),
        "c1_not_proven": sorted((k["design"], k["cec"]) for k in cec.values()
                                if k["cand"] == "C1" and k["cec"] != "PROVEN"),
        "sleep_inflated": sum(1 for k in cec.values() if k.get("cec_s", 0) > 360),
    }
    ctl_path = os.path.join(RES, "cex_control.json")
    cex_control = json.load(open(ctl_path)) if os.path.exists(ctl_path) else None

    summary = {"n_designs": n, "void": void, "closed": closed, "c5_closed_by_seed": c5_counts,
               "cec_by_design": {d: dict(c) for d, c in cec_by_design.items()},
               "cec_pattern": cec_pattern, "cex_control": cex_control,
               "timing_only_closed": {a: sum(1 for d in table if table[d]["arms"][a].get("wns", -1) >= 0)
                                      for a in ("C1", "C2", "C3")},
               "cstar_closed": cstar, "c4_ge_c5_median": c4_vs_c5, "c4_matches_oracle": c4_oracle,
               "predictions": [{"id": p, "claim": c, "correct": bool(ok), "measured": m} for p, c, ok, m in preds],
               "table": table, "c5": {d: [s.get("cand") for s in v] for d, v in c5dist.items()},
               "gate_test": gate, "failed_designs": failed_designs,
               "harness_commits": sorted({r.get("harness_commit") for r in rows if r.get("harness_commit")}),
               "images": sorted({r.get("image") for r in rows if r.get("image")})}
    json.dump(summary, open(os.path.join(OUT, "arms_summary.json"), "w"), indent=1, sort_keys=True)
    write_md(summary, c5dist)
    print(f"designs {n}; closed {closed}; C5 by seed {c5_counts}; C* {cstar}; void {void or 'none'}")
    for p in summary["predictions"]:
        print(f"  {p['id']:4s} {'CORRECT' if p['correct'] else 'WRONG  '}  {p['measured']}")


def fmt(x):
    return "" if x is None else (f"{x:+.3f}" if isinstance(x, float) else str(x))


def write_md(s, c5dist):
    L = ["# Classical arms: results", "",
         "Generated by `closureduel/arms/score.py` from `results/arms_raw.jsonl`. "
         "Nothing in this file is typed by hand; edit the scorer, not the file.", ""]
    L += [f"Harness commit(s): {', '.join(c[:7] for c in s['harness_commits'])}. "
          f"Image: `{', '.join(i[:19] for i in s['images'])}`. "
          f"Designs: {s['n_designs']} development, holdout untouched.", ""]
    L += ["## Void conditions", ""]
    L += [f"- **VOID: {v}**" for v in s["void"]] or ["- None triggered. The study stands."]
    ok = sum(p["correct"] for p in s["predictions"])
    L += ["", f"## Predictions: {ok} of {len(s['predictions'])} correct", "",
          "| # | Registered | Outcome | Measured |", "|---|---|---|---|"]
    L += [f"| {p['id']} | {p['claim']} | {'correct' if p['correct'] else '**WRONG**'} | {p['measured']} |"
          for p in s["predictions"]]
    wrong = [p for p in s["predictions"] if not p["correct"]]
    L += ["", "### Predictions that were wrong", ""]
    L += [f"- **{p['id']}**: registered \"{p['claim']}\"; measured {p['measured']}." for p in wrong] or ["- None."]
    L += ["", "## Closure count per arm (of %d)" % s["n_designs"], "",
          "| Arm | Closed |", "|---|---|"]
    names = {"C0": "C0 null", "C1": "C1 repair_design (unplaced)", "C2": "C2 buffer-only",
             "C3": "C3 sizing-only", "C4": "C4 classifier-routed"}
    L += [f"| {names[a]} | {k} |" for a, k in s["closed"].items()]
    cs = s["c5_closed_by_seed"]
    L += [f"| C5 random, median of 10 seeds (min to max) | {statistics.median(cs)} ({min(cs)} to {max(cs)}) |",
          f"| C\\* lever-space ceiling (a bound, **not an arm**) | {s['cstar_closed']} |", ""]
    rc = s["timing_only_closed"]
    L += ["### Timing only, legality NOT applied (not the registered result)", "",
          "WNS >= 0 counted regardless of whether equivalence was proven. This is the per-design WNS table "
          "below, aggregated, so a reader can see how much of the ranking above is set by the legality gate "
          "rather than by timing. Nothing in it is a legal closure.", "",
          "| Arm | WNS >= 0, any legality | of which legal |", "|---|---|---|"]
    L += [f"| {names[a]} | {rc[a]} | {s['closed'][a]} |" for a in ("C1", "C2", "C3")]
    L += [""]
    L += [f"C4 against the trivial baselines: closes {'at least as many as' if s['c4_ge_c5_median'] else 'fewer than'} "
          f"C5's median seed; matches or beats the per-design oracle max(C2, C3) on "
          f"{s['c4_matches_oracle']} of {s['n_designs']} designs.", ""]
    L += ["## Per design: WNS (ns) at the design's period, and the class of each arm", "",
          "| Design | Tier | Verdict | Period | C0 | C1 | C2 | C3 | C4 | C4 route | C\\* |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for d, t in sorted(s["table"].items(), key=lambda kv: (kv[1]["tier"], kv[0])):
        a = t["arms"]
        cell = lambda o: "" if o is None else f"{fmt(o.get('wns'))} {o['cls']}"
        L.append(f"| {d} | {t['tier']} | {t['verdict'].replace('_DOMINATED', '')} | {t['period']} | "
                 f"{cell(a['C0'])} | {cell(a['C1'])} | {cell(a['C2'])} | {cell(a['C3'])} | "
                 f"{cell(a['C4'])} | {a['C4']['route']} | {cell(a['C*'])} |")
    L += ["", "## Equivalence checks, by design and outcome", "",
          "| Design | PROVEN | NOT_PROVEN | TIMEOUT | other |", "|---|---|---|---|---|"]
    for d, c in sorted(s["cec_by_design"].items()):
        L.append(f"| {d} | {c.get('PROVEN', 0)} | {c.get('NOT_PROVEN', 0)} | {c.get('TIMEOUT', 0)} | "
                 f"{sum(v for k, v in c.items() if k not in ('PROVEN', 'NOT_PROVEN', 'TIMEOUT'))} |")
    e = s["cec_pattern"]
    L += ["", f"Of {e['not_proven_total']} lever-sequence candidates not PROVEN, **{e['not_proven_with_buffer']} contain "
          f"`buffer`**; of {e['sizing_only_total']} sizing-only candidates, {e['sizing_only_proven']} are PROVEN. "
          f"C1 rows not PROVEN: {e['c1_not_proven']}.",
          f"Rows whose recorded check time exceeds the 300 s cap by more than 60 s (wall clock inflated by a "
          f"machine sleep, 2026-09-21): {e['sleep_inflated']}.", ""]
    ctl = s.get("cex_control")
    if ctl:
        L += [f"Counterexample search control (`results/cex_control.json`): planted defect "
              f"**{ctl['planted_defect']['cex']}** in {ctl['planted_defect']['cex_s']} s; unmodified netlist "
              f"**{ctl['unmodified']['cex']}**. The all-candidate sweep was not run; see `PREREGISTRATION.md`, "
              "amendment 1 outcome.", ""]
    L += ["## Failure classes, all candidates", ""]
    cls = collections.Counter(o["cls"] for t in s["table"].values() for k, o in t["arms"].items()
                              if k in ("C1", "C2", "C3", "C4") and o)
    L += [f"- {k}: {v}" for k, v in sorted(cls.items())]
    L += ["", "## Area and flops, C0 against each arm", "",
          "| Design | C0 area | C1 | C2 | C3 | C4 | C0 flops | flops changed by any arm |", "|---|---|---|---|---|---|---|---|"]
    for d, t in sorted(s["table"].items()):
        a = t["arms"]
        ar = lambda o: "" if not o or "area" not in o else f"{o['area'] / a['C0']['area'] - 1:+.1%}"
        fl = sorted({o.get("flops") for k, o in a.items() if o and k in ("C1", "C2", "C3", "C4")} - {a["C0"]["flops"]})
        L.append(f"| {d} | {a['C0']['area']:.1f} | {ar(a['C1'])} | {ar(a['C2'])} | {ar(a['C3'])} | "
                 f"{ar(a['C4'])} | {a['C0']['flops']} | {fl or 'none'} |")
    L += ["", "## What this does not show", "",
          "- One trial per deterministic cell. No significance claim is made; C4 against C5 is a distribution over 10 seeds.",
          "- C1 is `repair_design -pre_placement` with no placement and no parasitics (registered limit). It warns that it "
          "falls back to wire-load models; whether that view matches the STA used here is untested.",
          "- WNS is register-to-register only; I/O paths are unconstrained in this SDC.",
          "- 10 development designs. The 5 holdout designs are sealed and were not run.", ""]
    open(os.path.join(OUT, "RESULTS_classical.md"), "w", newline="\n").write("\n".join(L))


if __name__ == "__main__":
    main()
