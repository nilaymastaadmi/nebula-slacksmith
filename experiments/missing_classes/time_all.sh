#!/bin/bash
# Time all three batch-3 variants across ALL reported groups.
#
# REPORT §5's reporting rule: a transform's effect is the delta in the group it
# touches, and movement elsewhere is reported separately, never folded in. The
# first C3 measurement asked for clk_b alone, which is exactly the folding that
# rule exists to prevent. This measures clk_a, clk_b and clk_e for each.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
run () {  # $1 label  $2 variant path relative to rtl/
  echo "=============== $1 ==============="
  python3 tools/remeasure.py \
    --rtl-dir rtl --top bench_top \
    --swap-instance u_aes_b --swap-module aes_load \
    --replace "aes/aes_key_mem.v:$2" \
    --sdc sdc/bench_top_v3.sdc --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
    --clock clk_a --clock clk_b --clock clk_e \
    --baseline-cache "$SLACKSMITH_WORK/ta_baseline" \
    --workdir "$SLACKSMITH_WORK/ta_$1" 2>&1
}
O=experiments/missing_classes/results; mkdir -p $O
{
run cliO1_fanout_split ../experiments/cli_backend/results/run1/O1_aes_key_mem.v
run O1_retiming        ../experiments/missing_classes/aes_key_mem_O1.v
run O2_fsm             ../experiments/missing_classes/aes_key_mem_O2.v
} | tee $O/timing_all_groups.txt
