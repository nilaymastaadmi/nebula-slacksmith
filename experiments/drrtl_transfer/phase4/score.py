#!/usr/bin/env python3
"""Phase 4 scorecard: Dr. RTL skill #8 (condition-wire replication), plain and
(* keep *), against gold and against the buffer-only lever. Predictions 12-14.
Reads phase4/results/summary.tsv and gate_<design>_<variant>.txt; nothing is
typed in."""
import csv, glob, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "results", "summary.tsv"), encoding="utf-8"), delimiter="\t"))
f = lambda x: float(x) if x not in ("", None, "READ_FAIL", "None", "?") else None
R = {(r["design"], r["variant"], r["abc"]): r for r in rows}
designs = sorted({r["design"] for r in rows})

def gate(d, v):
    p = os.path.join(HERE, "results", f"gate_{d}_{v}.txt")
    if not os.path.exists(p): return "no gate file"
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r'"G4":\s*"([^"]+)"', t)
    if m: return m.group(1)
    m = re.search(r'"G3":\s*"([^"]+)"', t)
    return f"G3 {m.group(1)}" if m else "unparsed"

print(f"{'design':14} {'variant':13} {'A slack':>8} {'A topfo':>7} {'A share':>7} {'B(buf) slack':>12} {'B topfo':>7} {'gate'}")
p12 = p13a = p13b = p14 = 0; n = 0
for d in designs:
    g = R.get((d, "gold", "A"), {}); gb = R.get((d, "gold", "B"), {})
    print(f"{d:14} {'gold':13} {f(g.get('slack')) or 0:>8.3f} {g.get('top_fanout',''):>7} {g.get('share',''):>7} {f(gb.get('slack')) or 0:>12.3f} {gb.get('top_fanout',''):>7}")
    for v in ("skill8_plain", "skill8_keep"):
        a = R.get((d, v, "A"), {}); b = R.get((d, v, "B"), {})
        print(f"{'':14} {v:13} {f(a.get('slack')) or 0:>8.3f} {a.get('top_fanout',''):>7} {a.get('share',''):>7} {f(b.get('slack')) or 0:>12.3f} {b.get('top_fanout',''):>7} {gate(d, v)}")
    gf, pf, kf = f(g.get("top_fanout")), f(R.get((d,"skill8_plain","A"),{}).get("top_fanout")), f(R.get((d,"skill8_keep","A"),{}).get("top_fanout"))
    gs, ks, lever = f(g.get("slack")), f(R.get((d,"skill8_keep","A"),{}).get("slack")), f(gb.get("slack"))
    n += 1
    if gf and pf is not None and abs(pf - gf) / gf < 0.20: p12 += 1
    if gf and kf is not None and kf <= gf / 2: p13a += 1
    if gs is not None and ks is not None and lever is not None and (ks - gs) < (lever - gs): p13b += 1
    if gate(d, "skill8_plain").startswith("PROVEN") and gate(d, "skill8_keep").startswith("PROVEN"): p14 += 1
    print(f"{'':14} gain: keep-A {(ks or 0)-(gs or 0):+.3f} vs buffer-only lever {(lever or 0)-(gs or 0):+.3f}")

print("\n## Registered predictions 12 to 14")
print(f"  P12 plain replication changes top fanout <20% on >=2 of 3: {'CORRECT' if p12 >= 2 else 'WRONG'} ({p12}/{n})")
print(f"  P13 keep cuts top fanout >=2x on >=2 of 3 ({p13a}/{n}) AND keep gain < buffer-only on all 3 ({p13b}/{n}): "
      f"{'CORRECT' if p13a >= 2 and p13b == n else 'WRONG'}")
print(f"  P14 all 6 variants PROVEN at G4: {'CORRECT' if p14 == n else 'WRONG'} ({p14}/{n} designs with both proven)")
