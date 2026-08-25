#!/usr/bin/env python3
"""
make_fv_wrapper.py -- generate a formal-verification tap wrapper.

Every hand-built miter in this project (experiments/fsm_reencode/,
experiments/mux_priority_to_parallel/, experiments/pipeline_cut_domain_a/)
needed the same mechanical step: Yosys's -formal frontend cannot read a
submodule instance's internal signal by hierarchical reference (confirmed
directly in experiments/fsm_reencode/NOTES.md -- an early attempt at
`u_opt.state_r` was silently treated as an undriven free wire, which made
the first BMC run fail against garbage rather than the real design). The
fix every time has been an exact copy of the target module, renamed, with
one or more internal signals tapped out to new output ports via sed. That
was done by hand three times, via sed one-liners rebuilt from scratch each
time, which is exactly the kind of repeated, error-prone busywork this tool
exists to remove -- not to change what gets built, only to stop re-deriving
the same five lines of sed under time pressure each time a new transform
needs one.

This does NOT decide what to tap or why -- that judgment call (which signal,
what obligation it serves) stays with whoever is proposing the transform.
It only performs the mechanical rewrite once that decision is made, the same
way every time, so the wrapper file is never the place a mistake enters.

Usage:
    python3 make_fv_wrapper.py \\
        --src domain_b.v --module domain_b \\
        --tap dbg_state:4:state_r \\
        --out domain_b_fv.v

    python3 make_fv_wrapper.py \\
        --src domain_a_clamped_comb.v --module domain_a_clamped_comb \\
        --tap dbg_clamped:16:clamped_w --tap dbg_valid:1:prod_valid_r \\
        --out domain_a_clamped_comb_fv.v

--tap NAME:WIDTH:EXPR may be repeated. WIDTH=1 emits a scalar port
(`output wire NAME`); WIDTH>1 emits a vector (`output wire [W-1:0] NAME`).
EXPR may be a plain signal name or any Verilog expression (including a
function call, as domain_b_onehot_fv.v's decode_state(state_r) tap needed).

New module name defaults to "<original>_fv"; override with --new-name.
"""

import argparse
import re
import sys


def parse_tap(spec: str):
    parts = spec.split(":", 2)
    if len(parts) != 3:
        raise ValueError(
            f"--tap must be NAME:WIDTH:EXPR, got {spec!r}"
        )
    name, width_s, expr = parts
    try:
        width = int(width_s)
    except ValueError:
        raise ValueError(f"--tap width must be an integer, got {width_s!r} in {spec!r}")
    if width < 1:
        raise ValueError(f"--tap width must be >= 1, got {width} in {spec!r}")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError(f"--tap port name must be a valid identifier, got {name!r}")
    if not expr.strip():
        raise ValueError(f"--tap expr must be non-empty in {spec!r}")
    return name, width, expr.strip()


def build_wrapper(src_text: str, module: str, new_name: str, taps: list) -> str:
    lines = src_text.splitlines(keepends=True)

    # --- find and rename the module declaration ---
    decl_re = re.compile(r"^module\s+" + re.escape(module) + r"\s*\(")
    decl_idx = None
    for i, line in enumerate(lines):
        if decl_re.match(line):
            decl_idx = i
            break
    if decl_idx is None:
        raise ValueError(
            f"could not find 'module {module} (' as a line start in the source; "
            "this tool expects the same single-line module-declaration style "
            "used throughout rtl/ (module NAME (  on its own line)"
        )

    port_lines = []
    for name, width, _expr in taps:
        if width == 1:
            port_lines.append(f"    output wire {name},\n")
        else:
            port_lines.append(f"    output wire [{width-1}:0] {name},\n")

    lines[decl_idx] = f"module {new_name} (\n" + "".join(port_lines)
    # the original line had its own trailing content after '(' (usually
    # nothing but a newline, matching this repo's style) -- reconstructing
    # decl_idx as two logical pieces (new header + original ports) keeps
    # every subsequent port declaration line untouched.

    # --- find endmodule and insert assigns just before it ---
    end_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "endmodule":
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("could not find a line containing only 'endmodule'")

    assign_lines = [f"    assign {name} = {expr};\n" for name, _w, expr in taps]
    lines[end_idx:end_idx] = ["\n"] + assign_lines

    return "".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Generate a formal-verification tap wrapper (see module docstring).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--src", required=True, help="source .v file")
    ap.add_argument("--module", required=True, help="module name to wrap (must match a 'module NAME (' line)")
    ap.add_argument("--tap", action="append", required=True, metavar="NAME:WIDTH:EXPR",
                     help="internal signal to tap; repeatable")
    ap.add_argument("--out", required=True, help="output .v file path")
    ap.add_argument("--new-name", default=None, help="new module name (default: <module>_fv)")
    args = ap.parse_args()

    try:
        taps = [parse_tap(t) for t in args.tap]
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    new_name = args.new_name or f"{args.module}_fv"

    with open(args.src, "r", encoding="utf-8") as f:
        src_text = f.read()

    try:
        out_text = build_wrapper(src_text, args.module, new_name, taps)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out_text)

    tap_summary = ", ".join(f"{n}[{w}]<={e}" for n, w, e in taps)
    print(f"wrote {args.out}: module {args.module} -> {new_name}, taps: {tap_summary}")


if __name__ == "__main__":
    main()
