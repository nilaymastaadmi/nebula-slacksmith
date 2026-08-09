#!/usr/bin/env python3
"""
Interface classifier -- the front end of the two-branch obligation generator.

Decides whether a module's interface is RIGID or ELASTIC, and therefore which
proof obligation is sound for a latency-changing transform on it:

    RIGID    -> k-padded miter        (see experiments/toy_miter)
    ELASTIC  -> stream equivalence    (see experiments/vr_miter)

Getting this wrong is not a missed optimisation, it is a wrong answer: pointing
a k-padded miter at an elastic interface refutes correct transforms, which
vr_miter demonstrates in 0 seconds.

Two passes, and the second is the one that matters:

  1. LEXICAL   -- find ports whose names look like a handshake. Handles the
                  common spellings and AXI-style prefixes. Cheap, and wrong on
                  its own: a port called `ready` that nothing reads is not
                  back-pressure.
  2. STRUCTURAL-- confirm the candidate actually reaches sequential state. A
                  real back-pressure input must be able to *prevent a register
                  from updating*, so it has to fan out into some flop's D or
                  enable cone. If it does not, the interface is rigid no matter
                  what the port is called.

A module is ELASTIC only if a candidate survives both passes.

Usage:  classify.py <top> <file.v> [file.v ...]
"""

import json
import re
import subprocess
import sys
from collections import deque

# ---------------------------------------------------------------- lexical

# Ordered most-specific first. AXI-style prefixes (awready, wvalid, ...) fall
# out of the substring match.
BACKPRESSURE_PAT = re.compile(r"(^|_)(ready|rdy|stall|hold|busy|nack|almost_full|afull|full)($|_)|ready$|rdy$", re.I)
VALIDITY_PAT     = re.compile(r"(^|_)(valid|vld|val|dv|strobe|stb|ack)($|_)|valid$|vld$", re.I)

# Pins that hold or update state. Reaching any of these means the signal can
# influence whether a register keeps its value.
FF_INPUT_PINS = {"D", "EN", "E", "ARST", "SRST", "R", "S", "CLR", "PRE", "ALOAD", "AD"}
FF_TYPE_PAT   = re.compile(r"^\$(_)?(a|s)?dffe?|^\$(_)?dlatch|^\$(_)?sr|^\$adlatch|^\$aldff", re.I)


def run_yosys(top, files):
    script = "".join(f"read_verilog -sv {f}; " for f in files)
    script += f"prep -top {top}; write_json /dev/stdout"
    out = subprocess.run(
        ["yosys", "-q", "-p", script],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit(f"yosys failed for {top}:\n{out.stderr[:800]}")
    # write_json to stdout is preceded by nothing in -q mode, but be defensive
    txt = out.stdout
    start = txt.index("{")
    return json.loads(txt[start:])


def build_graph(mod):
    """bit -> cells that consume it, and bit -> cell that drives it."""
    consumers, drivers = {}, {}
    for cname, cell in mod.get("cells", {}).items():
        dirs = cell.get("port_directions", {})
        for pin, bits in cell.get("connections", {}).items():
            # Fall back to a conservative heuristic when directions are absent.
            direction = dirs.get(pin) or ("output" if pin in ("Y", "Q") else "input")
            for b in bits:
                if not isinstance(b, int):
                    continue          # constant 0/1/x/z
                if direction == "output":
                    drivers[b] = (cname, cell["type"], pin)
                else:
                    consumers.setdefault(b, []).append((cname, cell["type"], pin))
    return consumers, drivers


def reaches_state(start_bits, consumers, drivers):
    """Forward BFS from start_bits. Returns the first (cell, type, pin) at which
    the signal touches sequential state, or None."""
    seen, q = set(), deque(b for b in start_bits if isinstance(b, int))
    seen.update(q)
    while q:
        bit = q.popleft()
        for cname, ctype, pin in consumers.get(bit, []):
            if FF_TYPE_PAT.match(ctype) and pin in FF_INPUT_PINS:
                return (cname, ctype, pin)
            # combinational: keep walking through this cell's outputs
            cell = None
            for n, c in _CELLS.items():
                if n == cname:
                    cell = c
                    break
            if cell is None:
                continue
            dirs = cell.get("port_directions", {})
            for opin, obits in cell.get("connections", {}).items():
                d = dirs.get(opin) or ("output" if opin in ("Y", "Q") else "input")
                if d != "output":
                    continue
                for ob in obits:
                    if isinstance(ob, int) and ob not in seen:
                        seen.add(ob)
                        q.append(ob)
    return None


def classify(top, files):
    design = run_yosys(top, files)
    mod = design["modules"].get(top) or list(design["modules"].values())[0]

    global _CELLS
    _CELLS = mod.get("cells", {})
    consumers, drivers = build_graph(mod)

    ports = mod.get("ports", {})
    findings = {"backpressure": [], "validity": [], "rejected": []}

    for pname, p in ports.items():
        direction, bits = p.get("direction"), p.get("bits", [])

        if direction == "input" and BACKPRESSURE_PAT.search(pname):
            hit = reaches_state(bits, consumers, drivers)
            if hit:
                findings["backpressure"].append((pname, hit))
            else:
                findings["rejected"].append(
                    (pname, "name suggests back-pressure, but it never reaches "
                            "sequential state -- cannot stall this module")
                )

        if direction == "output" and VALIDITY_PAT.search(pname):
            findings["validity"].append((pname, None))

    elastic = bool(findings["backpressure"])
    return top, elastic, findings


def report(top, elastic, f):
    verdict = "ELASTIC" if elastic else "RIGID"
    oblig = ("stream equivalence  (no fixed cycle offset exists)" if elastic
             else "k-padded miter      (opt.O[t+k] == ref.O[t])")
    print(f"\n{'='*66}\n  {top}\n{'='*66}")
    print(f"  verdict     : {verdict}")
    print(f"  obligation  : {oblig}")
    if f["backpressure"]:
        print("  back-pressure confirmed structurally:")
        for name, (cell, ctype, pin) in f["backpressure"]:
            print(f"      {name:<14} reaches {ctype} pin {pin}  ({cell})")
    if f["validity"]:
        print(f"  validity outputs: {', '.join(n for n, _ in f['validity'])}")
    if f["rejected"]:
        print("  candidates REJECTED by the structural pass:")
        for name, why in f["rejected"]:
            print(f"      {name:<14} {why}")
    if not elastic and not f["rejected"]:
        print("  no back-pressure input found; consumer cannot stall this module")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    t, e, f = classify(sys.argv[1], sys.argv[2:])
    report(t, e, f)
    sys.exit(0 if e is not None else 1)
