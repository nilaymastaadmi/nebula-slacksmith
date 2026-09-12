#!/bin/bash
# One physical arm: floorplan, global placement, then whatever repair command
# the caller names, then time and area. Everything else is byte-identical to
# experiments/openroad_repair/run.sh, which is the flow every published
# post-repair number in this project came from.
#
#   or_arm.sh <label> <repair tcl> <netlist> <sdc>
#
# The repair tcl is the ONLY thing that varies across A4, A5 and A6.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
LABEL=$1; REPAIR=$2; NET=$3; SDC=$4
OR=$OPENROAD_BIN; P=$ORFS_PLATFORM; LIB=$LIBERTY
W=$SLACKSMITH_WORK/cc_$LABEL; rm -rf $W; mkdir -p $W

[ -s "$NET" ] || { echo "FATAL: netlist $NET missing"; exit 2; }

cat > $W/flow.tcl <<TCL
read_lef $P/lef/sky130_fd_sc_hd.tlef
read_lef $P/lef/sky130_fd_sc_hd_merged.lef
read_liberty $LIB
read_verilog $NET
link_design bench_top
read_sdc $SDC

puts "=====> FLOORPLAN"
initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2.0 -site unithd
source $P/make_tracks.tcl
place_pins -hor_layers met3 -ver_layers met2
source $P/setRC.tcl

puts "=====> GLOBAL PLACEMENT"
global_placement -density 0.60
estimate_parasitics -placement

puts "=====> TIMING BEFORE"
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:\$c---"
  report_checks -path_delay max -to [get_clocks \$c] -group_count 1 -digits 3
}
puts "design_area BEFORE:"
report_design_area
write_verilog $W/prerepair.v

puts "=====> REPAIR (${LABEL}): ${REPAIR}"
${REPAIR}
puts "=====> DETAILED PLACEMENT"
detailed_placement
estimate_parasitics -placement

puts "=====> TIMING AFTER"
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:\$c---"
  report_checks -path_delay max -to [get_clocks \$c] -group_count 1 -digits 3
}
puts "design_area AFTER:"
report_design_area
write_verilog $W/repaired.v
exit
TCL

echo "running OpenROAD arm $LABEL (repair: $REPAIR)"
$OR -no_init -exit $W/flow.tcl > $W/flow.log 2>&1
echo "openroad exit: $?"
grep -E "^---CLOCK|slack \(|=====>|Design area|Error|FATAL" $W/flow.log | tail -40
echo "netlist: $W/repaired.v"
