#!/bin/bash
# Does the liberty file SETUP.md tells you to use give the same numbers as the
# one the committed results were measured with?
#
# The two differ by 9 bytes (default_fanout_load 1.0 vs 1.0000000000). That
# looks cosmetic. "Looks cosmetic" is not a measurement, and every timing
# number in REPORT.md comes from one of these files, so it gets checked.
#
#   usage: bash tools/liberty_equivalence.sh
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

A="$LIBERTY"
B="$ORFS_PLATFORM/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
W="$SLACKSMITH_WORK/lib_equiv"; mkdir -p "$W"

[ -f "$B" ] || { echo "ORFS liberty absent at $B; nothing to compare"; exit 0; }

NET="$W/flat_E_mapped.v"
[ -f "$NET" ] || zcat experiments/sdc_integrity/flat_E_mapped.v.gz > "$NET"

echo "A (LIBERTY)      $A  $(stat -c%s "$A") bytes"
echo "B (ORFS)         $B  $(stat -c%s "$B") bytes"
echo "byte difference: $(( $(stat -c%s "$B") - $(stat -c%s "$A") ))"
echo "differing lines: $(diff "$A" "$B" | grep -c '^[<>]')"
diff "$A" "$B" | head -6
echo

run () {  # $1 label  $2 liberty
  cat > "$W/$1.tcl" <<EOF
read_liberty $2
read_verilog $NET
link_design bench_top
read_sdc sdc/bench_top_v3.sdc
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:\$c---"
  report_checks -path_delay max -to [get_clocks \$c] -group_path_count 1 -digits 6
}
exit
EOF
  "$STA_BIN" -no_init -no_splash -exit "$W/$1.tcl" > "$W/$1.rpt" 2>&1
  printf "%-10s " "$1"
  grep -E "slack \((MET|VIOLATED)\)" "$W/$1.rpt" | awk '{printf "%14s ", $1}'
  echo
}

printf "%-10s %14s %14s %14s\n" "liberty" "clk_a" "clk_b" "clk_e"
run A "$A"
run B "$B"

SA=$(grep -E "slack \((MET|VIOLATED)\)" "$W/A.rpt" | awk '{print $1}' | tr '\n' ' ')
SB=$(grep -E "slack \((MET|VIOLATED)\)" "$W/B.rpt" | awk '{print $1}' | tr '\n' ' ')
echo
if [ "$SA" = "$SB" ]; then
  echo "IDENTICAL at 6 decimal places: the ORFS copy is a safe substitute"
else
  echo "DIFFERENT: A=[$SA] B=[$SB]  SETUP.md must say which one the report used"
fi
