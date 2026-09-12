#!/bin/bash
# R47 and R48: does the physical flow resolve 0.237 ns at all?
#
# Amendment 1. Section 5 has a null control for synthesis and STA (swap a module
# for itself, 0.000 on every group). The physical flow has never had one, and
# R38's -0.237 ns is 4% of the margin it sits in.
#
#   R47  gold through the identical flow twice -> expect 0.000
#   R48  A5, the registered do-nothing transform, through the same flow
#        -> expect it to move post-repair clk_b by less than 0.237 ns
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/composed_rtl/results; mkdir -p $R
SDC=sdc/bench_top_v3.sdc
GOLD_NET=$SLACKSMITH_WORK/cr_baseline/baseline_mapped.v

echo "########## R47: gold through the flow a SECOND time ##########"
OR_REPAIR_WORK=$SLACKSMITH_WORK/cr_or_gold2 \
  bash experiments/openroad_repair/run.sh "$GOLD_NET" "$SDC" 2>&1 | tee $R/repair_gold_run2.txt

echo "########## A5 zero-parasitic, to build its netlist ##########"
python3 tools/remeasure.py \
  --rtl-dir rtl --top bench_top \
  --swap-instance u_aes_b --swap-module aes_load \
  --replace "aes/aes_key_mem.v:../experiments/llm_proposer_aes/proposals/aes_key_mem_A5.v" \
  --sdc "$SDC" --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
  --clock clk_a --clock clk_b --clock clk_e \
  --baseline-cache "$SLACKSMITH_WORK/cr_baseline" \
  --workdir "$SLACKSMITH_WORK/cr_A5" 2>&1 | tee $R/timing_A5.txt

echo "########## R48: A5 through repair_design ##########"
OR_REPAIR_WORK=$SLACKSMITH_WORK/cr_or_a5 \
  bash experiments/openroad_repair/run.sh \
  "$SLACKSMITH_WORK/cr_A5/variant/variant_mapped.v" "$SDC" 2>&1 | tee $R/repair_A5.txt
