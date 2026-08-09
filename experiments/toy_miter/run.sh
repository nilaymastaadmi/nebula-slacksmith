#!/usr/bin/env bash
# Toy latency-changing miter: three engines, three separate verdicts.
# Uses only stock yosys (yosys-smtbmc, yosys-abc) -- no sby required.
#
# Usage: ./run.sh [depth]     (default depth 24)

set -u
DEPTH="${1:-24}"
cd "$(dirname "$0")"
mkdir -p work

banner() { echo; echo "=============================================================="; echo "  $1"; echo "=============================================================="; }

# ---------------------------------------------------------------- elaborate
banner "ELABORATE  (yosys -> smt2 / aiger)"
yosys -q -p "
    read_verilog -formal -sv mac_ref.v
    read_verilog -formal -sv mac_opt.v
    read_verilog -formal -sv miter.sv
    prep -top miter -flatten
    write_smt2 -wires work/miter.smt2
" || { echo "ELABORATION FAILED"; exit 1; }

yosys -q -p "
    read_verilog -formal -sv mac_ref.v
    read_verilog -formal -sv mac_opt.v
    read_verilog -formal -sv miter.sv
    prep -top miter -flatten
    memory_map
    techmap
    abc -g AND
    setundef -zero
    aigmap
    write_aiger -zinit work/miter.aig
" >/dev/null 2>&1

echo "smt2: $(wc -l < work/miter.smt2) lines"
[ -f work/miter.aig ] && echo "aiger: $(stat -c%s work/miter.aig) bytes"

# ---------------------------------------------------------------- 1. BMC
banner "1. BMC  (bounded, depth $DEPTH)  -- finds bugs, proves nothing"
yosys-smtbmc -s z3 -t "$DEPTH" --dump-vcd work/bmc.vcd work/miter.smt2
BMC=$?
echo "-> BMC exit $BMC"

# ------------------------------------------------------- 2. k-induction
banner "2. K-INDUCTION  (unbounded, depth $DEPTH)"
echo "NOTE: the induction step starts from an ARBITRARY state, so"
echo "      'initial assume(rst)' does not constrain it. If this fails"
echo "      while BMC passes, the counterexample is an unreachable state"
echo "      and you need a strengthening invariant -- that is a real"
echo "      finding, not a bug in the design."
yosys-smtbmc -s z3 -i -t "$DEPTH" --dump-vcd work/induct.vcd work/miter.smt2
IND=$?
echo "-> induction exit $IND"

# --------------------------------------------------------------- 3. PDR
banner "3. PDR / IC3  (unbounded, no manual invariants)"
if [ -f work/miter.aig ]; then
    yosys-abc -c "read_aiger work/miter.aig; fold; strash; pdr" 2>&1 | tail -20
    echo "-> pdr done"
else
    echo "SKIPPED: aiger export unavailable"
fi

banner "SUMMARY"
echo "BMC (bounded, depth $DEPTH) : exit $BMC   -- 0 = no counterexample found"
echo "K-induction                 : exit $IND   -- 0 = proved for all time"
echo "PDR                         : see above  -- look for 'Property proved'"
echo
echo "Report these three separately. A timeout is NOT a pass."
