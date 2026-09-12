#!/usr/bin/env python3
"""Cell area of a mapped netlist, summed from the liberty.

Needed because `report_design_area` is an OpenROAD command and **not** an
OpenSTA one: the zero-parasitic arms' power run printed
`invalid command name "report_design_area"` and returned no area at all. Rather
than edit the arm driver mid-experiment, area is derived afterwards from the
netlists the arms already wrote, which changes no arm and no timing number.

The liberty's own `area :` values are what OpenROAD sums too, so these numbers
are comparable with the physical arms' `report_design_area` output.

    python3 experiments/closure_cost/area_from_liberty.py NETLIST [NETLIST...]
"""
import os
import re
import sys

CELL_AREA = re.compile(r'cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)\s*\{', re.M)
AREA = re.compile(r'^\s*area\s*:\s*([0-9.eE+-]+)\s*;', re.M)
INST = re.compile(r'^\s*(sky130_fd_sc_hd__[A-Za-z0-9_]+)\s', re.M)
BUFLIKE = re.compile(r'^(sky130_fd_sc_hd__)(buf|clkbuf|bufinv|inv|clkinv|dlygate|dlymetal)', re.I)


def liberty_areas(path):
    """cell name -> area. Split on cell( headers and take each block's first
    area: line, which is the cell's own rather than a pin's."""
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    marks = [(m.start(), m.group(1)) for m in CELL_AREA.finditer(txt)]
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(txt)
        m = AREA.search(txt, pos, end)
        if m:
            out[name] = float(m.group(1))
    return out


def main():
    lib = os.environ["LIBERTY"]
    areas = liberty_areas(lib)
    print("liberty: %s, %d cells with an area" % (lib, len(areas)))
    print()
    print("| netlist | cells | buffer-like | area (u^2) | unpriced |")
    print("|---|---|---|---|---|")
    for net in sys.argv[1:]:
        if not os.path.exists(net):
            print("| %s | MISSING | | | |" % net)
            continue
        txt = open(net, encoding="utf-8", errors="replace").read()
        total, n, bufs, unpriced = 0.0, 0, 0, 0
        for m in INST.finditer(txt):
            name = m.group(1)
            n += 1
            if BUFLIKE.match(name):
                bufs += 1
            if name in areas:
                total += areas[name]
            else:
                unpriced += 1
        print("| `%s` | %d | %d | %.0f | %d |"
              % (os.path.basename(os.path.dirname(net)) + "/" + os.path.basename(net),
                 n, bufs, total, unpriced))
    return 0


if __name__ == "__main__":
    sys.exit(main())
