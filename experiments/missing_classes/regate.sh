#!/bin/bash
# Re-gate under the null control (amendment 3). Three questions:
#   R8  O1, whose REFUTED the null control showed was the harness
#   R9  A3, published REFUTED on the same module through the same miter
#   R10 P5, published REFUTED on rv32i_core, which has no unreset memory
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/missing_classes/results; mkdir -p $R

echo "=================== R8: O1 (aes_key_mem, k=0, branch 5) ==================="
python3 tools/gate_proposal.py \
  --proposal experiments/missing_classes/proposals/O1.json \
  --rtl rtl/aes/aes_key_mem.v --module aes_key_mem \
  --clk clk --rst reset_n \
  --inputs "key:256,keylen:1,init:1,round:4,new_sboxw:32" \
  --outputs "round_key:128,ready:1,sboxw:32" \
  --depth 20 --timeout 300 \
  --workdir "$SLACKSMITH_WORK/rg_O1" --repo . 2>&1 | tee $R/R8_O1.json

echo "=================== R9: A3 (aes_key_mem, k=1, branch 2) ==================="
python3 tools/gate_proposal.py \
  --proposal experiments/llm_proposer_aes/proposals/A3.json \
  --rtl rtl/aes/aes_key_mem.v --module aes_key_mem \
  --clk clk --rst reset_n \
  --inputs "key:256,keylen:1,init:1,round:4,new_sboxw:32" \
  --outputs "round_key:128,ready:1,sboxw:32" \
  --depth 20 --timeout 300 \
  --workdir "$SLACKSMITH_WORK/rg_A3" --repo . 2>&1 | tee $R/R9_A3.json

echo "=================== R10: P5 (rv32i_core, k=1, branch 2) ==================="
python3 tools/gate_proposal.py \
  --proposal experiments/llm_proposer/proposals/P5.json \
  --rtl rtl/rv32i_core.v --module rv32i_core \
  --depth 20 --timeout 300 \
  --workdir "$SLACKSMITH_WORK/rg_P5" --repo . 2>&1 | tee $R/R10_P5.json

echo "=================== R17: O2 (aes_key_mem, k=0, branch 4, FSM) ==================="
python3 tools/gate_proposal.py \
  --proposal experiments/missing_classes/proposals/O2.json \
  --rtl rtl/aes/aes_key_mem.v --module aes_key_mem \
  --clk clk --rst reset_n \
  --inputs "key:256,keylen:1,init:1,round:4,new_sboxw:32" \
  --outputs "round_key:128,ready:1,sboxw:32" \
  --depth 20 --timeout 300 \
  --workdir "$SLACKSMITH_WORK/rg_O2" --repo . 2>&1 | tee $R/R17_O2.json
