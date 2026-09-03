#!/usr/bin/env python3
"""Score PREREGISTRATION.md predictions 34 to 38.

    python3 experiments/openroad_flat/score.py

Slacks come from the two flow logs. Prediction 35 asks about fanout on the
post-repair worst paths, which OpenROAD's report_checks was not asked to
print, so it is measured from the repaired netlist with the same parser the
classifier uses.
"""
import gzip, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
import classify_path as cp  # noqa: E402

RES = os.path.join(HERE, "results")
CLOCKS = ("clk_a", "clk_b", "clk_e")


def blocks(arm):
    txt = open(os.path.join(RES, f"OR_{arm}.flow.log"), encoding="utf-8",
               errors="replace").read()
    before, after = txt.split("=====> REPAIR_DESIGN")
    def per_clock(seg):
        out = {}
        for c in CLOCKS:
            parts = re.split(rf"---CLOCK:{c}---", seg)
            if len(parts) > 1:
                out[c] = parts[1][:6000]
        return out
    areas = [int(x) for x in re.findall(r"Design area (\d+) u\^2", txt)]
    return per_clock(before), per_clock(after), areas


def slack(rpt):
    m = re.findall(r"([\-0-9.]+)\s+slack \((?:MET|VIOLATED)\)", rpt)
    return float(m[0]) if m else None


def main():
    tmp = tempfile.mkdtemp(prefix="orflat_")
    data = {}
    for arm in ("C", "E"):
        b, a, areas = blocks(arm)
        data[arm] = (b, a, areas)
        print(f"OR-{arm}   area {areas[0]} -> {areas[1]} u^2 "
              f"({100.0 * (areas[1] - areas[0]) / areas[0]:+.1f}%)")
        for c in CLOCKS:
            sb, sa = slack(b.get(c, "")), slack(a.get(c, ""))
            print(f"   {c}: before {sb:>9}  after {sa:>9}  "
                  f"delta {round(sa - sb, 3):+}")

    ok = lambda x: "CORRECT" if x else "WRONG"
    bC, aC, arC = data["C"]
    p34 = all(slack(aC[c]) > slack(bC[c]) for c in CLOCKS)
    print(f"\nP34 OR-C improves every group: {ok(p34)} "
          f"({[round(slack(aC[c]) - slack(bC[c]), 3) for c in CLOCKS]})")

    # P35: fanout on the post-repair worst paths, from the repaired netlist.
    gz = os.path.join(RES, "OR_C.repaired.v.gz")
    net = os.path.join(tmp, "OR_C.repaired.v")
    with gzip.open(gz, "rb") as fi, open(net, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    mods = cp.parse_netlist(net)
    worst = {}
    for c in CLOCKS:
        rows, _s, _m = cp.parse_path(aC[c])
        fos = []
        for r in rows:
            fo_, _own = cp.resolve_fanout(mods, "bench_top", r["inst"])
            fos.append((r["cell"], round(r["incr"], 3), fo_))
        worst[c] = fos
    over = {c: [f for f in v if (f[2] or 0) > cp.FANOUT_HI] for c, v in worst.items()}
    p35 = not any(over.values())
    print(f"P35 OR-C post-repair: no cell above fanout {cp.FANOUT_HI} on the three "
          f"worst paths: {ok(p35)}")
    for c in CLOCKS:
        mx = max((f[2] or 0) for f in worst[c]) if worst[c] else None
        print(f"    {c}: {len(worst[c])} cells, max fanout {mx}, over threshold {over[c]}")

    p36 = all(slack(aC[c]) >= 0 for c in CLOCKS)
    print(f"P36 OR-C closes all three: {ok(p36)} "
          f"({ {c: slack(aC[c]) for c in CLOCKS} })")

    growth = 100.0 * (arC[1] - arC[0]) / arC[0]
    print(f"P37 OR-C area growth below the hierarchical +20.2%: "
          f"{ok(growth < 20.2)} ({growth:+.1f}%)")

    _bE, aE, _arE = data["E"]
    p38 = slack(aE["clk_e"]) > slack(aC["clk_e"])
    print(f"P38 OR-E post-repair clk_e above OR-C's: {ok(p38)} "
          f"(OR-E {slack(aE['clk_e'])}, OR-C {slack(aC['clk_e'])})")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
