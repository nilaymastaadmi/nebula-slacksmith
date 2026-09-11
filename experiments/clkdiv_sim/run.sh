#!/bin/bash
# Evidence for the generated-clock periods REPORT section 4 claims.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/clkdiv_sim
W=$SLACKSMITH_WORK/clkdiv_sim; rm -rf $W; mkdir -p $W
iverilog -g2012 -o $W/tb rtl/clkdiv.v $D/tb_clkdiv.sv
vvp $W/tb | tee $D/results.log
