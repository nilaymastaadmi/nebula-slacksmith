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


DECL_RE = re.compile(
    r"^\s*(?:input|output|inout|wire|reg)\s+(?:wire\s+|reg\s+)?"
    r"(?:\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]\s*)?(.+?);", re.M)
CONST_RE = re.compile(r"^(\d+)'[sS]?[hbdoHBDO][0-9a-fA-FxXzZ_?]+$")
PART_RE = re.compile(r"^(.+?)\[(\d+):(\d+)\]$")
BIT_RE = re.compile(r"^(.+?)\[(\d+)\]$")


def _norm(net):
    """One spelling per net: no whitespace, no leading escape backslash.
    Yosys writes escaped names as `\\foo.bar [2]` in one place and the cell
    pin as `\\foo.bar[2]` in another."""
    return re.sub(r"\s+", "", net).lstrip("\\")


def _conns(text):
    return [(p, _norm(n)) for p, n in CONN_RE.findall(text)]


def _split_top(text):
    """Split a concatenation body on commas at brace depth 0."""
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def _bits(text, widths):
    """Expand a port connection into bit-level net names, MSB first.

    Handles `{a, b[3:1], 2'h0, c}` concatenations, part-selects, bit-selects
    and whole-bus names (width from the parent's declaration). Constant
    bits become None and are never charged.

    This is the 2026-09-03 fix. Before it, a connection was charged only if
    its text equalled a net name exactly, so `.sboxw(tmp_sboxw)` (a 32-bit
    bus) and `.imem_data({imem_data[2], imem_data[2], ...})` (one bit fanned
    into 20 port bits) were charged nothing. On this project's own benchmark
    that read a 387-load net as fanout 1 and a 59-load net as fanout 0, and
    classified both paths DEPTH_DOMINATED at share 0.000.
    """
    t = _norm(text)
    if not t:
        return []
    if t.startswith("{"):
        inner = t[1:t.rfind("}")] if "}" in t else t[1:]
        out = []
        for part in _split_top(inner):
            out.extend(_bits(part, widths))
        return out
    m = CONST_RE.match(t)
    if m:
        return [None] * int(m.group(1))
    m = PART_RE.match(t)
    if m:
        name, hi, lo = m.group(1), int(m.group(2)), int(m.group(3))
        step = -1 if hi >= lo else 1
        return [f"{name}[{i}]" for i in range(hi, lo + step, step)]
    if BIT_RE.match(t):
        return [t]
    w = widths.get(t)
    if w:
        msb, lsb = w
        step = -1 if msb >= lsb else 1
        return [f"{t}[{i}]" for i in range(msb, lsb + step, step)]
    return [t]


def _port_bits(port, width):
    if width:
        msb, lsb = width
        step = -1 if msb >= lsb else 1
        return [f"{port}[{i}]" for i in range(msb, lsb + step, step)]
    return [port]


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
                tok = _norm(tok)
                if tok:
                    inputs.add(tok)
        # Declared widths, needed to expand whole-bus connections.
        widths = {}
        for msb, lsb, names in DECL_RE.findall(body):
            for tok in names.split(","):
                tok = _norm(tok)
                if tok:
                    widths[tok] = (int(msb), int(lsb)) if msb else None
        cells, drv, own_loads = {}, {}, {}
        for ctype, inst, conns in CELL_RE.findall(body):
            inst = inst.lstrip("\\")
            cells[inst] = ctype
            for pin, net in _conns(conns):
                if not net or net in CONST or CONST_RE.match(net):
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
        raw[name] = {"inputs": inputs, "widths": widths, "cells": cells,
                     "drv": drv, "own_loads": own_loads, "subs": subs}

    # Leaf-first resolution. port_pins[module]["pins"][port_bit] is the
    # number of leaf input pins that port bit ultimately drives inside that
    # module; ["widths"] carries the port widths so a parent can expand a
    # whole-bus or concatenated connection bit by bit.
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
                    if not net:
                        continue
                    nbits = _bits(net, md["widths"])
                    if pp is None:
                        # unknown submodule: charge one pin per bit
                        for nb in nbits:
                            if nb is not None:
                                loads[nb] = loads.get(nb, 0) + 1
                        continue
                    pbits = _port_bits(pin, pp["widths"].get(pin))
                    if len(pbits) == 1 and len(nbits) > 1 and pin not in pp["widths"]:
                        # output port connected to a bus: nothing to charge
                        continue
                    for nb, pb in zip(nbits, pbits):
                        if nb is None:
                            continue
                        loads[nb] = loads.get(nb, 0) + pp["pins"].get(pb, 0)
            md["loads"] = loads
            pins = {}
            for p in md["inputs"]:
                for pb in _port_bits(p, md["widths"].get(p)):
                    pins[pb] = loads.get(pb, 0)
            port_pins[name] = {"pins": pins,
                               "widths": {p: md["widths"].get(p) for p in md["inputs"]}}
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
    # With `report_checks -fields {fanout}` each cell row carries OpenSTA's
    # own leaf-pin fanout as a leading integer column. That count is taken
    # through hierarchy by the tool that timed the path, so when it is
    # present it is the fanout used (see classify). Without the field the
    # optional group is empty and the netlist is the only source.
    pat = re.compile(
        r"^\s*(?:(\d+)\s+)?(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+[v^]\s+"
        r"([A-Za-z_\\][\w\\/\[\]\.$:]*)/(\w+)\s+\((sky130_fd_sc_hd__\w+)\)",
        re.M)
    for m in pat.finditer(report_text):
        rfo, incr, _arr, inst, pin, ctype = m.groups()
        rows.append({"incr": float(incr), "inst": inst,
                     "pin": pin, "cell": ctype,
                     "report_fanout": int(rfo) if rfo is not None else None})
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
    have_report = any(r["report_fanout"] is not None for r in rows)
    disagree = 0
    for r in rows:
        fo, owner = resolve_fanout(mods, top, r["inst"]) if mods else (None, None)
        r["netlist_fanout"], r["module"] = fo, owner
        if have_report:
            # Driver pins carry the count; the CLK and D rows have none and
            # contribute no delay of their own.
            r["fanout"] = r["report_fanout"] if r["report_fanout"] is not None else 0
            if fo is not None and r["report_fanout"] is not None and fo != r["report_fanout"]:
                disagree += 1
        else:
            r["fanout"] = fo
    fanout_source = "report" if have_report else ("netlist" if mods else "none")

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
        "fanout_source": fanout_source,
        "fanout_disagreements": disagree if have_report and mods else None,
        "top_cells": [{"inst": r["inst"], "cell": r["cell"],
                       "incr_ns": round(r["incr"], 3),
                       "fanout": r["fanout"], "module": r["module"],
                       "netlist_fanout": r["netlist_fanout"]}
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
