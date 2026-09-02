set -u
# Phase 2 of experiments/drrtl_transfer/PREREGISTRATION.md, predictions 6 and 7.
# Dr. RTL high-confidence skill #7 ("duplicate register / signal copies and
# split fanout cones") applied as written to cpu_fsm, whose program counter
# PC[2] drives 1,131 loads and burns 32.954 ns in one cell (96% of its path).
#
# Three RTL sources: gold, plain duplication, duplication with (* keep *).
# Each synthesized twice: A (unbuffered) and B (the physical lever). All six
# timed at the SAME period the scored run derived for cpu_fsm (51.849 ns,
# 0.9x its requirement), reg-to-reg only, identical to phase 1. Then:
#   - max fanout on any net inside mini_cpu, and on the PC / PC_dup nets
#   - the formal gate (EQY, k=0) on gold vs each variant, because a transform
#     that is not proven equivalent has no timing result to report.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
Y=$HOME/tools/oss-cad-suite/bin/yosys
STA=$HOME/tools/OpenSTA/build/sta
LIB=$HOME/sta_work/sky130hd_tt.lib
P2=experiments/drrtl_transfer/phase2
W=$HOME/drrtl_p2; rm -rf $W; mkdir -p $W $P2/results
PERIOD=51.849
TOP=mini_cpu
DU=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure; print(remeasure.dont_use_flags('$LIB'))")
[ $(echo $DU | wc -w) -ge 2 ] || { echo "FATAL: empty dont_use"; exit 3; }
BUF='+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put;buffer,-N,16;upsize;dnsize'

synth () {  # $1 src $2 out $3 abc-script-or-empty
  local abc="abc -liberty $LIB $DU"; [ -n "$3" ] && abc="$abc -script $3"
  $Y -p "read_verilog $1; hierarchy -check -top $TOP; synth -top $TOP; dfflibmap -liberty $LIB; $abc; opt_clean -purge; write_verilog -noattr $2; stat" > $2.log 2>&1
  [ -s "$2" ] || { echo "synth FAILED: $1"; exit 1; }
}
sta () {  # $1 netlist $2 out
  cat > $2.tcl <<EOF
read_liberty $LIB
read_verilog $1
link_design $TOP
create_clock -name clk -period $PERIOD [get_ports clk]
puts "---CLOCK:clk---"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -digits 3
EOF
  $STA -no_init -no_splash -exit $2.tcl > $2 2>&1
  grep -E "(-?[0-9.]+)[[:space:]]+slack \((MET|VIOLATED)\)" $2 | tail -1 | awk '{print $1}'
}
fanout () {  # $1 netlist -> "max_any max_PC max_PCdup"
  python3 - $1 <<'PY'
import sys; sys.path.insert(0, "tools")
from classify_path import parse_netlist
m = parse_netlist(sys.argv[1]); loads = m["mini_cpu"]["loads"]
mx = max(loads.values()) if loads else 0
pc = max([v for k, v in loads.items() if k.startswith("PC[") or k == "PC"] or [0])
pd = max([v for k, v in loads.items() if k.startswith("PC_dup")] or [0])
print(mx, pc, pd)
PY
}

printf "variant\tabc\tcells\tslack\tmax_fanout_any\tmax_fanout_PC\tmax_fanout_PC_dup\n" > $P2/results/summary.tsv
for v in gold skill7_plain skill7_keep; do
  src=$P2/cpu_fsm_$v.v
  for ab in A B; do
    sc=""; [ $ab = B ] && sc="$BUF"
    net=$W/${v}_$ab.v
    synth $src $net "$sc"
    cells=$(grep -cE "sky130_fd_sc_hd__" $net)
    sl=$(sta $net $W/${v}_$ab.rpt)
    fo=$(fanout $net)
    printf "%s\t%s\t%s\t%s\t%s\n" $v $ab $cells "$sl" "$(echo $fo | tr ' ' '\t')" >> $P2/results/summary.tsv
    echo "$v/$ab cells=$cells slack=$sl fanout(any,PC,PC_dup)=$fo"
    cp $W/${v}_$ab.rpt $P2/results/${v}_$ab.rpt
  done
done

echo; echo "=== formal gate, gold vs each variant (EQY, k=0) ==="
for v in skill7_plain skill7_keep; do
  cat > $W/$v.json <<EOF
{"id": "cpu_fsm_$v", "transform_type": "drrtl_skill7_register_duplication",
 "declared_latency_delta_k": 0, "target_module": "$TOP",
 "target_file": "experiments/drrtl_transfer/phase2/cpu_fsm_gold.v",
 "variant_file": "experiments/drrtl_transfer/phase2/cpu_fsm_$v.v",
 "rationale": "Dr. RTL skill 7 as written: duplicate PC, route the fetch mux to the copy"}
EOF
  python3 tools/gate_proposal.py --proposal $W/$v.json --rtl $P2/cpu_fsm_gold.v \
    --module $TOP --clk clk --rst rst --workdir $W/gate_$v --repo . --timeout 600 2>&1 \
    | grep -E '"id"|"G[1-4]"|counterexample|depth_exhausted' | tee $P2/results/gate_$v.txt
done
echo; cat $P2/results/summary.tsv
