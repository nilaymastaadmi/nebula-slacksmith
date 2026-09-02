#!/usr/bin/env python3
"""Trace a high-fanout synthesis temporary back to RTL-named signals.

For each FANOUT_DOMINATED design whose top cell drives a temporary (`_NNN_`),
walk the driving cone upward until RTL-named nets appear, so Dr. RTL skill #8
("replicate a high-fanout combinational condition wire for separate
consumers") can be applied to a real RTL signal rather than guessed at.

Usage (from the repo root, WSL):
  python3 experiments/drrtl_transfer/phase4_trace.py ~/drrtl_run
"""
import json, os, re, sys
sys.path.insert(0, "tools")
from classify_path import parse_netlist, CELL_RE, _conns, DRIVER_PINS

W = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/drrtl_run")
DESIGNS = {"aes": "key_expansion_128aes", "arm_cpu2": "risclite_mx",
           "communication": "sync_serial_communication_tx_rx", "datapath": "datapath"}
TEMP = re.compile(r"^_\d+_$")


def cell_index(path):
    """module -> {inst: (celltype, {pin: net})}"""
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r"^module\s+(\\?[^\s(]+)\s*\((.*?)^endmodule", txt, re.S | re.M):
        name, body = m.group(1).lstrip("\\"), m.group(2)
        cells = {}
        for ctype, inst, conns in CELL_RE.findall(body):
            cells[inst.lstrip("\\")] = (ctype, dict(_conns(conns)))
        out[name] = cells
    return out


def drivers_of(cells, net):
    """cells that drive `net` in this module"""
    return [(i, c) for i, (c, pins) in cells.items()
            if any(p in DRIVER_PINS and n == net for p, n in pins.items())]


def trace(cells, net, depth=0, seen=None, out=None):
    """Walk upward from `net` until RTL-named nets; collect (depth, name)."""
    seen = seen if seen is not None else set()
    out = out if out is not None else []
    if net in seen or depth > 6:
        return out
    seen.add(net)
    base = net.split("[")[0]
    if not TEMP.match(base):
        out.append((depth, net))
        return out
    for inst, ctype in drivers_of(cells, net):
        for pin, n in cells[inst][1].items():
            if pin not in DRIVER_PINS and n not in ("1'h0", "1'h1"):
                trace(cells, n, depth + 1, seen, out)
    return out


for d, top in DESIGNS.items():
    c = json.load(open(f"experiments/drrtl_transfer/results/{d}/classify.json"))
    net_path = f"{W}/{d}/A.v"
    mods = parse_netlist(net_path)
    idx = cell_index(net_path)
    t = c["top_cells"][0]
    inst, mod = t["inst"].split("/")[-1], t["module"]
    cells = idx.get(mod, {})
    ctype, pins = cells.get(inst, ("?", {}))
    drv = next((n for p, n in pins.items() if p in DRIVER_PINS), None)
    loads = mods.get(mod, {}).get("loads", {}).get(drv, 0) if drv else 0
    print(f"=== {d}: top cell {inst} ({ctype}) in {mod} drives {drv} (fanout {loads}), {t['incr_ns']} ns ===")
    print(f"    inputs: " + ", ".join(f"{p}={n}" for p, n in pins.items() if p not in DRIVER_PINS))
    named = trace(cells, drv) if drv else []
    named = sorted(set(named), key=lambda x: (x[0], x[1]))
    if not named:
        print("    no RTL-named net within 6 levels")
    for depth, n in named[:16]:
        print(f"    depth {depth}: {n}")
    # what consumes the high-fanout net: count by cell type
    cons = {}
    for i, (ct, pn) in cells.items():
        if any(p not in DRIVER_PINS and n == drv for p, n in pn.items()):
            cons[ct] = cons.get(ct, 0) + 1
    top3 = sorted(cons.items(), key=lambda x: -x[1])[:4]
    print(f"    consumers by cell type: " + ", ".join(f"{k} x{v}" for k, v in top3))
