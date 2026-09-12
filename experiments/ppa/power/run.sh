#!/bin/bash
# Before/after POWER across the physical flow, to sit beside the before/after
# timing and area this project already reports.
#
# Registered expectation, written before the run: power goes UP. repair_design
# added 960 buffers and 20.2% area on this pair, and buffers cost internal and
# switching power. A result showing power FLAT or DOWN would mean either the
# estimate is insensitive to 960 cells or the netlists are not the pair we
# think they are, and either way it would be a finding rather than a headline.
#
# This is a vector-free estimate at default switching activity, which is a
# relative figure for comparing two netlists under one model. It is not a
# signoff power number and is not presented as one.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../../tools/env.sh"
O=experiments/ppa/power; mkdir -p $O
W=$SLACKSMITH_WORK/power; rm -rf $W; mkdir -p $W

measure () {  # $1 label  $2 netlist
  cat > $W/$1.tcl <<TCL
read_liberty $LIBERTY
read_verilog $2
link_design bench_top
read_sdc sdc/bench_top_v2.sdc
puts "=====> $1"
report_power
report_design_area
TCL
  $STA_BIN -no_init -no_splash -exit $W/$1.tcl 2>&1 | tee $W/$1.log \
    | grep -E "^Total|^Design area|=====>"
}

echo "### before repair_design"
measure before "$HOME/or_repair/prerepair.v"
echo
echo "### after repair_design"
measure after "$HOME/or_repair/repaired.v"
cp $W/before.log $W/after.log $O/ 2>/dev/null

# Emit the derived figures, so the report quotes a file rather than an
# arithmetic step taken in someone's head. tools/check_report_numbers.py
# flagged 139.0 and 47.1 as unsupported when they were converted by hand from
# the 1.39e-01 the tool prints; that is the checker doing its job.
python3 - "$W/before.log" "$W/after.log" <<'PY' | tee $O/summary.md
import re, sys
def total(path):
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.strip().startswith("Total"):
            f = line.split()
            return float(f[1]), float(f[2]), float(f[3]), float(f[4])
    return None
b = total(sys.argv[1]); a = total(sys.argv[2])
print("| component | before (W) | after (W) |")
print("|---|---|---|")
for name, i in (("internal", 0), ("switching", 1), ("leakage", 2), ("total", 3)):
    print("| %s | %.3e | %.3e |" % (name, b[i], a[i]))
print()
print("total power before: **%.1f mW**" % (b[3] * 1000.0))
print("total power after : **%.1f mW**" % (a[3] * 1000.0))
print("delta             : **%+.1f%%**" % (100.0 * (a[3] - b[3]) / b[3]))
print()
print("Vector-free at default switching activity: a relative comparison of two")
print("netlists under one model, not a signoff number.")
PY
