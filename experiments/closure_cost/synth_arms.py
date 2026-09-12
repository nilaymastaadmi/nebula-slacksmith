#!/usr/bin/env python3
"""The five zero-parasitic arms: A0, A0b, A1, A2, A3.

One synthesis per arm, differing only in the abc script. Then WNS on the three
groups, total cells, buffer cells, area and power, all through the same tools
every other number in this project came from.

A0b exists because A1, A2 and A3 all carry _HEAD. Without it their deltas
against A0 include whatever _HEAD does on its own.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, "tools")
import remeasure                      # noqa: E402
import slacksmith                     # noqa: E402

LIB = os.environ["LIBERTY"]
STA = os.environ["STA_BIN"]
YOSYS = os.path.join(os.environ["OSS_CAD_BIN"], "yosys")
WORK = os.environ["SLACKSMITH_WORK"]
SDC = "sdc/bench_top_v3.sdc"
CLOCKS = ["clk_a", "clk_b", "clk_e"]

ARMS = [
    ("A0",  None,                   "plain abc -liberty, the flow every baseline came from"),
    ("A0b", slacksmith._HEAD,       "_HEAD only: no buffering, no sizing"),
    ("A1",  slacksmith.SIZE_ONLY,   "_HEAD + upsize; dnsize"),
    ("A2",  slacksmith.BUF_ONLY,    "_HEAD + buffer -N 16"),
    ("A3",  slacksmith.BOTH,        "_HEAD + buffer -N 16; upsize; dnsize (the loop's lever)"),
]

CELL = re.compile(r"^\s*sky130_fd_sc_hd__", re.M)
BUF = re.compile(r"^\s*sky130_fd_sc_hd__(buf|clkbuf|bufinv|inv)_", re.M)


def counts(netlist):
    txt = open(netlist, encoding="utf-8", errors="replace").read()
    return len(CELL.findall(txt)), len(BUF.findall(txt))


def power_and_area(netlist, workdir, label):
    """Same method as experiments/ppa/power/run.sh: vector-free, default
    activity, one model for every arm. A relative figure, not a signoff
    number."""
    tcl = os.path.join(workdir, "pwr_%s.tcl" % label)
    log = os.path.join(workdir, "pwr_%s.log" % label)
    with open(tcl, "w") as fh:
        fh.write("\n".join([
            "read_liberty %s" % LIB,
            "read_verilog %s" % netlist,
            "link_design bench_top",
            "read_sdc %s" % SDC,
            "report_power",
            "report_design_area",
        ]) + "\n")
    out = subprocess.run([STA, "-no_init", "-no_splash", "-exit", tcl],
                         capture_output=True, text=True).stdout
    open(log, "w", encoding="utf-8").write(out)
    total, area = None, None
    for line in out.splitlines():
        if line.strip().startswith("Total"):
            f = line.split()
            if len(f) >= 5:
                total = float(f[4])
        if "Design area" in line:
            m = re.search(r"Design area\s+([0-9.]+)", line)
            if m:
                area = float(m.group(1))
    return total, area


def main():
    rows = []
    for label, script, why in ARMS:
        wd = os.path.join(WORK, "cc_%s" % label)
        os.makedirs(wd, exist_ok=True)
        print("=" * 72, flush=True)
        print("%s  %s" % (label, why), flush=True)
        net = remeasure.synth_bench_top(
            YOSYS, "rtl", remeasure.BENCH_TOP_FILES, LIB, wd,
            "%s_mapped.v" % label, abc_script=script)
        slacks, _out = remeasure.sta_slack(STA, LIB, net, "bench_top", SDC,
                                           CLOCKS, wd)
        cells, bufs = counts(net)
        pwr, area = power_and_area(net, wd, label)
        rows.append((label, slacks, cells, bufs, area, pwr, net))
        print("  slacks %s  cells %d  buffers %d  area %s  power %s"
              % (slacks, cells, bufs, area, pwr), flush=True)

    print()
    print("| arm | clk_a | clk_b | clk_e | cells | buffers | area (u^2) | power (W) |")
    print("|---|---|---|---|---|---|---|---|")
    for label, slacks, cells, bufs, area, pwr, _net in rows:
        print("| %s | %.3f | %.3f | %.3f | %d | %d | %s | %s |"
              % (label, slacks["clk_a"], slacks["clk_b"], slacks["clk_e"],
                 cells, bufs,
                 ("%.0f" % area) if area else "n/a",
                 ("%.4g" % pwr) if pwr else "n/a"))
    print()
    for label, _s, _c, _b, _a, _p, net in rows:
        print("netlist %s: %s" % (label, net))
    return 0


if __name__ == "__main__":
    sys.exit(main())
