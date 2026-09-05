set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

echo "############ REGRESSION on both known verdicts ############"
echo "# P4 has a real counterexample and MUST read REFUTED."
echo "# A2 hit the strategy bound and MUST read UNRESOLVED."
echo

echo "--- P4 (expect REFUTED) ---"
python3 tools/gate_proposal.py \
  --proposal experiments/llm_proposer/proposals/P4.json \
  --rtl rtl/rv32i_core.v \
  --workdir $SLACKSMITH_WORK/verdict_check/P4 --timeout 300 2>&1 \
  | grep -E '"id"|"G3"|"G4"|counterexample|depth_exhausted'

echo
echo "--- A2 (expect UNRESOLVED) ---"
python3 tools/gate_proposal.py \
  --proposal experiments/llm_proposer_aes/proposals/A2.json \
  --rtl rtl/aes/aes_key_mem.v --module aes_key_mem \
  --clk clk --rst reset_n \
  --outputs "round_key:128,ready:1,sboxw:32" \
  --inputs "key:256,keylen:1,init:1,round:4,new_sboxw:32" \
  --workdir $SLACKSMITH_WORK/verdict_check/A2 --timeout 300 2>&1 \
  | grep -E '"id"|"G3"|"G4"|counterexample|depth_exhausted'

echo
echo "--- what the two partition logs actually say ---"
for p in P4 A2; do
  echo "[$p]"
  find $SLACKSMITH_WORK/verdict_check/$p/prop/strategies -name run.log 2>/dev/null \
    | xargs grep -lE "Reached maximum|model found" 2>/dev/null \
    | head -1 | xargs -r grep -oE "model found[^!]*!|Reached maximum number of time steps" \
    | head -2
done
