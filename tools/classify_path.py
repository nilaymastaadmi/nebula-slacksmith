#!/usr/bin/env python3
"""
classify_path.py -- decide WHY a timing path is slow before proposing a fix.

Motivation, measured rather than assumed. On the v2 benchmark the worst
`clk_b` path carried 27.045 ns of its 30.602 ns path delay in TWO cells
inside `aes_key_mem`, a 15-entry by 128-bit register array read through a
combinational 15-to-1 mux. No RTL rewrite shortens a net's fanout delay, and
batch 1 shows what happens when one is attempted anyway: 4 transforms
formally proven correct, 3 of which made timing worse, the best moving the
path group by 0.485 ns. A buffering pass on the same design, changing zero
lines of RTL, moved `clk_b` by 17.557 ns and closed it.

So the proposer needs a router in front of it. This is that router. It reads
an OpenSTA `report_checks` path plus the mapped netlist and answers:

  NO_ACTION         the path already meets its constraint.
  FANOUT_DOMINATED  most of the delay sits in cells driving many loads.
                    Route to buffering/sizing. Do not spend an LLM proposal
                    here; the lever is not in the RTL.
  DEPTH_DOMINATED   the delay is spread across ordinary low-fanout cells.
                    This is where an RTL transform can help and where the
                    typed-obligation gate earns its keep.
  MIXED             neither test is decisive. Reported as such rather than
                    forced into a bucket.

The primary statistic is `fanout_delay_share`: the fraction of the path's
delay contributed by cells whose driven net has at least FANOUT_HI loads.
That answers the question directly, where an earlier version of this file
used "share of delay in the top 2 cells AND max fanout" and mislabelled the
AES path as MIXED because the two tests disagreed.

Loads are counted THROUGH hierarchy. The netlist this flow writes is
hierarchical, and an earlier version stopped at every submodule port, so a
net feeding 128 flops through a port read as fanout 1. The tell was a
6.762 ns delay reported on a cell at fanout 1, which is not credible. Modules
are now resolved leaf-first: for every module and input port, the number of
leaf pins that port ultimately drives is computed, and a net connecting to
such a port is charged that count.

HONEST LIMIT ON THE THRESHOLDS. The three constants below were chosen after
looking at this benchmark, not before, so they describe it and are not
validated on held-out designs. What is checked is that they separate paths
known by independent measurement to be of different kinds. See
`docs/path-classification.md` for the validation table.

Usage:
  python3 tools/classify_path.py --report path.rpt --netlist mapped.v
  python3 tools/classify_path.py --report path.rpt --netlist mapped.v --json
"""
import argparse, json, re, sys

DRIVER_PINS = {"X", "Y", "Q", "Q_N", "SUM", "COUT", "CO"}

# --- thresholds, named constants so they are auditable and not buried ---
FANOUT_HI       = 32    # loads on one net before it counts as high fanout
FANOUT_SHARE_HI = 0.50  # >=50% of path delay from such cells -> fanout
FANOUT_SHARE_LO = 0.20  # <=20% -> depth

CELL_RE = re.compile(r"(sky130_fd_sc_hd__\w+)\s+(\\?\S+?)\s*\((.*?)\);", re.S)
# Submodule TYPE names can also be parameterised (\$paramod\...), so the type
# group accepts any non-space run; the KEYWORDS filter below rejects Verilog
# keywords that would otherwise match this shape.
SUB_RE = re.compile(r"^\s*(\\?[^\s(]+)\s+(\\?\S+?)\s*\((.*?)\);", re.S | re.M)
CONN_RE = re.compile(r"\.(\w+)\((.*?)\)")
KEYWORDS = {"module", "endmodule", "input", "output", "inout", "wire", "reg",
            "assign", "parameter", "localparam", "always", "initial",
            "generate", "function", "task"}
CONST = ("1'h0", "1'h1")


def _conns(text):
    return [(p, n.strip()) for p, n in CONN_RE.findall(text)]


