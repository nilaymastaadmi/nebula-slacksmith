#!/bin/bash
# R19: does P5's null control close given 30 minutes instead of 5?
#
# P5's own miter refutes in 2 to 5 s. Its gold-vs-gold control did not close in
# 300 s against 2,048 flops, so the refutation is currently UNCORROBORATED. If
# the control still does not close at 1800 s, then this harness cannot
# corroborate ANY refutation on a design that size, and every rv32i_core
# refutation in the project inherits that caveat.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/missing_classes/results; mkdir -p $R
python3 tools/gate_proposal.py \
  --proposal experiments/llm_proposer/proposals/P5.json \
  --rtl rtl/rv32i_core.v --module rv32i_core \
  --depth 20 --timeout 300 --null-timeout 1800 \
  --workdir "$SLACKSMITH_WORK/r19_P5" --repo . 2>&1 | tee $R/R19_P5.json
