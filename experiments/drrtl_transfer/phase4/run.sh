set -u
# Phase 4 of experiments/drrtl_transfer/PREREGISTRATION.md, predictions 12 to 14.
# Dr. RTL skill #8 (replicate a high-fanout condition wire per consumer) on
# aes, communication and datapath: gold, plain, (* keep *). Each synthesized
# as A (no lever) and B (buffer-only, the isolated fanout lever from phase 3),
# timed at the scored run's own period, re-classified, and gated against gold.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
Y=$HOME/tools/oss-cad-suite/bin/yosys
STA=$HOME/tools/OpenSTA/build/sta
LIB=$HOME/sta_work/sky130hd_tt.lib
P4=experiments/drrtl_transfer/phase4
W=$HOME/drrtl_p4; rm -rf $W; mkdir -p $W $P4/results
DU=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure; print(remeasure.dont_use_flags('$LIB'))")
[ $(echo $DU | wc -w) -ge 2 ] || { echo "FATAL: empty dont_use"; exit 3; }
BUF_ONLY='+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put;buffer,-N,16'

period_of () { python3 - "$1" <<'PY'
import csv, sys
for r in csv.DictReader(open("experiments/drrtl_transfer/results/summary.tsv"), delimiter="\t"):
    if r["design"] == sys.argv[1]: print(r["period_ns"]); break
PY
}
synth () {  # $1 src $2 ext $3 top $4 out $5 abc-script-or-empty
  local rv="read_verilog"; [ "$2" = "sv" ] && rv="read_verilog -sv"
  local abc="abc -liberty $LIB $DU"; [ -n "$5" ] && abc="$abc -script $5"
  $Y -p "$rv $1; hierarchy -check -top $3; synth -top $3; dfflibmap -liberty $LIB; $abc; opt_clean -purge; write_verilog -noattr $4; stat" > $4.log 2>&1
  [ -s "$4" ] || { echo "  synth FAILED: $1"; return 1; }
  sed -i -E 's/^(\s*(input|output|inout|wire|reg))\s+signed\s+/\1 /' $4
  grep -qE '^\s*always' $4 && { echo "  FLOW_FAIL: behavioral constructs in $4"; return 2; }
  return 0
}
sta_r2r () {  # $1 netlist $2 top $3 clk $4 period $5 out
  cat > $5.tcl <<EOF
read_liberty $LIB
read_verilog $1
link_design $2
create_clock -name clk -period $4 [get_ports $3]
puts "---CLOCK:clk---"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -digits 3
EOF
  $STA -no_init -no_splash -exit $5.tcl > $5 2>&1
  grep -qE 'syntax error' $5 && { echo READ_FAIL; return; }
  grep -E "(-?[0-9.]+)[[:space:]]+slack \((MET|VIOLATED)\)" $5 | tail -1 | awk '{print $1}'
}
classify_row () {  # $1 report $2 netlist $3 top -> "verdict share top_fanout top_incr"
  python3 tools/classify_path.py --report $1 --netlist $2 --top $3 --json 2>/dev/null | python3 -c "
import json,sys
try: c=json.load(sys.stdin); t=(c.get('top_cells') or [{}])[0]
except Exception: print('UNPARSED ? ? ?'); sys.exit()
print(c.get('verdict'), c.get('fanout_delay_share'), t.get('fanout'), t.get('incr_ns'))"
}

printf "design\tvariant\tabc\tcells\tslack\tverdict\tshare\ttop_fanout\ttop_incr\n" > $P4/results/summary.tsv
for spec in "aes:key_expansion_128aes:clk:sv" "communication:sync_serial_communication_tx_rx:clk:v" "datapath:datapath:clk:v"; do
  IFS=: read -r d top clk ext <<< "$spec"
  per=$(period_of $d)
  echo "=== $d ($top) period=$per ==="
  for v in gold skill8_plain skill8_keep; do
    src=$P4/${d}_$v.$ext
    for ab in A B; do
      sc=""; [ $ab = B ] && sc="$BUF_ONLY"
      net=$W/${d}_${v}_$ab.v
      synth $src $ext $top $net "$sc" || { printf "%s\t%s\t%s\tFLOW_FAIL\n" $d $v $ab >> $P4/results/summary.tsv; continue; }
      cells=$(grep -cE "sky130_fd_sc_hd__" $net)
      sl=$(sta_r2r $net $top $clk $per $W/${d}_${v}_$ab.rpt)
      row=$(classify_row $W/${d}_${v}_$ab.rpt $net $top)
      printf "%s\t%s\t%s\t%s\t%s\t%s\n" $d $v $ab $cells "$sl" "$(echo $row | tr ' ' '\t')" >> $P4/results/summary.tsv
      echo "  $v/$ab cells=$cells slack=$sl  $row"
      cp $W/${d}_${v}_$ab.rpt $P4/results/ 2>/dev/null
    done
  done
  echo "  --- gate (EQY, k=0) ---"
  for v in skill8_plain skill8_keep; do
    cat > $W/${d}_$v.json <<EOF
{"id": "${d}_$v", "transform_type": "drrtl_skill8_condition_replication", "declared_latency_delta_k": 0,
 "target_module": "$top", "target_file": "$P4/${d}_gold.$ext", "variant_file": "$P4/${d}_$v.$ext",
 "rationale": "Dr. RTL skill 8 as written: replicate the high-fanout condition wire per consumer"}
EOF
    python3 tools/gate_proposal.py --proposal $W/${d}_$v.json --rtl $P4/${d}_gold.$ext --module $top \
      --clk $clk --rst rst --workdir $W/gate_${d}_$v --repo . --timeout 600 > $P4/results/gate_${d}_$v.txt 2>&1
    grep -E '"G[1-4]"|counterexample|depth_exhausted' $P4/results/gate_${d}_$v.txt | tr -d '\n' | sed "s/^/  $v: /"; echo
  done
done
echo; cat $P4/results/summary.tsv
