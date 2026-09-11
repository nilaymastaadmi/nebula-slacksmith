#!/bin/bash
# Score R5: does the retiming improve clk_b?
#
# Registered prediction was NO. 91.4% of that path's delay is fanout
# (classifier verdict FANOUT_DOMINATED at iteration 1) and this transform
# removes a decoder from the launch-to-capture path without reducing a single
# net's load.
#
# The instance/module pair is the IDENTITY swap (u_aes_b already instantiates
# aes_load); the transform arrives through --replace, which substitutes the
# variant file IN PLACE in BENCH_TOP_FILES so ABC sees the same file order.
#
# The number is measured on a transform PROVEN over 2 of 3 outputs, with
# round_key undecidable. That is stated wherever the number is quoted.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
O=experiments/missing_classes/results; mkdir -p $O
python3 tools/remeasure.py \
  --rtl-dir rtl --top bench_top \
  --swap-instance u_aes_b --swap-module aes_b \
  --replace "rtl/aes/aes_key_mem.v:experiments/missing_classes/aes_key_mem_O1.v" \
  --sdc sdc/bench_top_v3.sdc --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
  --clock clk_b \
  --workdir "$SLACKSMITH_WORK/time_O1" 2>&1 | tee $O/R5_timing.txt
