set -u
# Arms of experiments/max_fanout/PREREGISTRATION.md. The OpenROAD flow is
# experiments/openroad_repair/run.sh unchanged; only the netlist and the SDC
# vary. Nothing here edits sdc/bench_top_v3.sdc.
#
#   usage: bash experiments/max_fanout/run.sh
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
RES=experiments/max_fanout/results; mkdir -p $RES
STA=$HOME/tools/OpenSTA/build/sta
LIB=$HOME/sta_work/sky130hd_tt.lib

# Prove the generated SDCs differ from v3 only by the appended block.
for n in 8 16 32; do
  diff <(head -191 sdc/bench_top_v3_mf$n.sdc) sdc/bench_top_v3.sdc > $RES/diff_mf$n.txt 2>&1 \
    && echo "mf$n: first 191 lines identical to v3" \
    || { echo "FATAL: mf$n differs from v3 above the appended block"; exit 3; }
done

# P41: set_max_fanout is a design rule, not a timing constraint, so the
# zero-parasitic slacks must not move. Same netlist, v3 vs mf16.
echo "=== P41 control: OpenSTA on arm E under v3 and under mf16"
for sdc in bench_top_v3 bench_top_v3_mf16; do
  cat > $RES/ctl_$sdc.tcl <<EOF
read_liberty $LIB
read_verilog $HOME/flatexp/E/mapped.v
link_design bench_top
read_sdc sdc/$sdc.sdc
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:\$c---"
  report_checks -path_delay max -to [get_clocks \$c] -group_path_count 1 -digits 3
}
exit
EOF
  $STA -no_init -no_splash -exit $RES/ctl_$sdc.tcl > $RES/ctl_$sdc.rpt 2>&1
  echo -n "  $sdc: "
  grep -E "slack \((MET|VIOLATED)\)" $RES/ctl_$sdc.rpt | awk '{printf "%s ", $1}'
  echo
done

# The four repair arms.
run_arm () {  # $1 label  $2 netlist  $3 sdc
  echo "=============== arm $1 (netlist $2, sdc $3)"
  bash experiments/openroad_repair/run.sh "$2" "$3"
  cp $HOME/or_repair/flow.log $RES/$1.flow.log
  gzip -9 -c $HOME/or_repair/repaired.v > $RES/$1.repaired.v.gz 2>/dev/null
}
run_arm MF16-E $HOME/flatexp/E/mapped.v sdc/bench_top_v3_mf16.sdc
run_arm MF8-E  $HOME/flatexp/E/mapped.v sdc/bench_top_v3_mf8.sdc
run_arm MF32-E $HOME/flatexp/E/mapped.v sdc/bench_top_v3_mf32.sdc
run_arm MF16-C $HOME/flatexp/C/mapped.v sdc/bench_top_v3_mf16.sdc

echo
echo "=== before/after per arm ==="
python3 experiments/max_fanout/score.py 2>&1 | tail -40
