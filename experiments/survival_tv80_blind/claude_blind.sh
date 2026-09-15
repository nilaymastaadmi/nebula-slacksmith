#!/bin/bash
# The blind proposer for experiments/survival_tv80_blind/: the same Claude Code CLI
# the unattended runs used, started in an empty temporary directory with every
# built-in tool disallowed, so the model sees the prompt and nothing else. Passed
# to tools/slacksmith.py as --claude-bin; tools/ is unchanged.
set -u
CB="${CLAUDE_REAL_BIN:-$HOME/.local/bin/claude}"
EMPTY=$(mktemp -d)
cd "$EMPTY" || exit 3
exec "$CB" "$@" --disallowedTools Bash Read Write Edit Glob Grep \
  WebFetch WebSearch NotebookEdit Task Agent TodoWrite ToolSearch Skill