def parse_netlist(path):
    """Return {module: {loads, drv, cells, subs}} with hierarchy-aware loads."""
    txt = open(path, encoding="utf-8", errors="replace").read()

    raw = {}
    # Module names may be Yosys parameterised names such as
    # \$paramod\opReg\WIDTH=s32'00000000000000000000000000100000 , which
    # contain '=', quotes and backslashes. The earlier pattern [\w$.]+ never
    # matched those headers, so every cell inside a parameterised submodule
    # was unresolvable and read as fanout None. Found 2026-09-02 on the DSP
    # and tv80 designs of the Dr. RTL benchmark; this project's own benchmark
    # has no parameterised modules and never exercised it.
    for m in re.finditer(r"^module\s+(\\?[^\s(]+)\s*\((.*?)^endmodule",
                         txt, re.S | re.M):
        name = m.group(1).lstrip("\\")
        body = m.group(2)
        inputs = set()
        for decl in re.findall(
                r"^\s*input\s+(?:wire\s+)?(?:\[[^\]]*\]\s*)?(.+?);", body, re.M):
            for tok in decl.split(","):
                tok = tok.strip().lstrip("\\")
                if tok:
                    inputs.add(tok)
        cells, drv, own_loads = {}, {}, {}
        for ctype, inst, conns in CELL_RE.findall(body):
            inst = inst.lstrip("\\")
            cells[inst] = ctype
            for pin, net in _conns(conns):
                if not net or net in CONST:
                    continue
                if pin in DRIVER_PINS:
                    drv[inst] = net
                else:
                    own_loads[net] = own_loads.get(net, 0) + 1
        stripped = CELL_RE.sub("", body)
        subs = []
        for mtype, inst, conns in SUB_RE.findall(stripped):
            mtype = mtype.lstrip("\\")
            if mtype in KEYWORDS:
                continue
            subs.append((mtype, inst.lstrip("\\"), _conns(conns)))
        raw[name] = {"inputs": inputs, "cells": cells, "drv": drv,
                     "own_loads": own_loads, "subs": subs}

    # Leaf-first resolution. port_pins[module][port] is the number of leaf
    # input pins that port ultimately drives inside that module.
    port_pins, done = {}, set()
    for _ in range(len(raw) + 2):
        progress = False
        for name, md in raw.items():
            if name in done:
                continue
            if any(st not in port_pins for st, _i, _c in md["subs"] if st in raw):
                continue
            loads = dict(md["own_loads"])
            for stype, _inst, conns in md["subs"]:
                pp = port_pins.get(stype)
                for pin, net in conns:
                    if not net or net in CONST:
                        continue
                    if pp is None:
                        add = 1          # unknown submodule: charge one pin
                    else:
                        add = pp.get(pin, 0)   # 0 for output ports
                    loads[net] = loads.get(net, 0) + add
            md["loads"] = loads
            port_pins[name] = {p: loads.get(p, 0) for p in md["inputs"]}
            done.add(name)
            progress = True
        if not progress:
            break
    for md in raw.values():
        md.setdefault("loads", dict(md["own_loads"]))
        md["subs"] = {i: t for t, i, _c in md["subs"]}
    return raw


def resolve_fanout(mods, top, inst_path):
    """Walk a hierarchical instance path; return (fanout, owning module)."""
    parts = inst_path.split("/")
    cur = top
    for p in parts[:-1]:
        if cur not in mods:
            return None, None
        nxt = mods[cur]["subs"].get(p)
        if nxt is None:
            return None, None
        cur = nxt
    leaf = parts[-1]
    if cur not in mods or leaf not in mods[cur]["cells"]:
        hits = [mn for mn, md in mods.items() if leaf in md["cells"]]
        if len(hits) != 1:
            return None, None
        cur = hits[0]
    net = mods[cur]["drv"].get(leaf)
    if net is None:
        return None, cur
    return mods[cur]["loads"].get(net, 0), cur


