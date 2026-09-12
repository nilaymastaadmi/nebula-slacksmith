#!/bin/bash
# R37 and R38: the marginal RTL gain AFTER repair_design.
#
# REPORT section 1 names this as the most important quantity the project has
# not measured. Both netlists go through the identical OpenROAD flow under the
# same SDC, into separate work dirs so neither touches $HOME/or_repair, whose
# prerepair.v and repaired.v are the inputs to experiments/ppa/power/.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/composed_rtl/results; mkdir -p $R
SDC=sdc/bench_top_v3.sdc

GOLD_NET=$SLACKSMITH_WORK/cr_baseline/baseline_mapped.v
CMP_NET=$SLACKSMITH_WORK/cr_composed_A4_O2_O1/variant/variant_mapped.v
for f in "$GOLD_NET" "$CMP_NET"; do
  [ -s "$f" ] || { echo "FATAL: missing $f. Run run.sh first."; exit 2; }
done

echo "########## gold through repair_design ##########"
OR_REPAIR_WORK=$SLACKSMITH_WORK/cr_or_gold \
  bash experiments/openroad_repair/run.sh "$GOLD_NET" "$SDC" 2>&1 | tee $R/repair_gold.txt

echo "########## composed through repair_design ##########"
OR_REPAIR_WORK=$SLACKSMITH_WORK/cr_or_composed \
  bash experiments/openroad_repair/run.sh "$CMP_NET" "$SDC" 2>&1 | tee $R/repair_composed.txt
