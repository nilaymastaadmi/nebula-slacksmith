#!/bin/bash
# Arm A: the hosted open-weight run. See PREREGISTRATION.md. First run is the run.
#
# Same task, SDC, flags and qualifiers as experiments/open_weight_2/run.sh, so
# the variable is the model and where it runs. The key is read from a file
# outside the repository by the shim and never appears here.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"

MODEL="${MODEL:-google/gemma-4-31b-it:free}"
BASE="${OPENWEIGHT_BASE:-https://openrouter.ai/api/v1}"
KEYFILE="${OPENWEIGHT_KEY_FILE:-$HOME/.openrouter_key}"
W=${1:-$SLACKSMITH_WORK/open_weight_3_hosted}
O=experiments/open_weight_3/results_hosted

# Void conditions from the registration. No key, or the registered model is not
# listed by the endpoint: report VOID and stop. Never substitute another model.
[ -s "$KEYFILE" ] || { echo "VOID: no key at $KEYFILE"; exit 2; }
curl -s -m 30 "$BASE/models" | grep -q "\"$MODEL\"" || {
  echo "VOID: $MODEL is not listed at $BASE/models. No substitute is run."; exit 2; }
echo "model: $MODEL at $BASE (key file outside the repository)"

rm -rf "$W"; mkdir -p "$W/handoff"
python3 -u experiments/open_weight_3/shim_hosted.py \
  --dir "$W/handoff" --model "$MODEL" --base "$BASE" --key-file "$KEYFILE" \
  > "$W/shim.log" 2>&1 &
SHIM=$!

python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v3.sdc \
  --liberty "$LIBERTY" \
  --sta-bin "$STA_BIN" \
  --clock clk_b \
  --engine sta \
  --proposer handoff \
  --force-lever rtl \
  --max-online 1 \
  --max-iters 1 \
  --g5 total \
  --workdir "$W"
RC=$?
wait $SHIM 2>/dev/null
echo "--- shim log ---"; cat "$W/shim.log"
echo "loop exit: $RC"

mkdir -p "$O"
cp -f "$W"/handoff/REQUEST_*.md "$W"/handoff/RAW_*.txt "$W"/handoff/META_*.json \
      "$W"/handoff/RESPONSE_*.json "$W"/decisions.jsonl "$W/shim.log" "$O/" 2>/dev/null
echo "artifacts in $O"
