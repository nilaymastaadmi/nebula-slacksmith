#!/bin/bash
# Eight arms, one netlist, one SDC. See PREREGISTRATION.md (R64 to R70).
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
O=experiments/closure_cost/results; mkdir -p "$O"
SDC=sdc/bench_top_v3.sdc

echo "############ zero-parasitic arms: A0, A0b, A1, A2, A3 ############"
python3 -u experiments/closure_cost/synth_arms.py 2>&1 | tee "$O/zero_parasitic.txt"

GOLD=$SLACKSMITH_WORK/cc_A0/A0_mapped.v
[ -s "$GOLD" ] || { echo "FATAL: A0 netlist missing, cannot run the physical arms"; exit 3; }

echo
echo "############ physical arms ############"
bash experiments/closure_cost/or_arm.sh A4 "repair_timing -setup"                 "$GOLD" "$SDC" 2>&1 | tee "$O/A4.txt"
bash experiments/closure_cost/or_arm.sh A5 "repair_design"                        "$GOLD" "$SDC" 2>&1 | tee "$O/A5.txt"
bash experiments/closure_cost/or_arm.sh A6 "repair_design
repair_timing -setup"                                                             "$GOLD" "$SDC" 2>&1 | tee "$O/A6.txt"

echo
echo "############ power on each physical arm's output ############"
W=$SLACKSMITH_WORK/cc_power; rm -rf $W; mkdir -p $W
for a in A4 A5 A6; do
  N=$SLACKSMITH_WORK/cc_$a/repaired.v
  [ -s "$N" ] || { echo "$a: no repaired netlist"; continue; }
  cat > $W/$a.tcl <<TCL
read_liberty $LIBERTY
read_verilog $N
link_design bench_top
read_sdc $SDC
puts "=====> $a"
report_power
report_design_area
TCL
  $STA_BIN -no_init -no_splash -exit $W/$a.tcl 2>&1 | tee $W/$a.log \
    | grep -E "^Total|^Design area|=====>"
  echo "$a buffers: $(grep -cE '^\s*sky130_fd_sc_hd__(buf|clkbuf|bufinv|inv)_' $N)  cells: $(grep -cE '^\s*sky130_fd_sc_hd__' $N)"
done | tee "$O/physical_power.txt"

echo
echo "############ void check: does A5 reproduce the published run? ############"
echo "--- this run (A5) ---"
grep -A8 "TIMING AFTER" "$O/A5.txt" | grep -E "slack \(|Design area"
echo "--- composed_rtl/results/repair_gold.txt ---"
grep -A8 "TIMING AFTER" experiments/composed_rtl/results/repair_gold.txt | grep -E "slack \(|Design area"
