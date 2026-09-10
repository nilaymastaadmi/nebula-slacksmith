#!/bin/bash
# G7 on bench_top WITH clock groups read from the SDC.
#
# The comparison this exists to make: the same design, the same gate, with and
# without the constraint file G0 already fingerprints. Six of the sixteen
# findings in the no-SDC run were a clock crossing to its own divided version,
# which is synchronous and needs no synchronizer.
#
# This does NOT change G7's scorecard. C4 was scored WRONG against the run that
# produced it and stays WRONG; this is a post-scoring improvement, dated.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=${1:-$SLACKSMITH_WORK/cdc_groups}
rm -rf "$W"; mkdir -p "$W"

FILES=$(python3 -c "
import sys; sys.path.insert(0, 'tools')
import remeasure
print(' '.join('rtl/' + f for f in remeasure.BENCH_TOP_FILES))
")

echo "############ WITHOUT --sdc (the run that scored C4 wrong) ############"
python3 tools/cdc_check.py --top bench_top --workdir "$W/nosdc" \
  --json "$W/nosdc.json" $FILES
echo "exit: $?"
echo
echo "############ WITH --sdc sdc/bench_top_v3.sdc ############"
python3 tools/cdc_check.py --top bench_top --sdc sdc/bench_top_v3.sdc \
  --workdir "$W/sdc" --json "$W/sdc.json" $FILES
echo "exit: $?"
