#!/bin/bash
# Reproduces experiments/sdc_integrity/NOTES.md. Exploratory demonstration:
# how much slack can SDC statements alone manufacture with zero design change?
# Netlist is frozen (flat arm E). Only the constraints vary.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
STA=$STA_BIN
LIB=$LIBERTY
W=$SLACKSMITH_WORK/sdc_trap; mkdir -p $W

# The frozen netlist (flat arm E) is committed gzipped rather than left in the
# author's home directory, because the claim this script makes is about a
# BYTE-IDENTICAL netlist and nobody can check that against a file they do not
# have. 387 KB compressed, sha256 8068609219...
NET=$W/flat_E_mapped.v
[ -f "$NET" ] || zcat experiments/sdc_integrity/flat_E_mapped.v.gz > "$NET"

# The endpoint of the residual clk_e path, from the committed report.
EP=$(grep -m1 "^Endpoint:" experiments/flatten_control/results/E_clk_e.rpt | awk '{print $2}')
SP=$(grep -m1 "^Startpoint:" experiments/flatten_control/results/E_clk_e.rpt | awk '{print $2}')
echo "residual clk_e path: $SP -> $EP"

run () {  # $1 label  $2 extra sdc lines
  cat > $W/$1.tcl <<EOF
read_liberty $LIB
read_verilog $NET
link_design bench_top
read_sdc sdc/bench_top_v3.sdc
$2
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:\$c---"
  report_checks -path_delay max -to [get_clocks \$c] -group_path_count 1 -digits 3
}
exit
EOF
  $STA -no_init -no_splash -exit $W/$1.tcl > $W/$1.rpt 2>&1
  printf "%-22s " "$1"
  grep -E "slack \((MET|VIOLATED)\)" $W/$1.rpt | awk '{printf "%9s ", $1}'
  echo
}

echo
printf "%-22s %9s %9s %9s\n" "constraint variant" "clk_a" "clk_b" "clk_e"
run baseline_honest ""
run mcp_on_endpoint "set_multicycle_path 2 -setup -to [get_pins $EP/D]"
run false_path_endpoint "set_false_path -to [get_pins $EP/D]"
run mcp_whole_clk_e "set_multicycle_path 2 -setup -from [get_clocks clk_e] -to [get_clocks clk_e]"
echo
echo "cell count is identical in every row: $(grep -cE '^\s*sky130_fd_sc_hd__' $NET) cells, one netlist, zero RTL change"
