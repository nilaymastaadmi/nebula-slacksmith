#!/usr/bin/env python3
"""Phase 3 scorecard: buffer-only vs sizing-only vs both, per verdict.
Reads phase3/results/summary.tsv; nothing is typed in."""
import csv, os, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "results", "summary.tsv"), encoding="utf-8"), delimiter="\t"))
f = lambda x: float(x) if x not in ("", None, "READ_FAIL") else None

by = {}
for r in rows:
    by.setdefault(r["verdict"], []).append(r)

print("## Per-verdict lever gains (ns), scored period, reg-to-reg")
print(f"{'verdict':18} {'n':>2} {'both med':>9} {'buf med':>9} {'size med':>9} {'closed both':>12} {'closed buf':>11} {'closed size':>12}")
med = {}
for v, rs in sorted(by.items()):
    gb = [f(r["gain_both"]) for r in rs]; gu = [f(r["gain_buf"]) for r in rs]; gs = [f(r["gain_size"]) for r in rs]
    cb = sum(1 for r in rs if f(r["slack_both"]) is not None and f(r["slack_both"]) >= 0)
    cu = sum(1 for r in rs if f(r["slack_buf"]) is not None and f(r["slack_buf"]) >= 0)
    cs = sum(1 for r in rs if f(r["slack_size"]) is not None and f(r["slack_size"]) >= 0)
    med[v] = (st.median(gb), st.median(gu), st.median(gs))
    print(f"{v:18} {len(rs):>2} {med[v][0]:>9.3f} {med[v][1]:>9.3f} {med[v][2]:>9.3f} {cb:>8}/{len(rs):<3} {cu:>7}/{len(rs):<3} {cs:>8}/{len(rs):<3}")

print("\n## Per design")
print(f"{'design':16} {'verdict':18} {'A':>8} {'both':>8} {'buf':>8} {'size':>8} {'g_both':>7} {'g_buf':>7} {'g_size':>7}")
for r in sorted(rows, key=lambda r: (r["verdict"], -f(r["gain_both"]))):
    print(f"{r['design']:16} {r['verdict']:18} {f(r['slack_A']):>8.3f} {f(r['slack_both']):>8.3f} {f(r['slack_buf']):>8.3f} {f(r['slack_size']):>8.3f} {f(r['gain_both']):>7.3f} {f(r['gain_buf']):>7.3f} {f(r['gain_size']):>7.3f}")

F, D = "FANOUT_DOMINATED", "DEPTH_DOMINATED"
fan = by.get(F, []); dep = by.get(D, [])
def ratio(a, b): return (a / b) if b > 0 else float("inf")
print("\n## Registered predictions 8 to 11")
r8 = ratio(med[F][1], med[D][1]) if F in med and D in med else None
print(f"  P8 buffer-only median gain FANOUT/DEPTH >= 3x: {'CORRECT' if r8 is not None and r8 >= 3 else 'WRONG'} "
      f"({med.get(F,(0,0,0))[1]:.3f} / {med.get(D,(0,0,0))[1]:.3f} = {r8 if r8 is None else round(r8,2)})")
r9 = ratio(med[F][2], med[D][2]) if F in med and D in med else None
print(f"  P9 sizing-only median gain FANOUT/DEPTH < 2x: {'CORRECT' if r9 is not None and r9 < 2 else 'WRONG'} "
      f"({med.get(F,(0,0,0))[2]:.3f} / {med.get(D,(0,0,0))[2]:.3f} = {r9 if r9 is None else round(r9,2)})")
cu = sum(1 for r in fan if f(r["slack_buf"]) is not None and f(r["slack_buf"]) >= 0)
cs = sum(1 for r in fan if f(r["slack_size"]) is not None and f(r["slack_size"]) >= 0)
print(f"  P10 buffer-only closes >=3 of 5 FANOUT ({cu}/{len(fan)}) and sizing-only <=2 of 5 ({cs}/{len(fan)}): "
      f"{'CORRECT' if cu >= 3 and cs <= 2 else 'WRONG'}")
n11 = sum(1 for r in dep if f(r["gain_size"]) is not None and f(r["gain_buf"]) is not None and f(r["gain_size"]) > f(r["gain_buf"]))
print(f"  P11 sizing-only > buffer-only on >=6 of 8 DEPTH ({n11}/{len(dep)}): {'CORRECT' if n11 >= 6 else 'WRONG'}")
