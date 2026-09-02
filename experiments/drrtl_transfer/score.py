#!/usr/bin/env python3
"""Determinism check (run 4 vs run 1) and the registered-prediction scorecard.

Usage: python3 experiments/drrtl_transfer/score.py
Reads results/summary.tsv (the scored run) and results_run1_as_registered/.
Every number printed comes from those two files; nothing is typed in.
"""
import csv, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))

def load(p):
    rows = list(csv.reader(open(p, encoding="utf-8"), delimiter="\t"))
    h = rows[0]
    out = {}
    for r in rows[1:]:
        r = r + [""] * (len(h) - len(r))
        out[r[0]] = dict(zip(h, r))
    return out

R4 = load(os.path.join(HERE, "results", "summary.tsv"))
R1 = load(os.path.join(HERE, "results_run1_as_registered", "summary.tsv"))

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

# ---- determinism: run 4 must reproduce run 1 on every row run 1 timed
print("## Determinism: run 4 vs run 1 (rows run 1 timed)")
same = diff = 0
for d, r1 in R1.items():
    if f(r1.get("slack_A")) is None:
        continue
    r4 = R4.get(d, {})
    keys = ["mapped_cells_A", "mapped_cells_B", "required_ns", "period_ns",
            "slack_A", "slack_B", "verdict", "fanout_share"]
    dif = [k for k in keys if r1.get(k) != r4.get(k)]
    if dif:
        diff += 1
        print(f"  DIFF {d}: " + ", ".join(f"{k} {r1.get(k)}->{r4.get(k)}" for k in dif))
    else:
        same += 1
print(f"  identical rows: {same}   differing rows: {diff}")

# ---- scope
timed = {d: r for d, r in R4.items() if f(r.get("slack_A")) is not None}
labels = {d: (r.get("mapped_cells_A") if f(r.get("slack_A")) is None else "timed")
          for d, r in R4.items()}
out_of_scope = {d: l for d, l in labels.items() if l != "timed"}
print(f"\n## Scope: {len(timed)} timed, {len(out_of_scope)} not: "
      + ", ".join(f"{d}={l}" for d, l in out_of_scope.items()))

# ---- verdict counts
by = {}
for d, r in timed.items():
    by.setdefault(r["verdict"], []).append(d)
print("\n## Verdicts (scored run)")
for v, ds in sorted(by.items()):
    print(f"  {v:18} {len(ds):2}  {', '.join(sorted(ds))}")

# ---- lever effect per verdict
print("\n## Physical lever (netlist B) per verdict")
for v, ds in sorted(by.items()):
    deltas = [f(timed[d]["delta_B"]) for d in ds]
    closed = sum(1 for d in ds if f(timed[d]["slack_B"]) is not None and f(timed[d]["slack_B"]) >= 0)
    improved = sum(1 for x in deltas if x is not None and x > 0.05)
    print(f"  {v:18} n={len(ds)}  improved>0.05ns: {improved}/{len(ds)}  "
          f"closed(MET after B): {closed}/{len(ds)}  "
          f"delta median {st.median(deltas):.3f}  min {min(deltas):.3f}  max {max(deltas):.3f}")

# ---- registered predictions
fan = by.get("FANOUT_DOMINATED", []); dep = by.get("DEPTH_DOMINATED", []); mix = by.get("MIXED", [])
print("\n## Registered predictions, scored")
print(f"  P1 all 20 time and classify: {'CORRECT' if len(timed)==20 else 'WRONG'} ({len(timed)} of 20)")
print(f"  P2 6 to 12 of 20 FANOUT_DOMINATED: {'CORRECT' if 6<=len(fan)<=12 else 'WRONG'} "
      f"({len(fan)} of 20; {len(fan)} of {len(timed)} in scope; {len(fan)+len(mix)} incl. MIXED)")
calls = {"aes":"FANOUT_DOMINATED","FIFO":"FANOUT_DOMINATED","LSTM":"FANOUT_DOMINATED",
         "arm_cpu1":"FANOUT_DOMINATED","cpu_fsm":"FANOUT_DOMINATED",
         "tv80":"DEPTH_DOMINATED","cpu_pipe":"DEPTH_DOMINATED","DSP":"DEPTH_DOMINATED",
         "datapath":"DEPTH_DOMINATED"}
ok = bad = uns = 0
for d, want in calls.items():
    got = timed.get(d, {}).get("verdict")
    if got is None: uns += 1; res = "unscorable"
    elif got == want: ok += 1; res = "correct"
    else: bad += 1; res = f"WRONG (got {got})"
    print(f"     P3 {d:10} predicted {want:17} {res}")
print(f"  P3 named calls: {ok} correct, {bad} wrong, {uns} unscorable")
fan_all = all(f(timed[d]["delta_B"]) > 0.05 for d in fan) if fan else False
dep_imp = sum(1 for d in dep if f(timed[d]["delta_B"]) > 0.05)
p4 = fan_all and dep_imp < len(dep)/2
print(f"  P4 PRIMARY lever improves every FANOUT ({sum(1 for d in fan if f(timed[d]['delta_B'])>0.05)}/{len(fan)}) "
      f"and fewer than half of DEPTH ({dep_imp}/{len(dep)}): {'CORRECT' if p4 else 'WRONG'}")
weird = [(d, timed[d]["top_incr"], timed[d]["top_fanout"]) for d in dep
         if f(timed[d]["top_incr"]) and f(timed[d]["top_incr"]) > 1.5
         and (timed[d]["top_fanout"] in ("None","") or f(timed[d]["top_fanout"]) is not None and f(timed[d]["top_fanout"]) <= 2)]
print(f"  P5 implausible delay at fanout<=2 on a DEPTH verdict: "
      f"{'CONFIRMED' if weird else 'not observed'} {weird}")
