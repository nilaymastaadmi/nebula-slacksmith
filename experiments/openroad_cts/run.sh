set -u
# Post-CTS and post-route timing.
#
# WHY. Every timing number this project has published, including the
# repair_design result in experiments/openroad_repair/, uses IDEAL CLOCKS: no
# clock tree, zero insertion delay, zero skew. That is the standard context
# for repair_design and it is not a signoff number. A clock tree costs real
# insertion delay and introduces real skew, and on a design with five
# asynchronous domains AND five in-RTL generated clocks there is no guarantee
# the closure survives it.
#
# This measures three points on one flow, everything else held identical:
#   1. post-placement, ideal clocks   (what experiments/openroad_repair reports)
#   2. post-CTS, PROPAGATED clocks    (real insertion delay and skew)
#   3. post-global-route parasitics   (routed RC instead of placement estimates)
#
# set_propagated_clock is the line that makes point 2 mean anything. Without
# it OpenROAD keeps using ideal clocks even after building the tree, and the
# numbers would look identical to point 1 for the wrong reason.
#
# The CTS buffer list is the plain clkbuf family. The lpflow clkbufkapwr cells
# are deliberately excluded, which matches both this project's own dont_use
# policy (docs/measurement-methodology.md finding 1) and the sky130hd
# platform's own DONT_USE_CELLS.
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
OR=$OPENROAD_BIN
P=$ORFS_PLATFORM
LIB=$LIBERTY
NET=${1:-$HOME/bufexp/A.v}
SDC=${2:-sdc/bench_top_v2.sdc}
W=$HOME/or_cts; mkdir -p $W

[ -s "$NET" ] || { echo "FATAL: netlist $NET missing"; exit 2; }

CTSBUF="sky130_fd_sc_hd__clkbuf_1 sky130_fd_sc_hd__clkbuf_2 sky130_fd_sc_hd__clkbuf_4 sky130_fd_sc_hd__clkbuf_8 sky130_fd_sc_hd__clkbuf_16"

cat > $W/flow.tcl <<TCL
read_lef $P/lef/sky130_fd_sc_hd.tlef
read_lef $P/lef/sky130_fd_sc_hd_merged.lef
read_liberty $LIB
read_verilog $NET
link_design bench_top
read_sdc $SDC

initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2.0 -site unithd
source $P/make_tracks.tcl
place_pins -hor_layers met3 -ver_layers met2
source $P/setRC.tcl

global_placement -density 0.60
estimate_parasitics -placement
repair_design
detailed_placement

proc report_all {tag} {
  puts "=====> TIMING \$tag"
  foreach c {clk_a clk_b clk_e} {
    puts "---CLOCK:\$c---"
    report_checks -path_delay max -to [get_clocks \$c] -group_count 1 -digits 3
  }
  puts "=====> AREA \$tag"
  report_design_area
}

estimate_parasitics -placement
report_all "1_POST_PLACE_IDEAL_CLOCKS"

puts "=====> CTS"
clock_tree_synthesis -buf_list {$CTSBUF} -root_buf sky130_fd_sc_hd__clkbuf_16
set_propagated_clock [all_clocks]
detailed_placement
estimate_parasitics -placement
report_all "2_POST_CTS_PROPAGATED"
puts "=====> CLOCK SKEW after CTS"
report_clock_skew

puts "=====> GLOBAL ROUTE"
set_routing_layers -signal met1-met5 -clock met3-met5
global_route
estimate_parasitics -global_routing
report_all "3_POST_GLOBAL_ROUTE"
puts "=====> CLOCK SKEW after route"
report_clock_skew

write_verilog $W/cts_routed.v
exit
TCL

echo "running OpenROAD CTS flow (netlist $NET, sdc $SDC)"
$OR -no_init -exit $W/flow.tcl > $W/flow.log 2>&1
echo "openroad exit: $?"
echo "=== results ==="
grep -E "^=====>|slack \(|Design area|^Clock |Skew|ERROR|Error" $W/flow.log | head -70
