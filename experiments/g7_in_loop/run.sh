#!/bin/bash
# Scores L1 to L3. The claim under test is that a transform can pass formal
# equivalence and still break a clock crossing, and that G7 catches it.
#
# L1 must hold for the rest to mean anything: if equivalence REJECTS the
# variant then the hole is not real and the case is thrown out, not patched.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=${1:-$SLACKSMITH_WORK/g7_loop}
rm -rf "$W"; mkdir -p "$W"
V=experiments/g7_in_loop/async_fifo_cdcbreak.v

echo "############ L1: is the variant functionally equivalent? ############"
# Both sides read as module async_fifo, so the variant is copied under a
# scratch name and EQY compares the two as gold and gate.
mkdir -p "$W/eq"
cp rtl/async_fifo.v "$W/eq/gold.v"
cp "$V"            "$W/eq/gate.v"
cp rtl/sync2ff.v   "$W/eq/"
cat > "$W/eq/eq.eqy" <<'EOF'
[options]

[gold]
read_verilog gold.v sync2ff.v
prep -top async_fifo -flatten

[gate]
read_verilog gate.v sync2ff.v
prep -top async_fifo -flatten

[strategy sby]
use sby
depth 12
engine smtbmc boolector
EOF
( cd "$W/eq" && eqy -f eq.eqy > eqy.log 2>&1; echo "eqy exit: $?" )
grep -E "Successfully proved|Unproven|proved|FAIL|ERROR" "$W/eq/eqy.log" | tail -6
echo

echo "############ L2 and L3: G7 on the original and the variant ############"
for side in gold gate; do
  src=$([ $side = gold ] && echo rtl/async_fifo.v || echo "$V")
  echo "--- $side ($src) ---"
  python3 tools/cdc_check.py --top async_fifo \
    --hamming --ham-module async_fifo --ham-depth 16 --ham-timeout 300 \
    --workdir "$W/$side" --json "$W/$side.json" \
    "$src" rtl/sync2ff.v
  echo "exit: $?"
  echo
done
