#!/usr/bin/env python3
"""R53 (amendment 2): gold and the composed RTL through the ABC buffering lever.

The loop's physical lever is an ABC script (buffer -N 16; upsize; dnsize),
applied at mapping with no placement and no parasitics. It is the same lever
experiments/drrtl_transfer/ and experiments/depth_i2c/ measure with, so this
run gives the fanout-dominated cell of the survival table at the same level as
the depth-dominated cell. Every other composed_rtl number is either unbuffered
(run.sh) or post-repair_design (repair.sh); this is the level in between.

Both netlists are built here, from the same sources cr_composed_A4_O2_O1 was
built from, differing from run.sh only in the ABC script. Prints a table and
writes results/abc_buffered_pair.txt.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "tools"))
import remeasure, slacksmith  # noqa: E402

work = os.environ["SLACKSMITH_WORK"]
lib = os.environ["LIBERTY"]
sta = os.environ["STA_BIN"]
yosys = os.path.join(os.environ["OSS_CAD_BIN"], "yosys")
sdc = os.path.join(REPO, "sdc", "bench_top_v3.sdc")
clocks = ["clk_a", "clk_b", "clk_e"]
rtl = os.path.join(REPO, "rtl")


def slacks(files, d):
    os.makedirs(d, exist_ok=True)
    net = remeasure.synth_bench_top(yosys, rtl, files, lib, d, "mapped.v",
                                    abc_script=slacksmith.BOTH)
    s, _ = remeasure.sta_slack(sta, lib, net, "bench_top", sdc, clocks, d)
    return s, net


print("ABC script:", slacksmith.BOTH)
gold, gnet = slacks(remeasure.BENCH_TOP_FILES, os.path.join(work, "cr_abc_gold"))

swapped_top = os.path.join(work, "cr_composed_A4_O2_O1", "variant", "bench_top_variant.v")
composed = os.path.join(HERE, "aes_key_mem_composed.v")
for f in (swapped_top, composed):
    if not os.path.exists(f):
        sys.exit(f"FATAL: missing {f}; run run.sh first")
files = []
for f in remeasure.BENCH_TOP_FILES:
    if f == "bench_top.v":
        files.append(swapped_top)
    elif f == "aes/aes_key_mem.v":
        files.append(composed)
    else:
        files.append(f)
comp, cnet = slacks(files, os.path.join(work, "cr_abc_composed"))

lines = [f"{'clock':<8} {'gold+ABC':>10} {'composed+ABC':>13} {'delta':>8}"]
for c in clocks:
    g, v = gold.get(c), comp.get(c)
    if g is None or v is None:
        lines.append(f"{c:<8} {'UNPARSED':>10} {'UNPARSED':>13} {'--':>8}")
    else:
        lines.append(f"{c:<8} {g:>10.3f} {v:>13.3f} {v - g:>+8.3f}")
cells = lambda p: sum(1 for l in open(p) if l.lstrip().startswith("sky130_fd_sc_hd__"))
lines.append(f"cells: gold+ABC {cells(gnet)}, composed+ABC {cells(cnet)}")
out = "\n".join(lines)
print(out)
os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
with open(os.path.join(HERE, "results", "abc_buffered_pair.txt"), "w") as f:
    f.write(out + "\n")
