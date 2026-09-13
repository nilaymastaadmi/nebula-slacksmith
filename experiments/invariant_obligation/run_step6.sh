#!/bin/bash
# Amendment 2 then step 6.
#   R96  the invariant on tv80s with the TRANSFORMED tv80_mcode in place
#   R93  run 1's transform through depth_tv80's survival harness, against the
#        0.152 ns floor measured before any tv80 prediction was written
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/invariant_obligation; R=$D/results
echo "################ R96: invariant on the transformed design ################"
cd $D/tv80
for t in excl onehot; do
  timeout 900 $OSS_CAD_BIN/sby -f parent_variant.sby $t > ../results/R96_variant_$t.log 2>&1
  echo "  $t: $(grep -E 'successful proof|failed|DONE \(' ../results/R96_variant_$t.log | tail -2 | tr '\n' ' ')"
done
cd "$REPO"
echo
echo "################ R93: timing run 1's transform through the survival harness ################"
bash experiments/depth_tv80/measure.sh \
  "run1_O1_onehot_mcycle_tail_case_merge:$REPO/experiments/depth_tv80/results/run1/online_variants/O1_tv80_mcode.v" \
  2>&1 | tail -14 | tee $R/R93_survival.txt
