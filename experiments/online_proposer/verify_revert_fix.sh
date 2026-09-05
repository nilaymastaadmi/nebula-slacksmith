#!/bin/bash
# Verify the revert fix behaviourally, with the SAME two proposals.
#
# Before the fix, iteration 4 measured clk_e -25.957, byte-identical to the
# iteration 1 baseline, because reverting O2 discarded confirmed O1 too.
# After the fix it must measure the O1 state, clk_e -24.079.
#
# --max-online 2 so the loop stops at its cap rather than asking for an O3
# nobody is waiting to answer.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=$SLACKSMITH_WORK/online_fixed
SCRATCH=/mnt/c/Users/toshn/AppData/Local/Temp/claude/C--/85fbc98d-cf67-40a3-8e9a-39dc2325ed42/scratchpad

rm -rf "$W"; mkdir -p "$W/handoff"
for n in 1 2; do
  cp "$SCRATCH/RESPONSE_O$n.json" "$W/handoff/RESPONSE_O$n.json"
done
echo "same proposals: O1 $(sha256sum "$W/handoff/RESPONSE_O1.json" | cut -c1-16)  O2 $(sha256sum "$W/handoff/RESPONSE_O2.json" | cut -c1-16)"
echo

python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v3.sdc \
  --liberty "$LIBERTY" \
  --sta-bin "$STA_BIN" \
  --clock clk_a --clock clk_b --clock clk_e \
  --engine sta \
  --proposer handoff \
  --force-lever rtl \
  --max-online 2 \
  --max-iters 6 \
  --g5 total \
  --workdir "$W"
echo "exit: $?"
