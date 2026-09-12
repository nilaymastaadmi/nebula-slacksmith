#!/usr/bin/env python3
"""Two null edits on tv80, to measure the floor before any prediction is made.

Neither changes what the design computes. Both change what the synthesiser
sees, which is the point: `tools/remeasure.py` already documents that ABC's
technology mapping is sensitive to file processing order, so a design's slack
moves for reasons that have nothing to do with an optimisation.

  ctrl_rename   renames the module `tv80_alu` and its single instantiation
  ctrl_reorder  moves that module's text to the end of the file
  ctrl_flip     rewrites one ternary as its complement, `c ? a : b` into
                `!c ? b : a`, on a decode line inside tv80_mcode

MEASURED 2026-09-12, and it changes what these are worth:

  ctrl_reorder  produces a netlist BYTE-IDENTICAL to gold. Yosys elaborates
                modules by hierarchy, not by position in the file, so moving a
                module's text is not a perturbation at all. It measures
                reproducibility and nothing else. Kept, because a control that
                turns out to be a no-op is worth keeping visible.
  ctrl_rename   produces a DIFFERENT netlist, because module names propagate
                into instance names, and identical timing to three decimals.
                A real textual perturbation worth 0.000 ns.
  ctrl_flip     exists because neither of the above changes netlist STRUCTURE,
                and a floor measured only by name changes cannot tell you
                whether the instrument resolves a small structural effect.

Regenerated and checked on every run, so a control that drifts from its
definition fails the run instead of quietly becoming a different experiment.
"""
import io
import os
import re
import sys

D = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(D, "rtl", "tv80.v")
OUT_RENAME = os.path.join(D, "rtl_ctrl_rename", "tv80.v")
OUT_REORDER = os.path.join(D, "rtl_ctrl_reorder", "tv80.v")
OUT_FLIP = os.path.join(D, "rtl_ctrl_flip", "tv80.v")

# One decode line in tv80_mcode. `c ? a : b` and `!c ? b : a` are the same
# function; the second builds a different cone.
FLIP_FROM = "0 : MCycles = (F[Flag_Z]) ? 3'd2 : 3'd3;"
FLIP_TO = "0 : MCycles = (!F[Flag_Z]) ? 3'd3 : 3'd2;"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def module_span(text, name):
    """(start, end) of `module <name> ... endmodule`, end exclusive."""
    m = re.search(r"^\s*module\s+%s\b" % re.escape(name), text, re.M)
    if not m:
        return None
    e = re.search(r"^\s*endmodule\b.*$", text[m.start():], re.M)
    if not e:
        return None
    return m.start(), m.start() + e.end()


def main():
    gold = io.open(GOLD, encoding="utf-8", errors="replace").read()

    # 1. Rename a module and its instantiation. Functionally identical by
    #    construction: a module name is not observable at the interface.
    n = len(re.findall(r"\btv80_alu\b", gold))
    if n < 2:
        print("FATAL: expected the module and at least one instantiation of "
              "tv80_alu, found %d references" % n)
        return 2
    write(OUT_RENAME, re.sub(r"\btv80_alu\b", "tv80_alu_nc", gold))

    # 2. Move that module's text to the end. Verilog does not care where a
    #    module sits in a file; ABC's mapping does.
    span = module_span(gold, "tv80_alu")
    if span is None:
        print("FATAL: could not find the tv80_alu module span")
        return 3
    a, b = span
    moved = gold[:a] + gold[b:] + "\n" + gold[a:b] + "\n"
    if len(moved.split()) != len(gold.split()):
        print("FATAL: reorder changed the token count, %d against %d"
              % (len(moved.split()), len(gold.split())))
        return 4
    write(OUT_REORDER, moved)

    # 3. Structural, and still functionally identical.
    if gold.count(FLIP_FROM) != 1:
        print("FATAL: expected exactly 1 flip site, found %d" % gold.count(FLIP_FROM))
        return 5
    write(OUT_FLIP, gold.replace(FLIP_FROM, FLIP_TO, 1))

    print("ctrl_rename : %d references renamed" % n)
    print("ctrl_reorder: moved %d chars of tv80_alu to the end, token count identical"
          % (b - a))
    print("ctrl_flip   : 1 ternary rewritten as its complement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
