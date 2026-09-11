#!/bin/bash
# R28/R29: corroborate P5's refutation by REPLAYING its counterexample in
# simulation, which needs no assumption about whether the miter can tell a
# design from itself.
#
# Four solver budgets failed to close P5's null control (R19, R26, R27). This
# is different evidence: SBY writes a self-contained testbench that drives the
# exact counterexample, so running it shows gold and gate diverging directly.
# It is the same kind of evidence P4 has and P5 lacked.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/missing_classes/results; mkdir -p $R
G=$SLACKSMITH_WORK/r19_P5
TB=$(ls $G/miter_prop_bmc/engine_0/trace_tb.v 2>/dev/null | head -1)
[ -s "$TB" ] || { echo "FATAL: no trace_tb.v at $G/miter_prop_bmc/engine_0/"; exit 2; }
echo "trace: $TB ($(wc -l < $TB) lines)"

W=$SLACKSMITH_WORK/replay_p5; rm -rf $W; mkdir -p $W
cp $G/gold.v $G/gate.v $G/miter_prop.sv $TB $W/

echo
echo "=============== R28: replay on gold vs GATE (expect divergence) ==============="
( cd $W && iverilog -g2012 -DFORMAL -o tb_real gold.v gate.v miter_prop.sv trace_tb.v \
    && vvp tb_real 2>&1 | head -20 ) | tee $R/R28_replay_real.txt

echo
echo "=============== R29: same trace on gold vs GOLD (expect none) ==============="
# The control this method needs, and it costs seconds rather than 1800.
sed 's/rv32i_core_gold/rv32i_core_gate/' $W/gold.v > $W/gold_as_gate.v
( cd $W && iverilog -g2012 -DFORMAL -o tb_ctrl gold.v gold_as_gate.v miter_prop.sv trace_tb.v \
    && vvp tb_ctrl 2>&1 | head -20 ) | tee $R/R29_replay_control.txt
