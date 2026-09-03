#!/usr/bin/env python3
"""Generate sdc/bench_top_v3_mf<N>.sdc: v3 plus one set_max_fanout line.

    python3 sdc/make_v3_maxfanout.py 16

The frozen v3 file is read and copied verbatim. Nothing in it is edited,
re-derived or re-typed, so the diff against v3 is exactly the appended
block and `diff` proves it. See experiments/max_fanout/PREREGISTRATION.md
for why the constraint is added in a new file rather than to v3.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "bench_top_v3.sdc")

NOTE = """
# -----------------------------------------------------------------------
# 6. Max fanout, added {date} in a NEW file, never by editing v3.
#
#    Everything above this line is bench_top_v3.sdc verbatim.
#
#    WHY THIS EXISTS. sky130hd's liberty declares `default_fanout_load`
#    and NO `default_max_fanout`, and the OpenROAD sky130hd platform sets
#    no max fanout either. So nothing in the flow ever declared a fanout
#    limit, and `repair_design` had no rule to repair against: it left a
#    cell driving 65 loads on all three worst paths
#    (experiments/openroad_flat/). This file gives it one.
#
#    WHY {n}. It is the limit this project's own physical lever has
#    enforced since before this experiment existed: the ABC script is
#    `buffer -N 16`, committed in tools/slacksmith.py. Using the same
#    number asks both levers for the same thing, and it was not chosen
#    by looking at any result. The sensitivity of the result to this
#    choice is reported by running 8 and 32 as well, all three published.
# -----------------------------------------------------------------------
set_max_fanout {n} [current_design]
"""


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    src = open(SRC, encoding="utf-8").read()
    out = os.path.join(HERE, f"bench_top_v3_mf{n}.sdc")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(src)
        f.write(NOTE.format(n=n, date="2026-09-03"))
    print(f"wrote {out} ({len(src.splitlines())} lines copied from "
          f"bench_top_v3.sdc, {len(NOTE.splitlines())} appended)")


if __name__ == "__main__":
    main()
