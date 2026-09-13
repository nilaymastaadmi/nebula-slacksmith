#!/bin/bash
# Steps 4 and 5 of PREREGISTRATION.md. Run only after R86 and R87 have passed.
#
#   R88  tv80 run 1, re-gated plainly through the REPAIRED gate (derived ports,
#        module defaults, so Mode = 0)
#   R89  i2c run 1, the same
#   R90  the parent invariant on tv80_core at Mode = 1, by k-induction
#   R91  the child obligation under that invariant, Mode = 1
#   R92  a deliberately broken child under the same invariant
#   R94  run 3 at Mode = 1, no invariant
#   R95  run 1 at Mode = 1, no invariant
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/invariant_obligation; R=$D/results; mkdir -p $R
SBY=$OSS_CAD_BIN/sby

echo "################ R88: tv80 run 1 through the repaired gate ################"
python3 tools/gate_proposal.py \
  --proposal experiments/depth_tv80/results/run1/online_variants/O1.json \
  --rtl experiments/depth_tv80/rtl/tv80.v --module tv80_mcode \
  --depth 20 --timeout 420 \
  --workdir "$SLACKSMITH_WORK/io_R88" --repo . > $R/R88_tv80_run1_regate.json 2>&1
grep -E '"G3"|"G4"|"G4_ports"|"G4_bmc"|"G4_pdr"' $R/R88_tv80_run1_regate.json

echo
echo "################ R89: i2c run 1 through the repaired gate ################"
python3 tools/gate_proposal.py \
  --proposal experiments/depth_i2c/results/run1/replay/O1.json \
  --rtl experiments/depth_i2c/rtl/i2c.v --module i2c_master_bit_ctrl \
  --depth 20 --timeout 420 \
  --workdir "$SLACKSMITH_WORK/io_R89" --repo . > $R/R89_i2c_run1_regate.json 2>&1
grep -E '"G3"|"G4"|"G4_ports"|"G4_bmc"|"G4_pdr"' $R/R89_i2c_run1_regate.json

cd $D/tv80
echo
echo "################ R90: parent invariant, tv80_core, Mode = 1 ################"
for t in excl onehot; do
  timeout 900 $SBY -f parent.sby $t > ../results/R90_parent_$t.log 2>&1
  echo "  $t: $(grep -E 'DONE \(|summary: (engine|successful|failed)' ../results/R90_parent_$t.log | tail -2 | tr '\n' ' ')"
done

echo
echo "################ R95 / R91 / R92 / R94: child obligations, Mode = 1 ################"
for t in plain inv broken run3; do
  timeout 900 $SBY -f child.sby $t > ../results/child_$t.log 2>&1
  echo "  $t: $(grep -E 'DONE \(|failed assertion' ../results/child_$t.log | tail -2 | tr '\n' ' ')"
done
