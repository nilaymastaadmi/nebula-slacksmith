#!/bin/bash
# The composed variant under the equal-initial-state assumption, gated exactly
# as the parts were in experiments/missing_classes/regate_zeroinit.sh:
# depth 8, timeout 400, null-timeout 400, --zero-init.
#
# Why both gates run. aes_key_mem reads round_key out of an unreset memory, so
# the plain miter starts the two instances from different arbitrary contents and
# the null control refutes gold against gold on that one output (REPORT §9).
# The parts carry two verdicts each for that reason, and the composition has to
# carry the same two or the comparison is not like for like.
#
# The void check travels with the assumption: A3 is known-bad and MUST stay
# REFUTED under --zero-init. It was re-run with the parts and is not re-run
# here; if it ever passes, every zero-init verdict in the project goes with it.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/composed_rtl/results; mkdir -p $R

python3 tools/gate_proposal.py \
  --proposal experiments/composed_rtl/proposals/CMP1.json \
  --rtl rtl/aes/aes_key_mem.v --module aes_key_mem \
  --clk clk --rst reset_n \
  --inputs "key:256,keylen:1,init:1,round:4,new_sboxw:32" \
  --outputs "round_key:128,ready:1,sboxw:32" \
  --depth 8 --timeout 400 --null-timeout 400 --zero-init \
  --workdir "$SLACKSMITH_WORK/cr_gate_zi" --repo . 2>&1 | tee $R/CMP1_gate_zeroinit.json
