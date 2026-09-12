#!/bin/bash
# Amendment 2, R49 to R52: three more perturbation points for the post-repair
# noise floor, using the three parts of the composition. Their unbuffered
# netlists were built by run.sh; each goes through the identical OpenROAD flow
# gold and the composition went through, into its own work dir.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/composed_rtl/results; mkdir -p $R
SDC=sdc/bench_top_v3.sdc

for v in A4_onehot_read O2_fsm_reencode O1_fanout_split; do
  NET=$SLACKSMITH_WORK/cr_$v/variant/variant_mapped.v
  [ -s "$NET" ] || { echo "FATAL: missing $NET; run run.sh first"; exit 2; }
  echo "########## $v through repair_design ##########"
  OR_REPAIR_WORK=$SLACKSMITH_WORK/cr_or_$v \
    bash experiments/openroad_repair/run.sh "$NET" "$SDC" 2>&1 | tee $R/repair_$v.txt
done

echo
echo "=== post-repair summary (gold, A5 and composed from earlier runs) ==="
for f in repair_gold repair_gold_run2 repair_A5 repair_A4_onehot_read repair_O2_fsm_reencode repair_O1_fanout_split repair_composed; do
  [ -f $R/$f.txt ] || continue
  a=$(awk '/TIMING AFTER/{f=1} f&&/CLOCK:clk_a/{getline; print $1}' $R/$f.txt)
  b=$(awk '/TIMING AFTER/{f=1} f&&/CLOCK:clk_b/{getline; print $1}' $R/$f.txt)
  e=$(awk '/TIMING AFTER/{f=1} f&&/CLOCK:clk_e/{getline; print $1}' $R/$f.txt)
  ar=$(grep "Design area" $R/$f.txt | tail -1 | awk '{print $3}')
  printf "%-26s clk_a=%-8s clk_b=%-8s clk_e=%-8s area=%s\n" "$f" "$a" "$b" "$e" "$ar"
done | tee $R/post_repair_summary.txt
