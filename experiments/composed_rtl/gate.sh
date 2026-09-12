#!/bin/bash
# G3 precondition and G4 proof on the composed variant (R33, R34).
#
# Same gate, same depth and same timeout the three parts were gated with in
# experiments/missing_classes/regate.sh. The composition is routed to branch 4,
# the strictest obligation any part carried, because O2 re-encodes state.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/composed_rtl/results; mkdir -p $R

python3 tools/gate_proposal.py \
  --proposal experiments/composed_rtl/proposals/CMP1.json \
  --rtl rtl/aes/aes_key_mem.v --module aes_key_mem \
  --clk clk --rst reset_n \
  --inputs "key:256,keylen:1,init:1,round:4,new_sboxw:32" \
  --outputs "round_key:128,ready:1,sboxw:32" \
  --depth 20 --timeout 300 \
  --workdir "$SLACKSMITH_WORK/cr_gate" --repo . 2>&1 | tee $R/CMP1_gate.json
