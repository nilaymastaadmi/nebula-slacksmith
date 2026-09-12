#!/bin/bash
# Zero-parasitic timing for the composed RTL and its three parts, all under ONE
# SDC and one flow, plus the null control that has to pass before any delta
# here is reportable.
#
# Registered in PREREGISTRATION.md (R32 to R40) before anything was synthesized.
#
# The three parts are re-measured here rather than quoted from their own
# experiments, because A4's published +4.925 is an SDC v2 number and O1/O2 are
# v3 numbers. Adding those three as published would be exactly the cross-regime
# arithmetic REPORT section 1 retracted once already.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
O=experiments/composed_rtl/results; mkdir -p "$O"

bash experiments/composed_rtl/compose.sh || exit 3

run () {  # $1 label  $2 path to the aes_key_mem variant, relative to rtl/
  echo "=============== $1 ==============="
  python3 tools/remeasure.py \
    --rtl-dir rtl --top bench_top \
    --swap-instance u_aes_b --swap-module aes_load \
    --replace "aes/aes_key_mem.v:$2" \
    --sdc sdc/bench_top_v3.sdc --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
    --clock clk_a --clock clk_b --clock clk_e \
    --baseline-cache "$SLACKSMITH_WORK/cr_baseline" \
    --workdir "$SLACKSMITH_WORK/cr_$1" 2>&1
}

{
# The null control runs FIRST and swaps the gold file for itself. If this is
# not 0.000 on every group, nothing below it is a measurement of a transform.
run null_gold_vs_gold  ../rtl/aes/aes_key_mem.v
run A4_onehot_read     ../experiments/llm_proposer_aes/proposals/aes_key_mem_A4.v
run O2_fsm_reencode    ../experiments/missing_classes/aes_key_mem_O2.v
run O1_fanout_split    ../experiments/cli_backend/results/run1/O1_aes_key_mem.v
run composed_A4_O2_O1  ../experiments/composed_rtl/aes_key_mem_composed.v
} | tee "$O/timing_zero_parasitic.txt"

echo
echo "=== cell counts (R39) ==="
for d in cr_baseline cr_composed_A4_O2_O1; do
  n=$SLACKSMITH_WORK/$d/baseline_mapped.v
  [ -f "$n" ] || n=$SLACKSMITH_WORK/$d/variant/variant_mapped.v
  [ -f "$n" ] && echo "$d: $(grep -cE '^\s*sky130_fd_sc_hd__' "$n") cells   $n"
done | tee "$O/cell_counts.txt"
