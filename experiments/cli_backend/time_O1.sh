#!/bin/bash
# C3: does the unattended proposal improve clk_b?
# Registered prediction: no, because the duplicated control nets are pure
# aliases and opt_clean merges them.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
O=experiments/cli_backend/results; mkdir -p $O
python3 tools/remeasure.py \
  --rtl-dir rtl --top bench_top \
  --swap-instance u_aes_b --swap-module aes_load \
  --replace "aes/aes_key_mem.v:../experiments/cli_backend/results/run1/O1_aes_key_mem.v" \
  --sdc sdc/bench_top_v3.sdc --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
  --clock clk_b \
  --workdir "$SLACKSMITH_WORK/time_cli_O1" 2>&1 | tee $O/C3_timing.txt
