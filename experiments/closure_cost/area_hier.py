#!/usr/bin/env python3
"""Cell count and area of a hierarchical netlist, counted per instance.

Why this exists. `area_from_liberty.py` sums every cell line in the netlist
text. A hierarchical netlist writes each module once, and `bench_top`
instantiates `aes_key_mem`'s parent twice (`u_aes_b`, `u_aes_e`), so the text
sum counts one AES instance and misses the other. Found on 2026-09-13: the zero-parasitic arms' 28,844 and 30,264 cells are text counts, and
beat 1 of the demo already shows the same text count missing 18,352 cells.

This walks the hierarchy from the top module and multiplies each module's
cells by the number of times it is instantiated. It changes no arm, no netlist
and no timing number; it re-reads the netlists the arms already wrote.

    python3 experiments/closure_cost/area_hier.py [--top bench_top] NETLIST [NETLIST...]
"""
import argparse
import os
import re
import sys
from functools import lru_cache

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from area_from_liberty import BUFLIKE, liberty_areas  # noqa: E402

MODULE = re.compile(r"^\s*module\s+(\S+)\s*\(", re.M)
ENDMODULE = re.compile(r"^\s*endmodule\b", re.M)
# An instance line: a type name, an instance name, then "(". Escaped Verilog
# identifiers (\$paramod$...\name) run to the next whitespace.
INSTANCE = re.compile(r"^\s*(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$\[\]]*)\s*\(", re.M)
KEYWORDS = {"module", "input", "output", "inout", "wire", "reg", "assign", "always", "initial"}


def parse(txt):
    """module name -> list of instantiated type names."""
    mods = {}
    for m in MODULE.finditer(txt):
        end = ENDMODULE.search(txt, m.end())
        body = txt[m.end(): end.start() if end else len(txt)]
        mods[m.group(1)] = [i.group(1) for i in INSTANCE.finditer(body)
                            if i.group(1) not in KEYWORDS]
    return mods


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", default="bench_top")
    ap.add_argument("netlists", nargs="+")
    a = ap.parse_args()
    areas = liberty_areas(os.environ["LIBERTY"])
    print("| netlist | cells, per instance | buffer-like | area (u^2) | cells, text | unpriced |")
    print("|---|---|---|---|---|---|")
    for net in a.netlists:
        txt = open(net, encoding="utf-8", errors="replace").read()
        mods = parse(txt)
        if a.top not in mods:
            print("| `%s` | top %s not found | | | | |" % (net, a.top))
            continue

        @lru_cache(maxsize=None)
        def walk(name):
            cells = bufs = unpriced = 0
            area = 0.0
            for t in mods[name]:
                if t in mods:
                    c, b, ar, u = walk(t)
                    cells += c; bufs += b; area += ar; unpriced += u
                elif t.startswith("sky130_fd_sc_hd__"):
                    cells += 1
                    bufs += 1 if BUFLIKE.match(t) else 0
                    if t in areas:
                        area += areas[t]
                    else:
                        unpriced += 1
            return cells, bufs, area, unpriced

        c, b, ar, u = walk(a.top)
        text = sum(1 for m in mods.values() for t in m if t.startswith("sky130_fd_sc_hd__"))
        print("| `%s` | %d | %d | %.0f | %d | %d |"
              % (os.path.basename(os.path.dirname(net)) + "/" + os.path.basename(net),
                 c, b, ar, text, u))
    return 0


if __name__ == "__main__":
    sys.exit(main())
