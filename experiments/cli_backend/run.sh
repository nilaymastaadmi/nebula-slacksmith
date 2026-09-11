#!/bin/bash
# The unattended run. See PREREGISTRATION.md. First run is the run.
#
# env.sh sources ~/.slacksmith_token, which holds CLAUDE_CODE_OAUTH_TOKEN and
# lives OUTSIDE this repository. tools/preflight.sh fails if a
# credential-shaped string ever reaches a tracked file.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
export SLACKSMITH_PROMPT="$REPO/tools/proposer_prompt_v2.md"
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || {
  echo "FATAL: no CLAUDE_CODE_OAUTH_TOKEN. Put it in ~/.slacksmith_token."; exit 2; }
W=${1:-$SLACKSMITH_WORK/cli_backend}
rm -rf "$W"; mkdir -p "$W"

python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v3.sdc \
  --liberty "$LIBERTY" \
  --sta-bin "$STA_BIN" \
  --clock clk_b \
  --engine sta \
  --proposer cli \
  --claude-bin "$(command -v claude)" \
  --force-lever rtl \
  --max-online 1 \
  --max-iters 1 \
  --g5 total \
  --workdir "$W"
echo "exit: $?"