def parse_path(report_text):
    """Pull (incr_delay, instance, pin, cell_type) rows out of report_checks.

    The instance pattern requires a real identifier: a sibling tool once used
    \\S+ here and matched a `//` comment.
    """
    rows = []
    pat = re.compile(
        r"^\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+[v^]\s+"
        r"([A-Za-z_\\][\w\\/\[\]\.$:]*)/(\w+)\s+\((sky130_fd_sc_hd__\w+)\)",
        re.M)
    for m in pat.finditer(report_text):
        incr, _arr, inst, pin, ctype = m.groups()
        rows.append({"incr": float(incr), "inst": inst,
                     "pin": pin, "cell": ctype})
    m = re.search(r"^\s*(-?\d+\.\d+)\s+slack \((MET|VIOLATED)\)",
                  report_text, re.M)
    slack = float(m.group(1)) if m else None
    met = (m.group(2) == "MET") if m else None
    return rows, slack, met


def classify(report_text, netlist_path, top="bench_top"):
    rows, slack, met = parse_path(report_text)
    if not rows:
        return {"verdict": "UNPARSED",
                "note": "no cell rows matched in the report"}

    # Path delay is the SUM of incremental cell delays. The report's
    # "data arrival time" includes the launch clock edge, which is nonzero
    # for a generated or divided clock and would inflate the denominator.
    path_delay = sum(r["incr"] for r in rows)

    mods = parse_netlist(netlist_path) if netlist_path else {}
    for r in rows:
        fo, owner = resolve_fanout(mods, top, r["inst"]) if mods else (None, None)
        r["fanout"], r["module"] = fo, owner

    unresolved = sum(1 for r in rows if r["fanout"] is None)
    hi = [r for r in rows if (r["fanout"] or 0) >= FANOUT_HI]
    fanout_delay = sum(r["incr"] for r in hi)
    share = fanout_delay / path_delay if path_delay else 0.0

    if met:
        verdict, lever = "NO_ACTION", "path already meets its constraint"
    elif unresolved == len(rows):
        verdict, lever = "UNRESOLVED", "no fanout data; netlist and report disagree"
    elif share >= FANOUT_SHARE_HI:
        verdict, lever = "FANOUT_DOMINATED", "buffering / gate sizing, not RTL"
    elif share <= FANOUT_SHARE_LO:
        verdict, lever = "DEPTH_DOMINATED", "RTL transform through the typed gate"
    else:
        verdict, lever = "MIXED", "buffer first, then re-measure before proposing RTL"

    ranked = sorted(rows, key=lambda r: -r["incr"])
    return {
        "verdict": verdict, "recommended_lever": lever,
        "slack_ns": slack, "met": met,
        "path_delay_ns": round(path_delay, 3),
        "cells_on_path": len(rows),
        "cells_above_fanout_hi": len(hi),
        "fanout_delay_ns": round(fanout_delay, 3),
        "fanout_delay_share": round(share, 4),
        "unresolved_cells": unresolved,
        "top_cells": [{"inst": r["inst"], "cell": r["cell"],
                       "incr_ns": round(r["incr"], 3),
                       "fanout": r["fanout"], "module": r["module"]}
                      for r in ranked[:3]],
        "thresholds": {"fanout_hi": FANOUT_HI,
                       "fanout_share_hi": FANOUT_SHARE_HI,
                       "fanout_share_lo": FANOUT_SHARE_LO},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--netlist", default=None)
    ap.add_argument("--top", default="bench_top")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    res = classify(open(a.report, encoding="utf-8", errors="replace").read(),
                   a.netlist, a.top)
    if a.json:
        print(json.dumps(res, indent=2)); return
    print(f"verdict             : {res['verdict']}")
    print(f"recommended lever   : {res.get('recommended_lever')}")
    print(f"slack               : {res.get('slack_ns')} ns")
    print(f"path delay          : {res.get('path_delay_ns')} ns "
          f"over {res.get('cells_on_path')} cells")
    print(f"fanout-attributable : {res.get('fanout_delay_ns')} ns "
          f"= {res.get('fanout_delay_share')} of path "
          f"({res.get('cells_above_fanout_hi')} cells over fanout "
          f"{res.get('thresholds', {}).get('fanout_hi')})")
    if res.get("unresolved_cells"):
        print(f"unresolved cells    : {res['unresolved_cells']} "
              f"(not found in netlist)")
    for c in res.get("top_cells", []):
        print(f"    {c['incr_ns']:>8} ns  {c['cell']:<30} fanout="
              f"{c['fanout']}  {c['inst']}")


if __name__ == "__main__":
    main()
