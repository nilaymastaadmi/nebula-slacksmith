#!/usr/bin/env python3
"""Score PREREGISTRATION.md predictions 41 to 45.

    python3 experiments/max_fanout/score.py
"""
import gzip, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
import classify_path as cp  # noqa: E402

RES = os.path.join(HERE, "results")
CLOCKS = ("clk_a", "clk_b", "clk_e")
# baselines already on the record, experiments/openroad_flat/
BASE = {"E": {"clk_a": 10.175, "clk_b": 5.225, "clk_e": -0.952, "area": 21.7},
        "C": {"clk_a": 10.087, "clk_b": 5.489, "clk_e": -2.243, "area": 18.7}}


def blocks(arm):
    p = os.path.join(RES, f"{arm}.flow.log")
    if not os.path.exists(p):
        return None, None, []
    txt = open(p, encoding="utf-8", errors="replace").read()
    parts = txt.split("=====> REPAIR_DESIGN")
    def per_clock(seg):
        out = {}
        for c in CLOCKS:
            bits = re.split(rf"---CLOCK:{c}---", seg)
            if len(bits) > 1:
                out[c] = bits[1][:6000]
        return out
    areas = [int(x) for x in re.findall(r"Design area (\d+) u\^2", txt)]
    return per_clock(parts[0]), (per_clock(parts[1]) if len(parts) > 1 else {}), areas


def slack(rpt):
    m = re.findall(r"([\-0-9.]+)\s+slack \((?:MET|VIOLATED)\)", rpt or "")
    return float(m[0]) if m else None


def ctl_slacks(name):
    p = os.path.join(RES, f"ctl_{name}.rpt")
    if not os.path.exists(p):
        return {}
    txt = open(p, encoding="utf-8", errors="replace").read()
    out = {}
    for c in CLOCKS:
        bits = re.split(rf"---CLOCK:{c}---", txt)
        if len(bits) > 1:
            out[c] = slack(bits[1][:6000])
    return out


def main():
    ok = lambda b: "CORRECT" if b else "WRONG"
    data = {}
    for arm in ("MF16-E", "MF8-E", "MF32-E", "MF16-C"):
        b, a, areas = blocks(arm)
        if b is None:
            continue
        data[arm] = (b, a, areas)
        growth = (100.0 * (areas[1] - areas[0]) / areas[0]) if len(areas) >= 2 else None
        print(f"{arm:<8} area {areas[0]} -> {areas[1]} u^2 ({growth:+.1f}%)"
              if growth is not None else f"{arm}: incomplete")
        for c in CLOCKS:
            sb, sa = slack(b.get(c)), slack(a.get(c))
            print(f"   {c}: before {sb:>9}  after {sa:>9}  delta {round(sa - sb, 3):+}")

    v3, mf = ctl_slacks("bench_top_v3"), ctl_slacks("bench_top_v3_mf16")
    p41 = v3 and v3 == mf
    print(f"\nP41 zero-parasitic slacks unchanged by the constraint: {ok(p41)} "
          f"(v3 {v3}, mf16 {mf})")

    if "MF16-E" not in data:
        return
    b16, a16, ar16 = data["MF16-E"]

    tmp = tempfile.mkdtemp(prefix="mf_")
    net = os.path.join(tmp, "r.v")
    with gzip.open(os.path.join(RES, "MF16-E.repaired.v.gz"), "rb") as fi, open(net, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    mods = cp.parse_netlist(net)
    over = {}
    for c in CLOCKS:
        rows, _s, _m = cp.parse_path(a16.get(c, ""))
        hi = []
        for r in rows:
            fo_, _own = cp.resolve_fanout(mods, "bench_top", r["inst"])
            if (fo_ or 0) > 16:
                hi.append((r["cell"].replace("sky130_fd_sc_hd__", ""), round(r["incr"], 3), fo_))
        over[c] = hi
    p42 = not any(over.values())
    print(f"P42 MF16-E: no cell above fanout 16 on the three worst paths: {ok(p42)}")
    for c in CLOCKS:
        print(f"    {c}: over 16 -> {over[c]}")

    p43 = slack(a16.get("clk_e")) >= 0
    print(f"P43 MF16-E closes clk_e: {ok(p43)} ({slack(a16.get('clk_e'))})")

    g16 = 100.0 * (ar16[1] - ar16[0]) / ar16[0]
    p44 = g16 > BASE["E"]["area"]
    print(f"P44 MF16-E area growth above OR-E's +21.7%: {ok(p44)} ({g16:+.1f}%)")

    got = {n: slack(data[f"MF{n}-E"][1].get("clk_e"))
           for n in (8, 16, 32) if f"MF{n}-E" in data}
    if len(got) == 3:
        best = max(got, key=lambda k: got[k])
        p45 = best != 8
        print(f"P45 clk_e not monotonic in the limit (8 is not best): {ok(p45)} "
              f"({got}, best limit {best})")

    print(f"\nagainst the no-constraint baselines: MF16-E clk_e "
          f"{slack(a16.get('clk_e'))} vs OR-E {BASE['E']['clk_e']}")
    if "MF16-C" in data:
        print(f"                                     MF16-C clk_e "
              f"{slack(data['MF16-C'][1].get('clk_e'))} vs OR-C {BASE['C']['clk_e']}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
