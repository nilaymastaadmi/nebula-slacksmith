set -u
# OpenROAD repair_design on the v2 benchmark.
#
# experiments/buffering_control/ showed that a mapping-level ABC buffering pass
# closes both violated groups. That pass has no placement and no parasitics, so
# it is a control, not a flow. This runs the real thing: floorplan, global
# placement, placement-based parasitics, then repair_design, and times the
# design before and after with everything else held identical.
#
# The liberty is deliberately OUR sky130hd_tt.lib, not the one shipped with the
# OpenROAD platform (their md5 differ), so these numbers stay comparable with
# every other measurement in this project.
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
OR=$OPENROAD_BIN
P=$ORFS_PLATFORM
LIB=$LIBERTY
NET=${1:-$HOME/bufexp/A.v}          # default: the unbuffered mapped netlist
SDC=${2:-sdc/bench_top_v2.sdc}
W=$HOME/or_repair; mkdir -p $W

[ -s "$NET" ] || { echo "FATAL: netlist $NET missing"; exit 2; }
[ -s "$LIB" ] || { echo "FATAL: liberty missing"; exit 2; }

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

puts "=====> TIMING BEFORE repair_design"
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:\$c---"
  report_checks -path_delay max -to [get_clocks \$c] -group_count 1 -digits 3
}
puts "design_area BEFORE:"
report_design_area

# Write the pre-repair netlist as well. Both sides then carry OpenROAD's own
# flat naming, so a name-based equivalence check has something to match on.
# Comparing OpenROAD's output against the hierarchical Yosys netlist does not
# work: equiv_make found only 86 equivalence points in a 55K-cell design.
write_verilog $W/prerepair.v

puts "=====> REPAIR_DESIGN"
repair_design
puts "=====> DETAILED PLACEMENT"
detailed_placement
estimate_parasitics -placement

puts "=====> TIMING AFTER repair_design"
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:\$c---"
  report_checks -path_delay max -to [get_clocks \$c] -group_count 1 -digits 3
}
puts "design_area AFTER:"
report_design_area
write_verilog $W/repaired.v
exit
TCL

echo "running OpenROAD (netlist: $NET)"
$OR -no_init -exit $W/flow.tcl > $W/flow.log 2>&1
echo "openroad exit: $?"
echo "=== slacks ==="
grep -E "^---CLOCK|slack \(|=====>|Design area|FATAL|Error" $W/flow.log | tail -40
