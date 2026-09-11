#!/bin/bash
# The unforced run. See PREREGISTRATION.md.
#
# NOTE WHAT IS ABSENT: there is no --force-lever. Every other RTL result in
# this project was produced with --force-lever rtl, because bench_top's binding
# paths are fanout-dominated and the classifier correctly routes them to the
# physical lever. This run asks whether the router EVER selects RTL on its own.
#
# If it routes to physical anyway, that is the result. Trying a second design
# after seeing this one route to physical is a void condition.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || {
  echo "FATAL: no CLAUDE_CODE_OAUTH_TOKEN"; exit 2; }
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
[ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="$HOME/.local/bin/claude"
[ -x "$CLAUDE_BIN" ] || { echo "FATAL: no claude CLI"; exit 2; }
W=${1:-$SLACKSMITH_WORK/unforced}
rm -rf "$W"; mkdir -p "$W"

python3 -u tools/slacksmith.py \
  --rtl-dir experiments/unforced/rtl \
  --rtl-files experiments/unforced/rtl_files.txt \
  --top i2c_master_top \
  --sdc experiments/unforced/i2c.sdc \
  --liberty "$LIBERTY" \
  --sta-bin "$STA_BIN" \
  --clock wb_clk_i \
  --engine sta \
  --proposer cli \
  --claude-bin "$CLAUDE_BIN" \
  --max-online 1 \
  --max-iters 2 \
  --g5 total \
  --workdir "$W"
echo "exit: $?"
