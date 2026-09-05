set -u
# Equivalence of the OpenROAD netlist before and after repair_design.
#
# Both sides are written by OpenROAD from the same placed design, so they share
# its flat naming and equiv_make has something to match on. Comparing the
# repaired netlist against the ORIGINAL hierarchical Yosys netlist does not
# work: equiv_make found only 86 equivalence points in a 55K-cell design and
# proved none, which is a failure of the matching, not a result.
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
Y=$OSS_CAD_BIN/yosys
LIB=$LIBERTY
W=$HOME/or_repair
A=$W/prerepair.v
B=$W/repaired.v

for f in "$A" "$B"; do [ -s "$f" ] || { echo "FATAL: $f missing"; exit 2; }; done
echo "prerepair.v $(stat -c%s $A) bytes, repaired.v $(stat -c%s $B) bytes"

echo "=== formal equivalence, pre-repair (gold) vs repaired (gate) ==="
$Y -p "
  read_liberty -lib $LIB
  read_verilog $A
  prep -top bench_top -flatten
  design -stash gold
  read_liberty -lib $LIB
  read_verilog $B
  prep -top bench_top -flatten
  design -stash gate
  design -copy-from gold -as gold bench_top
  design -copy-from gate -as gate bench_top
  equiv_make gold gate equiv
  hierarchy -top equiv
  equiv_struct
  equiv_simple -seq 5
  equiv_induct -seq 5
  equiv_status
" > $W/equiv_or.log 2>&1
echo "exit: $?"
grep -E "Found [0-9]+ unproven|Proved [0-9]+|Equivalence check|ERROR" $W/equiv_or.log | tail -8
