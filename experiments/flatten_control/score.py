#!/usr/bin/env python3
"""Score PREREGISTRATION.md predictions 19 to 25 from results/summary.tsv.

    python3 experiments/flatten_control/score.py
"""
import csv, os

HERE = os.path.dirname(os.path.abspath(__file__))
CLOCKS = ("clk_a", "clk_b", "clk_e")


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "results", "summary.tsv"), encoding="utf-8"),
                               delimiter="\t"))
    S = {}      # (arm, clock) -> slack
    F = {}      # (arm, clock) -> max fanout on path
    T = {}      # (arm, clock) -> (top cell, incr, fanout, verdict, share)
    cells = {}
    for r in rows:
        k = (r["arm"], r["clock"])
        S[k] = float(r["slack"]) if r["slack"] not in ("", "None") else None
        F[k] = int(r["max_fanout_on_path"]) if r["max_fanout_on_path"] not in ("", "None") else None
        T[k] = (r["top_cell"], r["top_incr"], r["top_fanout"], r["verdict"], r["share"])
        cells[r["arm"]] = r["cells"]

    print(f"{'arm':<4} {'cells':>7} " + " ".join(f"{c:>9}" for c in CLOCKS) + "   verdict / share / top cell (incr, fanout) / max fanout on path")
    for arm in "ABCDE":
        if (arm, "clk_a") not in S:
            continue
        line = f"{arm:<4} {cells[arm]:>7} " + " ".join(f"{S[(arm, c)]:>9}" for c in CLOCKS)
        for c in CLOCKS:
            t = T[(arm, c)]
            line += f"\n       {c}: {t[3]} {t[4]}  {t[0]} ({t[1]} ns, fanout {t[2]})  max fanout {F[(arm, c)]}"
        print(line)

    def ok(b):
        return "CORRECT" if b else "WRONG"

    p19 = (S[("A", "clk_a")], S[("A", "clk_b")], S[("A", "clk_e")]) == (-13.167, -18.957, -25.957) and \
          (S[("B", "clk_a")], S[("B", "clk_b")], S[("B", "clk_e")]) == (1.75, 5.556, -1.444)
    print(f"\nP19 A and B reproduce the record exactly: {ok(p19)}")
    if not p19:
        print("    EXPERIMENT VOID per registration; the rest is reported for the record only")
    if ("D", "clk_e") in S:
        print(f"P20 D clk_e above B (-1.444): {ok(S[('D', 'clk_e')] > -1.444)} (D {S[('D', 'clk_e')]})")
        print(f"P21 D clk_a above B (+1.75): {ok(S[('D', 'clk_a')] > 1.75)} (D {S[('D', 'clk_a')]})")
        mf = max(F[("D", c)] or 0 for c in CLOCKS)
        print(f"P22 D: no cell on the three worst paths above fanout 100: {ok(mf <= 100)} (max {mf})")
        print(f"P23 D closes clk_e: {ok(S[('D', 'clk_e')] >= 0)} (D {S[('D', 'clk_e')]})")
    if ("C", "clk_e") in S:
        diffs = {c: round(S[("C", c)] - S[("A", c)], 3) for c in CLOCKS}
        print(f"P24 |C - A| < 2 ns on every group: {ok(all(abs(v) < 2 for v in diffs.values()))} ({diffs})")
    if ("E", "clk_a") in S and ("D", "clk_a") in S:
        print(f"P25 E clk_a below D clk_a: {ok(S[('E', 'clk_a')] < S[('D', 'clk_a')])} "
              f"(D {S[('D', 'clk_a')]}, E {S[('E', 'clk_a')]})")
        for c in CLOCKS:
            print(f"    {c}: D {S[('D', c)]}  E {S[('E', c)]}  ({round(S[('E', c)] - S[('D', c)], 3):+})")
    # Amendment 1: arms F and G.
    if ("F", "clk_e") in S:
        rows_f = [r for r in rows if r["arm"] == "F" and r["clock"] == "clk_e"]
        # "no flop output with more than 32 loads on F's worst clk_e path" is
        # read from the report: any dfxtp/dfrtp/dfstp row with fanout > 32.
        rpt = open(os.path.join(HERE, "results", "F_clk_e.rpt"), encoding="utf-8").read()
        import re
        flops_hi = [(m.group(1), int(m.group(2))) for m in re.finditer(
            r"^\s*(\d+)\s+[-\d.]+\s+[-\d.]+\s+[v^]\s+\S+/Q\s+\(sky130_fd_sc_hd__(df\w+)\)", rpt, re.M)
            if int(m.group(1)) > 32] if False else []
        for m in re.finditer(r"^\s*(\d+)\s+[-\d.]+\s+[-\d.]+\s+[v^]\s+\S+/Q\s+\(sky130_fd_sc_hd__(df\w+)\)", rpt, re.M):
            if int(m.group(1)) > 32:
                flops_hi.append((m.group(2), int(m.group(1))))
        p26 = S[("F", "clk_e")] > S[("D", "clk_e")] and not flops_hi
        print(f"P26 F clk_e above D and no flop output above 32 loads on F's clk_e path: {ok(p26)} "
              f"(F {S[('F', 'clk_e')]}, D {S[('D', 'clk_e')]}, flops above 32: {flops_hi})")
        print(f"P27 F does not close clk_e: {ok(S[('F', 'clk_e')] < 0)} (F {S[('F', 'clk_e')]})")
        for c in CLOCKS:
            print(f"    {c}: D {S[('D', c)]}  F {S[('F', c)]}  ({round(S[('F', c)] - S[('D', c)], 3):+})")
    if ("G", "clk_e") in S and ("F", "clk_e") in S:
        print(f"P28 G clk_e above F clk_e: {ok(S[('G', 'clk_e')] > S[('F', 'clk_e')])} "
              f"(F {S[('F', 'clk_e')]}, G {S[('G', 'clk_e')]})")
        for c in CLOCKS:
            print(f"    {c}: F {S[('F', c)]}  G {S[('G', c)]}  ({round(S[('G', c)] - S[('F', c)], 3):+})")


if __name__ == "__main__":
    main()
