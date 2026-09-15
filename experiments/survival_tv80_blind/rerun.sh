#!/bin/bash
# Amendment 1 of experiments/survival_tv80_blind/PREREGISTRATION.md: runs 3 to 6 never
# reached the model (account session limit), so each is rerun ONCE with run.sh's exact
# command. If a rerun's reply is the session-limit message again, reruns stop there.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || { echo "FATAL: no CLAUDE_CODE_OAUTH_TOKEN"; exit 2; }
D=experiments/depth_tv80
R=experiments/survival_tv80_blind/results; mkdir -p $R
LAST_START_UTC="14:00"   # 19:30 IST, the registered stop rule
for i in 3 4 5 6; do
  now=$(date -u +%H:%M)
  if [[ "$now" > "$LAST_START_UTC" ]]; then
    echo "rerun $i not started: $now UTC is past the 19:30 IST stop rule" | tee -a $R/not_run.txt
    continue
  fi
  W=$SLACKSMITH_WORK/survival_tv80_blind/run$i; rm -rf "$W"; mkdir -p "$W"
  echo "################ rerun $i (amendment 1), $(date -u +%H:%M:%S) UTC ################"
  python3 -u tools/slacksmith.py \
    --rtl-dir $D/rtl --rtl-files $D/rtl_files.txt --top tv80s \
    --sdc $D/tv80.sdc --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
    --clock clk --engine sta \
    --proposer cli --claude-bin "$REPO/experiments/survival_tv80_blind/claude_blind.sh" \
    --max-online 1 --max-iters 2 --g5 total \
    --gate-param Mode=1 \
    --workdir "$W" 2>&1 | tee $R/run$i.log
  echo "exit: ${PIPESTATUS[0]}" | tee -a $R/run$i.log
  mkdir -p $R/run$i
  cp "$W"/decisions.jsonl "$W"/SUMMARY.md $R/run$i/ 2>/dev/null
  cp -r "$W"/cli "$W"/online_variants $R/run$i/ 2>/dev/null
  if [ -d "$W/gates" ]; then
    (cd "$W/gates" && find . -type f \( -name '*.json' -o -name 'g4.log' -o -name 'miter_prop.sv' -o -name '*.eqy' \) \
      | while read -r f; do mkdir -p "$REPO/$R/run$i/gates/$(dirname "$f")"; cp "$f" "$REPO/$R/run$i/gates/$f"; done)
  fi
  if grep -q "hit your session limit" "$R/run$i/cli/RESPONSE_O1.txt" 2>/dev/null; then
    echo "rerun $i hit the session limit again: reruns stop here (amendment 1)" | tee -a $R/not_run.txt
    break
  fi
done
grep -h '"step": "gate"' $R/run*/decisions.jsonl 2>/dev/null | tee $R/gates.txt
grep -h '"step": "classify"' $R/run*/decisions.jsonl 2>/dev/null | grep -o '"lever": "[a-z]*", "routed_lever": "[a-z]*", "lever_forced": [a-z]*' | tee $R/routing.txt
