#!/bin/bash
# The registered online-proposer run. See PREREGISTRATION.md and amendment 1.
#
# --force-lever rtl is REQUIRED and is disclosed, not incidental: the corrected
# classifier never routes to the RTL lever on this benchmark, so without it the
# proposer is never called. The log records lever_forced=true on the iteration
# where it happens.
#
# --proposer handoff halts the loop and writes a request file. The response is
# written by Claude Opus 5 via the session driving this project, the same
# proposer batches 1 and 2 disclosed. No counterexample and no G4 verdict is
# placed in the request; that exclusion is the batch-3 boundary.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=${1:-$SLACKSMITH_WORK/online}
rm -rf "$W"; mkdir -p "$W"

python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v3.sdc \
  --liberty "$LIBERTY" \
  --sta-bin "$STA_BIN" \
  --clock clk_a --clock clk_b --clock clk_e \
  --engine sta \
  --proposer handoff \
  --force-lever rtl \
  --max-online 6 \
  --max-iters 6 \
  --g5 total \
  --workdir "$W"
echo "exit: $?"
