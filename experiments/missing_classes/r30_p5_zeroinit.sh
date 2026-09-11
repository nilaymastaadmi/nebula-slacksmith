#!/bin/bash
# R30/R31: is P5's counterexample an artifact of the two instances powering up
# with DIFFERENT register files? rv32i_core has an unreset regfile, which is
# the same precondition that poisoned aes_key_mem.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/missing_classes/results; mkdir -p $R
python3 tools/gate_proposal.py \
  --proposal experiments/llm_proposer/proposals/P5.json \
  --rtl rtl/rv32i_core.v --module rv32i_core \
  --depth 20 --timeout 400 --null-timeout 900 --zero-init \
  --workdir "$SLACKSMITH_WORK/r30_P5" --repo . 2>&1 | tee $R/R30_P5_zeroinit.json
