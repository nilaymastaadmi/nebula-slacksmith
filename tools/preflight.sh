#!/bin/bash
# Check every external dependency before a run, and say exactly which one is
# missing and where it comes from. The alternative is what this repo did until
# now: fail forty lines into a two-minute run with "command not found".
#
#   usage: bash tools/preflight.sh
#
# Exits 0 if everything needed for tools/demo_check.sh is present, 1 otherwise.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

MISS=0
need () {  # $1 label, $2 path, $3 where it comes from
  if [ -e "$2" ]; then
    printf '  ok      %-16s %s\n' "$1" "$2"
  else
    printf '  MISSING %-16s %s\n            get it: %s\n' "$1" "$2" "$3"
    MISS=$((MISS+1))
  fi
}

echo "repo:  $REPO"
echo "work:  $SLACKSMITH_WORK"
echo
echo "external tools"
OSS="github.com/YosysHQ/oss-cad-suite-build releases; set OSS_CAD_BIN to its bin/"
need yosys    "$OSS_CAD_BIN/yosys"     "$OSS"
need yosys-abc "$OSS_CAD_BIN/yosys-abc" "$OSS"
need eqy      "$OSS_CAD_BIN/eqy"       "$OSS"
need sby      "$OSS_CAD_BIN/sby"       "$OSS"
need iverilog "$OSS_CAD_BIN/iverilog"  "$OSS"
need vvp      "$OSS_CAD_BIN/vvp"       "$OSS"
need OpenSTA  "$STA_BIN"               "build github.com/parallaxsw/OpenSTA; set STA_BIN"
need liberty  "$LIBERTY"               "SETUP.md, sky130_fd_sc_hd__tt_025C_1v80.lib; set LIBERTY"

echo
echo "optional (only the OpenROAD engine and G6 need these)"
for p in "$OPENROAD_BIN:openroad" "$ORFS_PLATFORM:orfs_platform"; do
  path=${p%:*}; lbl=${p##*:}
  if [ -e "$path" ]; then printf '  ok      %-16s %s\n' "$lbl" "$path"
  else printf '  absent  %-16s %s  (demo_check does not need it)\n' "$lbl" "$path"; fi
done

echo
echo "repo fixtures"
for f in experiments/classifier_regression/v3_bufsize_it3.v.gz \
         experiments/sdc_integrity/flat_E_mapped.v.gz \
         experiments/slackbench/results/raw.tsv \
         experiments/closed_loop/run_v3_final.jsonl; do
  if [ -e "$REPO/$f" ]; then printf '  ok      %s\n' "$f"
  else printf '  MISSING %s\n' "$f"; MISS=$((MISS+1)); fi
done

echo
echo "git history (beat 4 checks that registration precedes results)"
if git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 \
   && [ -n "$(git -C "$REPO" log --diff-filter=A --format=%h -- \
              experiments/llm_proposer/PREREGISTRATION.md 2>/dev/null)" ]; then
  echo "  ok      history present"
else
  echo "  MISSING history: clone the repo, do not download a zip"
  MISS=$((MISS+1))
fi

echo
echo "secret scan (this repository is public)"
# Added 2026-09-11. The cli proposer backend needs CLAUDE_CODE_OAUTH_TOKEN, and
# the obvious wrong way to supply it is to paste it into a script here. One of
# this author's earlier repositories carries a leaked API key in its git
# history, which is unremovable without a force-push, so the guard is cheap
# insurance against repeating it. The token goes in ~/.slacksmith_token,
# outside the repository, and tools/env.sh sources it if present.
SECRET_HITS=0
if git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
  HITS=$(git -C "$REPO" grep -lE 'sk-ant-(oat|api)[0-9]{2}-|ghp_[A-Za-z0-9]{36}'          -- . 2>/dev/null || true)
  if [ -n "$HITS" ]; then
    echo "  FAIL    credential-shaped string in tracked files:"
    echo "$HITS" | sed 's/^/            /'
    echo "          Do NOT commit. Rotate the credential, then remove it."
    SECRET_HITS=1
    MISS=$((MISS+1))
  fi
fi
[ $SECRET_HITS -eq 0 ] && echo "  ok      no credential-shaped strings tracked"

echo
if [ $MISS -eq 0 ]; then
  echo "preflight: all present. run: bash tools/demo_check.sh"
else
  echo "preflight: $MISS missing"
fi
[ $MISS -eq 0 ]
