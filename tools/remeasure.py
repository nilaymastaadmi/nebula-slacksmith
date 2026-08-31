#!/usr/bin/env python3
"""
remeasure.py -- swap a module into bench_top, synthesize, and diff real
timing against a baseline, against the project's own frozen SDC.

The third and final piece of mechanical busywork this project's three real
transforms all needed by hand: copy bench_top.v, sed the one instance line
to the transformed module, run the same nine-file Yosys synth against
sky130hd_tt.lib, then the same OpenSTA read_liberty/read_verilog/
link_design/read_sdc/report_checks sequence, then read the slack numbers
off by eye to build the before/after table that goes in NOTES.md. Done by
hand three times (experiments/fsm_reencode, mux_priority_to_parallel,
pipeline_cut_domain_a) with real risk of a stale liberty path or a copy-
paste slack number entering the report unnoticed. This does not decide
which path groups matter for a given transform -- that stays a judgment
call, passed explicitly via --clock.

This does NOT decide whether a timing result is good news -- see
experiments/pipeline_cut_domain_a/NOTES.md, where the honest answer was
"proven correct, measurably worse." It only makes sure the number reported
is the number the tools actually produced.

Usage:
    python3 remeasure.py \\
        --rtl-dir rtl \\
        --top bench_top \\
        --swap-instance u_domain_a --swap-module domain_a_clamped_pipelined \\
        --replace domain_a.v:domain_a_clamped_pipelined.v \\
        --sdc sdc/bench_top.sdc \\
        --liberty ~/sta_work/sky130hd_tt.lib \\
        --sta-bin ~/tools/OpenSTA/build/sta \\
        --clock clk_a --clock clk_a_div2 \\
        --workdir ~/remeasure_domain_a \\
        --baseline-cache ~/remeasure_baseline_bench_top

--baseline-cache reuses a previous baseline synthesis+STA run rather than
repeating it -- the baseline is identical across every transform applied to
the same clock/path groups, and re-synthesizing all nine bench_top files
each time is the slowest step in the whole tool for no new information.

--workdir and --baseline-cache MUST be under a real filesystem path (e.g.
under $HOME on this project's WSL setup), never /tmp: confirmed directly
that /tmp does not reliably persist between separate invocations here (the
underlying VM appears to reclaim it), which surfaced mid-development as a
"file not found" on a directory a prior run had just written successfully.

Requires yosys and the project's own OpenSTA build; assumes the same nine
source files (async_fifo.v, bench_top.v, clkdiv.v, domain_a.v..domain_e.v,
sync2ff.v) this project's bench_top has used throughout -- pass --extra-file
to add any new file a transform introduces (as every _fv/_pipelined/_parallel
variant so far has needed).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys


# v2 file set (2026-08-31 benchmark growth). Order is load-bearing: ABC's
# technology mapping is sensitive to file processing order, established by
# measurement when this tool was first validated.
BENCH_TOP_FILES = [
    "aes/aes_core.v", "aes/aes_encipher_block.v", "aes/aes_decipher_block.v",
    "aes/aes_key_mem.v", "aes/aes_sbox.v", "aes/aes_inv_sbox.v",
    "rv32i_core.v", "rv32_load.v", "aes_load.v",
    "async_fifo.v", "bench_top.v", "clkdiv.v",
    "domain_a.v", "domain_b.v", "domain_c.v", "domain_d.v", "domain_e.v",
    "sync2ff.v",
]

# Cell families excluded from technology mapping, matching standard sky130
# flow practice (OpenLane excludes the same families by default).
#
# Measured, not assumed: on the v2 benchmark ABC selected
# sky130_fd_sc_hd__lpflow_isobufsrc_1 on a high-fanout net and OpenSTA
# reported a 12.391 ns delay through that ONE cell, 38% of a 33 ns critical
# path. Excluding these families dropped WNS from -27.37 to -22.54 (4.83 ns)
# with no RTL change whatsoever. lpflow cells are low-power isolation and
# power-gating cells; they are not intended as general logic and ABC was
# picking them on area cost. Leaving them in means reporting a synthesis
# artifact as a timing result.
#
# The list is derived from the liberty at run time rather than hardcoded, so
# it stays correct if the library changes.
DONT_USE_PATTERNS = ("lpflow", "probe")


def dont_use_flags(liberty_path):
    """Return ABC -dont_use flags for every excluded cell present in the liberty."""
    try:
        with open(liberty_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return ""
    cells = set(re.findall(r"cell \((sky130_fd_sc_hd__[a-z0-9_]+)\)", text))
    excluded = sorted(c for c in cells if any(p in c for p in DONT_USE_PATTERNS))
    return " ".join(f"-dont_use {c}" for c in excluded)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def synth_bench_top(yosys_bin, rtl_dir, files, liberty, workdir, mapped_name, extra_yosys_top="bench_top"):
    os.makedirs(workdir, exist_ok=True)
    paths = " ".join(os.path.join(rtl_dir, f) for f in files)
    mapped_path = os.path.join(workdir, mapped_name)
    script = (
        f"read_verilog {paths}; "
        f"hierarchy -check -top {extra_yosys_top}; "
        f"synth -top {extra_yosys_top}; "
        f"dfflibmap -liberty {liberty}; "
        f"abc -liberty {liberty} {dont_use_flags(liberty)}; "
        # opt_clean -purge strips named-but-unused wires. Required, not
        # cosmetic: Yosys names Verilog function temporaries like
        # \rev32$func$/abs/path/file.v:101$4454.i , and OpenSTA's Verilog
        # reader rejects that escaped identifier with a syntax error. Found
        # 2026-08-31 when the one LLM proposal using a function produced a
        # netlist that synthesized cleanly and could not be timed at all
        # (1,386 such names). -purge removes all of them and the netlist reads.
        f"opt_clean -purge; "
        f"write_verilog -noattr {mapped_path}"
    )
    proc = run([yosys_bin, "-p", script])
    if proc.returncode != 0 or not os.path.exists(mapped_path):
        print("yosys synthesis failed:", file=sys.stderr)
        print(proc.stdout[-3000:], file=sys.stderr)
        print(proc.stderr[-3000:], file=sys.stderr)
        sys.exit(1)
    return mapped_path


def sta_slack(sta_bin, liberty, mapped_path, top, sdc, clocks, workdir):
    tcl_path = os.path.join(workdir, "query.tcl")
    lines = [
        f"read_liberty {liberty}",
        f"read_verilog {mapped_path}",
        f"link_design {top}",
        f"read_sdc {sdc}",
    ]
    for clk in clocks:
        lines.append(f"puts \"---CLOCK:{clk}---\"")
        lines.append(f"report_checks -path_delay max -to [get_clocks {clk}] -group_path_count 1 -digits 3")
    with open(tcl_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    proc = run([sta_bin, "-no_init", "-no_splash", "-exit", tcl_path])
    out = proc.stdout + proc.stderr

    results = {}
    for clk in clocks:
        # OpenSTA ends a path report with "<number>   slack (MET)" or
        # "<number>   slack (VIOLATED)". Match BOTH. The original version of
        # this parser matched only MET, so any variant that broke timing
        # reported UNPARSED instead of the negative number -- audit finding
        # F6, 2026-08-31: the measurement tool was blind to the one outcome
        # that matters most. Fixed and validated with a deliberate
        # negative-control run (tightened scratch SDC, both columns report
        # negative slack, no UNPARSED).
        block_m = re.search(rf"---CLOCK:{re.escape(clk)}---(.*?)(?=---CLOCK:|\Z)", out, re.S)
        slack = None
        if block_m:
            nums = re.findall(r"([\-0-9.]+)\s+slack \((?:MET|VIOLATED)\)", block_m.group(1))
            if nums:
                slack = float(nums[-1])
        results[clk] = slack
    return results, out


def main():
    ap = argparse.ArgumentParser(
        description="Swap a module into bench_top and diff real timing against a baseline (see module docstring).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--rtl-dir", required=True)
    ap.add_argument("--top", default="bench_top")
    ap.add_argument("--swap-instance", required=True, help="instance name in bench_top.v to retarget, e.g. u_domain_a")
    ap.add_argument("--swap-module", required=True, help="module name to instantiate instead")
    ap.add_argument("--replace", action="append", default=[], metavar="OLD:NEW", dest="replacements",
                     help="substitute NEW for OLD in the file list, IN PLACE (e.g. domain_a.v:domain_a_clamped_pipelined.v) -- "
                          "REQUIRED whenever --swap-module lives in a new file rather than editing one already in "
                          "bench_top's file set. In-place, not filter-then-append: ABC's technology mapping is "
                          "sensitive to file processing order (confirmed directly -- an early version of this tool "
                          "appended the new file at the end instead, and reproduced a known-true result to within "
                          "0.03ns but not exactly, closed only by fixing the ordering to match how every hand-built "
                          "synthesis in this project has always listed files). Repeatable for transforms touching "
                          "more than one file.")
    ap.add_argument("--sdc", required=True)
    ap.add_argument("--liberty", required=True)
    ap.add_argument("--sta-bin", required=True)
    ap.add_argument("--yosys-bin", default="yosys")
    ap.add_argument("--clock", action="append", required=True, dest="clocks", help="clock/path-group name to report; repeatable")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--baseline-cache", default=None, help="directory to cache/reuse the unmodified bench_top synthesis")
    args = ap.parse_args()

    liberty = os.path.expanduser(args.liberty)
    sta_bin = os.path.expanduser(args.sta_bin)
    os.makedirs(args.workdir, exist_ok=True)

    # --- baseline ---
    baseline_dir = args.baseline_cache or os.path.join(args.workdir, "baseline")
    baseline_mapped = os.path.join(baseline_dir, "baseline_mapped.v")
    if not (args.baseline_cache and os.path.exists(baseline_mapped)):
        print(f"synthesizing baseline into {baseline_dir} ...")
        synth_bench_top(args.yosys_bin, args.rtl_dir, BENCH_TOP_FILES, liberty, baseline_dir, "baseline_mapped.v")
    else:
        print(f"reusing cached baseline: {baseline_mapped}")
    base_slack, _ = sta_slack(sta_bin, liberty, baseline_mapped, args.top, args.sdc, args.clocks, args.workdir)

    # --- variant ---
    variant_dir = os.path.join(args.workdir, "variant")
    variant_top_src = os.path.join(variant_dir, f"{args.top}_variant.v")
    os.makedirs(variant_dir, exist_ok=True)
    with open(os.path.join(args.rtl_dir, f"{args.top}.v")) as f:
        text = f.read()
    # The module-name token must be a real Verilog identifier, not "any
    # non-space run". The original \S+ also matched the "//" of a comment, so
    # a header comment mentioning the instance name counted as a second
    # instantiation and the tool refused to run (found 2026-08-31 by hitting
    # it: bench_top.v's own v2 header documents "u_rv32_a (clk_a): ..."). A
    # tool that a documentation comment can break is a tool that will break
    # at the worst moment.
    pattern = re.compile(
        rf"^(\s*)[A-Za-z_][A-Za-z0-9_]*\s+{re.escape(args.swap_instance)}\s*\(", re.M)
    new_text, n = pattern.subn(rf"\g<1>{args.swap_module} {args.swap_instance} (", text)
    if n != 1:
        print(f"error: expected exactly 1 match for instance {args.swap_instance!r} in {args.top}.v, found {n}", file=sys.stderr)
        sys.exit(1)
    with open(variant_top_src, "w") as f:
        f.write(new_text)

    replacements = {}
    for r in args.replacements:
        if ":" not in r:
            print(f"error: --replace must be OLD:NEW, got {r!r}", file=sys.stderr)
            sys.exit(1)
        old, new = r.split(":", 1)
        replacements[old] = new

    # walk BENCH_TOP_FILES in its natural order, substituting IN PLACE --
    # not filtering then appending -- so the variant build's file processing
    # order matches the baseline's (and every hand-built synthesis in this
    # project) except for the specific file(s) actually being replaced.
    variant_paths = []
    for f in BENCH_TOP_FILES:
        if f == f"{args.top}.v":
            variant_paths.append(variant_top_src)
        elif f in replacements:
            variant_paths.append(os.path.join(args.rtl_dir, replacements[f]))
        else:
            variant_paths.append(os.path.join(args.rtl_dir, f))

    print(f"synthesizing variant ({args.swap_module} in place of {args.swap_instance}) ...")
    paths = " ".join(variant_paths)
    mapped_path = os.path.join(variant_dir, "variant_mapped.v")
    script = (
        f"read_verilog {paths}; "
        f"hierarchy -check -top {args.top}; "
        f"synth -top {args.top}; "
        f"dfflibmap -liberty {liberty}; "
        f"abc -liberty {liberty} {dont_use_flags(liberty)}; "
        # opt_clean -purge strips named-but-unused wires. Required, not
        # cosmetic: Yosys names Verilog function temporaries like
        # \rev32$func$/abs/path/file.v:101$4454.i , and OpenSTA's Verilog
        # reader rejects that escaped identifier with a syntax error. Found
        # 2026-08-31 when the one LLM proposal using a function produced a
        # netlist that synthesized cleanly and could not be timed at all
        # (1,386 such names). -purge removes all of them and the netlist reads.
        f"opt_clean -purge; "
        f"write_verilog -noattr {mapped_path}"
    )
    proc = run([args.yosys_bin, "-p", script])
    if proc.returncode != 0 or not os.path.exists(mapped_path):
        print("yosys synthesis failed:", file=sys.stderr)
        print(proc.stdout[-3000:], file=sys.stderr)
        print(proc.stderr[-3000:], file=sys.stderr)
        sys.exit(1)
    var_slack, _ = sta_slack(sta_bin, liberty, mapped_path, args.top, args.sdc, args.clocks, args.workdir)

    print(f"\n{'clock':<16} {'baseline':>10} {'variant':>10} {'delta':>10}")
    for clk in args.clocks:
        b, v = base_slack.get(clk), var_slack.get(clk)
        if b is None or v is None:
            print(f"{clk:<16} {'UNPARSED':>10} {'UNPARSED':>10} {'--':>10}  (inspect raw STA output)")
            continue
        d = v - b
        print(f"{clk:<16} {b:>10.3f} {v:>10.3f} {d:>+10.3f}")


if __name__ == "__main__":
    main()
