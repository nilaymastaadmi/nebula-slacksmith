#!/bin/bash
# Arm B: open_weight_2's JSON-mode run replayed with the whole request in context.
# See PREREGISTRATION.md. The only change from experiments/open_weight_2/
# run_jsonmode.sh is --num-ctx 16384 on the shim. First run is the run.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"

MODEL="${MODEL:-qwen2.5-coder:7b}"
HOST="${OLLAMA_HOST:-http://localhost:11434}"
W=${1:-$SLACKSMITH_WORK/open_weight_3_local}
O=experiments/open_weight_3/results_local

curl -s -m 5 "$HOST/api/tags" | grep -q "$MODEL" || {
  echo "VOID: $MODEL not available at $HOST. No substitute is run."; exit 2; }
echo "model: $MODEL at $HOST (no API key, localhost only), num_ctx 16384, JSON mode"

rm -rf "$W"; mkdir -p "$W/handoff"
python3 -u experiments/open_weight_3/shim_local.py \
  --dir "$W/handoff" --model "$MODEL" --host "$HOST" --json-mode --num-ctx 16384 \
  --timeout 7200 > "$W/shim.log" 2>&1 &
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
