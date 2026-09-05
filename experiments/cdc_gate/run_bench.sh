#!/bin/bash
# G7 on the real benchmark: 8,274 flops, five asynchronous domains, three
# gray-pointer async FIFOs and two-flop synchronizers on every single-bit
# crossing. Scores C3, C4, C5 and C6.
#
# This is the positive control. bench_top's CDC is believed correct, so a gate
# that reports violations here is either finding a real defect in the benchmark
# or is wrong itself, and both are reportable.
#
# The file list comes from tools/remeasure.BENCH_TOP_FILES, the same list the
# synthesis flow uses. A glob would pick up the variant files that redefine
# bench_top (that is exactly how the first attempt failed), and a hardcoded
# copy here would drift from what the flow actually builds.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=${1:-$SLACKSMITH_WORK/cdc_bench}
mkdir -p "$W"

FILES=$(python3 -c "
import sys; sys.path.insert(0, 'tools')
import remeasure
print(' '.join('rtl/' + f for f in remeasure.BENCH_TOP_FILES))
")
echo "sources: $(echo $FILES | wc -w) files from remeasure.BENCH_TOP_FILES"
echo

echo "=== structural pass: every crossing, depth only ==="
time python3 tools/cdc_check.py \
  --top bench_top \
  --workdir "$W" \
  --json "$W/bench_top_crossings.json" \
  $FILES
echo "exit: $?"
