#!/bin/bash
# Amendment 3: R97 proof of the hinted variant, then R98 and R99 timing.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/invariant_obligation; R=$D/results
cd $D/tv80
echo "################ R97: hinted variant under the invariant, and its null control ################"
for t in hint hint_broken; do
  timeout 900 $OSS_CAD_BIN/sby -f child.sby $t > ../results/R97_child_$t.log 2>&1
  echo "  $t: $(grep -E 'failed assertion|DONE \(' ../results/R97_child_$t.log | tail -2 | tr '\n' ' ')"
done
cd "$REPO"
echo
echo "################ R98 / R99: timing ################"
bash experiments/depth_tv80/measure.sh \
  "run1_O1_onehot_mcycle_tail_case_merge:$REPO/experiments/depth_tv80/results/run1/online_variants/O1_tv80_mcode.v" \
  "run1_hinted_full_parallel_case:$REPO/$D/hint/tv80_hint.v" \
  2>&1 | tail -14 | tee $R/R98_R99_survival.txt
