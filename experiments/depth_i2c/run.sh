#!/bin/bash
# Phase 1 of experiments/depth_i2c/PREREGISTRATION.md: three unattended runs
# on i2c_master_top, NO --force-lever, one online proposal each, two
# iterations so the loop's own accept-or-revert step runs on the proposal.
# Same flags as experiments/unforced/ run 6. Everything the loop wrote that is
# not a multi-megabyte solver model is copied into results/runN/.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || { echo "FATAL: no CLAUDE_CODE_OAUTH_TOKEN"; exit 2; }
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
[ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="$HOME/.local/bin/claude"
[ -x "$CLAUDE_BIN" ] || { echo "FATAL: no claude CLI"; exit 2; }
echo "claude: $CLAUDE_BIN"
D=experiments/depth_i2c
R=$D/results; mkdir -p $R
N=${DEPTH_I2C_RUNS:-3}

for i in $(seq 1 $N); do
  W=$SLACKSMITH_WORK/depth_i2c/run$i; rm -rf "$W"; mkdir -p "$W"
  echo "################ run $i of $N, $(date -u +%H:%M:%S) UTC ################"
  python3 -u tools/slacksmith.py \
    --rtl-dir $D/rtl --rtl-files $D/rtl_files.txt --top i2c_master_top \
    --sdc $D/i2c.sdc --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
    --clock wb_clk_i --engine sta \
    --proposer cli --claude-bin "$CLAUDE_BIN" \
    --max-online 1 --max-iters 2 --g5 total \
    --workdir "$W" 2>&1 | tee $R/run$i.log
  echo "exit: ${PIPESTATUS[0]}" | tee -a $R/run$i.log
  mkdir -p $R/run$i
  cp "$W"/decisions.jsonl "$W"/SUMMARY.md $R/run$i/ 2>/dev/null
  cp -r "$W"/cli "$W"/online_variants $R/run$i/ 2>/dev/null
  if [ -d "$W/gates" ]; then
    (cd "$W/gates" && find . -type f \( -name '*.json' -o -name 'g4.log' -o -name '*.raw.log' -o -name '*.synth.log' -o -name 'miter_prop.sv' -o -name '*.eqy' \) \
      | while read -r f; do mkdir -p "$REPO/$R/run$i/gates/$(dirname "$f")"; cp "$f" "$REPO/$R/run$i/gates/$f"; done)
  fi
done

echo
echo "=== phase 1 gate verdicts ==="
grep -h '"step": "gate"' $R/run*/decisions.jsonl 2>/dev/null | tee $R/phase1_gates.txt
grep -h '"step": "classify"' $R/run*/decisions.jsonl 2>/dev/null | grep -o '"lever": "[a-z]*", "routed_lever": "[a-z]*", "lever_forced": [a-z]*' | tee $R/phase1_routing.txt
