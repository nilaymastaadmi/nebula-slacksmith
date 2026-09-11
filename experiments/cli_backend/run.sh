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

# Resolve the CLI explicitly. This script runs non-interactively
# (wsl -e bash run.sh), which is NOT a login shell, so ~/.profile never runs
# and ~/.local/bin is absent from PATH. Attempt 1 passed the empty string from
# `command -v claude` into subprocess.run and died with PermissionError: ''.
# Fail loudly rather than hand a subprocess an empty program name.
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
[ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="$HOME/.local/bin/claude"
[ -x "$CLAUDE_BIN" ] || {
  echo "FATAL: no claude CLI. Looked on PATH and at $HOME/.local/bin/claude."; exit 2; }
echo "claude: $CLAUDE_BIN"
W=${1:-$SLACKSMITH_WORK/cli_backend}
rm -rf "$W"; mkdir -p "$W"

python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v3.sdc \
  --liberty "$LIBERTY" \
  --sta-bin "$STA_BIN" \
  --clock clk_b \
  --engine sta \
  --proposer cli \
  --claude-bin "$CLAUDE_BIN" \
  --force-lever rtl \
  --max-online 1 \
  --max-iters 1 \
  --g5 total \
  --workdir "$W"
echo "exit: $?"
