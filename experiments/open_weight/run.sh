#!/bin/bash
# The open-weight run. See PREREGISTRATION.md (R41 to R46). First run is the run.
#
# Same task, same SDC, same flags and the same three qualifiers as
# experiments/cli_backend/run.sh, so the only variable is the model. No API key
# is used or needed: the model runs locally under Ollama and the only network
# address touched is localhost.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"

MODEL="${MODEL:-qwen2.5:7b-instruct}"
HOST="${OLLAMA_HOST:-http://localhost:11434}"
W=${1:-$SLACKSMITH_WORK/open_weight}

# Void condition from the registration: no Ollama, no experiment. Do not fall
# back to a hosted model and call the result open-weight.
curl -s -m 5 "$HOST/api/tags" | grep -q "$MODEL" || {
  echo "VOID: $MODEL not available at $HOST. Registration forbids substituting"
  echo "      a hosted model, so this run reports VOID and stops."; exit 2; }
echo "model: $MODEL at $HOST (no API key, localhost only)"

rm -rf "$W"; mkdir -p "$W/handoff"

python3 -u experiments/open_weight/shim.py \
  --dir "$W/handoff" --model "$MODEL" --host "$HOST" > "$W/shim.log" 2>&1 &
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

O=experiments/open_weight/results; mkdir -p "$O"
cp -f "$W"/handoff/REQUEST_*.md  "$O/" 2>/dev/null
cp -f "$W"/handoff/RAW_*.txt     "$O/" 2>/dev/null
cp -f "$W"/handoff/META_*.json   "$O/" 2>/dev/null
cp -f "$W"/handoff/RESPONSE_*.json "$O/" 2>/dev/null
cp -f "$W"/decisions.jsonl       "$O/" 2>/dev/null
cp -f "$W/shim.log"              "$O/" 2>/dev/null
echo "artifacts in $O"
