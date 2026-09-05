#!/usr/bin/env python3
"""
Does the physical lever change which RTL transform wins?

The closed loop reverted P2 under SDC v3 on a buffered netlist, and P2 is the
ONE proposal batch 1 found to improve clk_a (+0.485 under SDC v2 on an
unbuffered netlist). Two things differ between those runs, the SDC and the
buffering, so the loop's result alone cannot attribute the sign flip to
buffering.

This isolates it. One SDC (v2), one transform (P2), one variable: whether
`buffer -N 16; upsize; dnsize` is in the ABC script. Baseline and variant are
built by the identical flow on each side, which is the rule
docs/measurement-methodology.md exists to enforce.

    python3 experiments/closed_loop/context_control.py \\
        --liberty ~/sta_work/sky130hd_tt.lib \\
        --sta-bin ~/tools/OpenSTA/build/sta \\
        --variant ~/slacksmith_v3b/variants/P2_rv32i_core.v
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import remeasure
from slacksmith import BUFFER_SCRIPT

ap = argparse.ArgumentParser()
ap.add_argument("--liberty", required=True)
ap.add_argument("--sta-bin", required=True)
ap.add_argument("--yosys-bin",
                default=os.environ.get("OSS_CAD_BIN", os.path.expanduser("~/tools/oss-cad-suite/bin")) + "/yosys")
ap.add_argument("--variant", required=True,
                help="the spliced P2 rv32i_core.v")
ap.add_argument("--sdc", default=os.path.join(REPO, "sdc", "bench_top_v2.sdc"))
ap.add_argument("--workdir", default=os.path.expanduser("~/ctx_control"))
a = ap.parse_args()

a.liberty = os.path.expanduser(a.liberty)
a.sta_bin = os.path.expanduser(a.sta_bin)
a.variant = os.path.expanduser(a.variant)
rtl = os.path.join(REPO, "rtl")
clocks = ["clk_a"]

ndu = len(remeasure.dont_use_flags(a.liberty).split())
if ndu < 2:
    sys.exit(f"FATAL: dont_use returned {ndu} flags")
print(f"dont_use flags: {ndu}")

base_files = list(remeasure.BENCH_TOP_FILES)
var_files = [os.path.relpath(a.variant, rtl) if f == "rv32i_core.v" else f
             for f in base_files]
assert var_files != base_files, "variant substitution did not apply"

rows = []
for label, abc in (("unbuffered", None), ("buffered", BUFFER_SCRIPT)):
    out = {}
    for kind, files in (("baseline", base_files), ("P2", var_files)):
        d = os.path.join(a.workdir, f"{label}_{kind}")
        net = remeasure.synth_bench_top(
            a.yosys_bin, rtl, files, a.liberty, d, "mapped.v",
            abc_script=abc)
        s, _ = remeasure.sta_slack(a.sta_bin, a.liberty, net, "bench_top",
                                   a.sdc, clocks, d)
        out[kind] = s["clk_a"]
    delta = None
    if out["baseline"] is not None and out["P2"] is not None:
        delta = round(out["P2"] - out["baseline"], 3)
    rows.append((label, out["baseline"], out["P2"], delta))
    print(f"{label:12} baseline={out['baseline']}  P2={out['P2']}  "
          f"delta={delta:+}" if delta is not None else f"{label}: UNPARSED")

print()
print("| context | baseline clk_a | with P2 | delta |")
print("|---|---|---|---|")
for label, b, p, d in rows:
    print(f"| {label} | {b} | {p} | {d:+} |" if d is not None
          else f"| {label} | {b} | {p} | UNPARSED |")
