#!/bin/bash
# The missing-classes run. See PREREGISTRATION.md and amendment 1.
#
# Targets clk_b alone so the binding module is domain_b, the benchmark's
# 10-state FSM and the only block in it that is a candidate for both of the
# two classes the engine had never proposed.
#
# --force-lever rtl is REQUIRED and disclosed, same as experiments/online_proposer:
# the corrected classifier never routes to the RTL lever on this benchmark.
#
# SLACKSMITH_PROMPT points at v2, which adds the retiming row. v1 is untouched
# and stays attached to experiments/online_proposer.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"
W=${1:-$SLACKSMITH_WORK/missing_classes}
rm -rf "$W"; mkdir -p "$W"

python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v3.sdc \
  --liberty "$LIBERTY" \
  --sta-bin "$STA_BIN" \
  --clock clk_b \
  --engine sta \
  --proposer handoff \
  --force-lever rtl \
  --max-online 4 \
  --max-iters 4 \
  --g5 total \
  --workdir "$W"
echo "exit: $?"
