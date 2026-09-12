#!/usr/bin/env python3
"""Score R56 to R60 from results/survival.tsv. Numbers here are computed, not
typed; NOTES.md quotes this script's output.

    python3 experiments/depth_i2c/score.py
"""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
rows = {}
for r in csv.DictReader(open(os.path.join(HERE, "results", "survival.tsv"), encoding="utf-8"), delimiter="\t"):
    rows[r["variant"]] = r

def f(v):
    try: return float(v)
    except (TypeError, ValueError): return None

g = rows.get("gold"); c = rows.get("control"); g2 = rows.get("gold_run2")
if not g:
    sys.exit("no gold row")
gA, gB, gC = f(g["A_unbuffered"]), f(g["B_abc_lever"]), f(g["C_after_repair"])
print(f"gold: A={gA} B={gB} C={gC} (lever alone: B-A={gB-gA:+.3f}, repair: C={gC})")

# R60 determinism
if g2:
    d60 = f(g2["C_after_repair"]) - gC
    print(f"R60 gold twice through OpenROAD: delta {d60:+.3f} -> {'CONFIRMED' if abs(d60) < 1e-9 else 'WRONG'}")
# R59 control floor
if c:
    dC = f(c["C_after_repair"]) - gC
    print(f"R59 control post-repair movement {dC:+.3f} -> {'CONFIRMED' if abs(dC) < 0.050 else 'WRONG'}")
    print(f"    control: A {f(c['A_unbuffered'])-gA:+.3f}  B {f(c['B_abc_lever'])-gB:+.3f}")

for name, r in rows.items():
    if name in ("gold", "control", "gold_run2"): continue
    dA = f(r["A_unbuffered"]) - gA; dB = f(r["B_abc_lever"]) - gB; dCv = f(r["C_after_repair"]) - gC
    print(f"\n{name}:")
    print(f"  A unbuffered   {dA:+.3f}")
    print(f"  B after ABC    {dB:+.3f}   ({(dB/dA*100) if dA else float('nan'):.0f}% of A retained)")
    print(f"  C after repair {dCv:+.3f}   (control moved {dC:+.3f})" if c else f"  C after repair {dCv:+.3f}")
    print(f"  R56 A > +0.050          -> {'CONFIRMED' if dA > 0.050 else 'WRONG'}")
    print(f"  R57 B >= 50% of A       -> {'CONFIRMED' if (dA > 0 and dB >= 0.5*dA) else ('VOID (A not positive)' if dA <= 0 else 'WRONG')}")
    if c:
        print(f"  R58 C > 0 and > control -> {'CONFIRMED' if (dCv > 0 and dCv > abs(dC)) else 'WRONG'}")
    print(f"  area after repair: gold {g['area_after']} variant {r['area_after']}")
