#!/bin/bash
# Re-gate under the equal-initial-state assumption (amendment 6).
#   R21  O2  FSM re-encoding, expect PROVEN over 3 of 3
#   R22  O1  retiming, uncertain: carries an invariant across the write port
#   VOID A3  known-bad, MUST stay REFUTED. If the assumption makes a bad
#            transform prove, it is too strong and the result is thrown out.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
R=experiments/missing_classes/results; mkdir -p $R
run () {  # $1 tag  $2 proposal
  echo "=================== $1 ==================="
  python3 tools/gate_proposal.py \
    --proposal "$2" \
    --rtl rtl/aes/aes_key_mem.v --module aes_key_mem \
    --clk clk --rst reset_n \
    --inputs "key:256,keylen:1,init:1,round:4,new_sboxw:32" \
    --outputs "round_key:128,ready:1,sboxw:32" \
    --depth 8 --timeout 400 --null-timeout 400 --zero-init \
    --workdir "$SLACKSMITH_WORK/zi_$1" --repo . 2>&1 | tee $R/zeroinit_$1.json
}
run O2 experiments/missing_classes/proposals/O2.json
run O1 experiments/missing_classes/proposals/O1.json
run A3_voidcheck experiments/llm_proposer_aes/proposals/A3.json
