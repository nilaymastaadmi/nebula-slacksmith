#!/usr/bin/env python3
"""What the generator actually writes, per obligation, counted from the files.

Why this exists. REPORT §1.1 refuses to state a speed-up ratio because no
engineer was ever timed writing an obligation by hand. That refusal is honest
and it is also a non-answer to something the organisers asked for in writing.

The fix is not to invent a denominator. A web search on 2026-09-12 found no
published per-obligation authoring time, and a number borrowed from a
verification-effort survey would be a category error dressed as evidence.

So this counts the numerator instead: **how much machinery each obligation is,
and how many decisions it encodes**, measured from the committed artifacts. A
reader can then judge the manual cost themselves, against their own experience,
which is a better answer than a ratio we cannot support.

    python3 experiments/speedup_step/obligation_cost.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# One committed obligation per branch, named here rather than globbed, so the
# table cannot silently change shape when a new experiment lands.
OBLIGATIONS = [
    ("1  combinational (EQY)", "experiments/cec_check/ctrl.eqy"),
    ("2  k-padded miter", "experiments/pipeline_cut_domain_a/miter_pipeline_domain_a.sv"),
    ("2  k-padded, runner", "experiments/pipeline_cut_domain_a/miter.sby"),
    ("4  mapped-state miter", "experiments/fsm_reencode/miter_mapped.sv"),
    ("4  mapped-state, runner", "experiments/fsm_reencode/miter.sby"),
]

SIGNAL = re.compile(r"\b(?:input|output|wire|reg|logic)\b[^;]*?\b([A-Za-z_][A-Za-z0-9_]*)\s*[;,)]")
ASSERT = re.compile(r"\bassert\b|\bassume\b|\bcover\b", re.I)
PORTMAP = re.compile(r"\.\s*[A-Za-z_][A-Za-z0-9_]*\s*\(")


def measure(path):
    full = os.path.join(HERE, path)
    if not os.path.exists(full):
        return None
    text = io.open(full, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    code = [l for l in lines
            if l.strip() and not l.strip().startswith(("#", "//", "*", "/*"))]
    return {
        "lines": len(lines),
        "code": len(code),
        "signals": len(set(SIGNAL.findall(text))),
        "portmaps": len(PORTMAP.findall(text)),
        "properties": len(ASSERT.findall(text)),
    }


def main():
    rows = []
    for label, path in OBLIGATIONS:
        m = measure(path)
        if m is None:
            print("missing: %s" % path, file=sys.stderr)
            continue
        rows.append((label, path, m))

    print("| branch | artifact | lines | code lines | distinct signals | port connections | properties |")
    print("|---|---|---|---|---|---|---|")
    tot = {"lines": 0, "code": 0, "portmaps": 0, "properties": 0}
    for label, path, m in rows:
        print("| %s | `%s` | %d | %d | %d | %d | %d |"
              % (label, os.path.basename(path), m["lines"], m["code"],
                 m["signals"], m["portmaps"], m["properties"]))
        for k in tot:
            tot[k] += m[k]
    print("| **total** | %d artifacts | **%d** | **%d** | | **%d** | **%d** |"
          % (len(rows), tot["lines"], tot["code"], tot["portmaps"], tot["properties"]))
    print()
    print("Every line above is generated from the declared transform type by "
          "tools/gate_proposal.py. No engineer was timed writing an equivalent "
          "by hand, so this project states what the automation produces and "
          "claims no ratio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
