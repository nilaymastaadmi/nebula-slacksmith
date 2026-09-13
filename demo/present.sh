#!/bin/bash
# Presenter for the demo recording: one beat per invocation, one take per beat.
#
#   bash demo/present.sh <beat 1-8>          # waits for the go file, then plays
#   bash demo/present.sh <beat 1-8> --dry    # no waits, no holds, for checking
#   touch ~/slacksmith_work/present/go       # starts a waiting take
#
# Why a script and not a person typing: the recording is driven from a session
# that may not type into a terminal, and a scripted take is also the only way
# to hold every screen for exactly as long as its narration runs. The hold
# times come from demo/present_plan.py, which derives them from demo/SCRIPT.md,
# so editing the narration re-times the takes without touching this file.
#
# Honesty rules this script keeps:
#   - A beat that is too slow to run on camera (1, 2 and 6, measured by
#     tools/capture_takes.sh) is REPLAYED from demo/takes/ and the screen says
#     so, as demo/VIDEO_PROMPT.md requires. Everything else runs for real.
#   - It prints no number of its own. Every figure on screen is tool output or
#     a committed evidence file, so nothing here can disagree with REPORT.md.
#   - Screens follow demo/SCRIPT.md's SCREEN line. Where a ZOOM TARGET has no
#     command in DEMO.md (beat 4's checker verdicts, beat 5's lever table and
#     PPA factor), the screen cats the committed evidence file that carries it.
set -u
BEAT=${1:?usage: bash demo/present.sh <beat 1-8> [--dry]}
MODE=${2:-}
. "$(dirname "${BASH_SOURCE[0]}")/../tools/env.sh"
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0="$REPO"

T=$REPO/demo/takes
P=$SLACKSMITH_WORK/present
GO=$P/go
LOG=$P/beat$BEAT.times
mkdir -p "$P"

DRY=0; [ "$MODE" = "--dry" ] && DRY=1
C_P=$'\e[38;5;71m'; C_C=$'\e[1;37m'; C_N=$'\e[38;5;245m'; C_0=$'\e[0m'
[ $DRY -eq 1 ] && { C_P=; C_C=; C_N=; C_0=; }

prompt () { printf '%s$%s %s%s%s\n' "$C_P" "$C_0" "$C_C" "$1" "$C_0"; }
note ()   { printf '%s# %s%s\n' "$C_N" "$1" "$C_0"; }
live ()   { prompt "$1"; bash -c "$1"; }      # runs for real, on camera
replay () {  # $1 capture file, $2.. the original command, one display line each
  local f=$1; shift
  prompt "cat demo/takes/$f"
  note "replayed: a recorded run of the command below, too slow to run on camera"
  local l; for l in "$@"; do note "  $l"; done
  cat "$T/$f"
}

SLACK_CMD=(
  "python3 tools/slacksmith.py --sdc sdc/bench_top_v2.sdc \\"
  "  --liberty ~/sta_work/sky130hd_tt.lib --sta-bin ~/tools/OpenSTA/build/sta \\"
  "  --clock clk_a --clock clk_b --clock clk_e --workdir ~/demo_run --engine sta"
)
GITLOG="git log --diff-filter=A --format='%ad %h %s' --date=short -- experiments/llm_proposer/PREREGISTRATION.md experiments/llm_proposer/proposals/"
TSV="column -t -s \$'\\t' experiments/slackbench/results/raw.tsv"

screen () {
  case "$1" in
    bench)       replay beat1.txt "python3 tools/bench_size.py" ;;
    loop)        replay beat2_loop.txt "${SLACK_CMD[@]}" ;;
    showrun)     live "python3 tools/show_run.py ~/demo_run/decisions.jsonl" ;;
    final)       live "python3 tools/show_run.py experiments/closed_loop/run_v3_final.jsonl" ;;
    gitlog)      live "cat experiments/llm_proposer/PREREGISTRATION.md | head -30"
                 live "$GITLOG" ;;
    result)      live "cat experiments/llm_proposer/fourchecker/RESULT.md" ;;
    trace)       live "sed -n '140,150p' experiments/llm_proposer_aes/NOTES.md" ;;
    lever)       live "sed -n '79,86p' experiments/openroad_repair/NOTES.md" ;;
    post_repair) live "cat experiments/composed_rtl/results/post_repair_summary.txt"
                 live "cat experiments/composed_rtl/results/abc_buffered_pair.txt" ;;
    ppa)         live "cat experiments/ppa/fmax/results/table.md" ;;
    verdict)     replay beat6_verdict.txt "bash tools/verdict_regression.sh" ;;
    classify)    replay beat6_classify.txt "python3 tools/classify_regression.py" ;;
    sdc)         live "bash experiments/sdc_integrity/run.sh" ;;
    page1)       live "$TSV | sed -n '1,29p'" ;;
    page2)       live "$TSV | sed -n '1p;30,\$p'" ;;
    *) echo "present.sh: no screen named $1" >&2; return 1 ;;
  esac
}

# ---- preflight: fail before the camera rolls, never during a take ----------
PLAN=$(python3 "$REPO/demo/present_plan.py" "$BEAT") || { echo "present.sh: no plan for beat $BEAT" >&2; exit 1; }
fail () { echo "PREFLIGHT FAIL: $*" >&2; exit 1; }
if [ $DRY -eq 0 ]; then
  cols=$(tput cols 2>/dev/null || echo 0); rows=$(tput lines 2>/dev/null || echo 0)
  [ "$cols" -ge 165 ] || fail "terminal is $cols columns, need 165 (demo/PHASE1_CUT.md finding 4)"
  [ "$rows" -ge 40 ]  || fail "terminal is $rows rows, need 40"
fi
case "$BEAT" in
  1) [ -s "$T/beat1.txt" ] || fail "missing demo/takes/beat1.txt, run tools/capture_takes.sh" ;;
  2) [ -s "$T/beat2_loop.txt" ] || fail "missing demo/takes/beat2_loop.txt"
     n=$(grep -c g0_sdc ~/demo_run/decisions.jsonl 2>/dev/null || echo 0)
     [ "$n" -eq 1 ] || fail "~/demo_run holds $n runs, need exactly 1 or show_run replays duplicates (finding 3)" ;;
  6) [ -s "$T/beat6_verdict.txt" ] && [ -s "$T/beat6_classify.txt" ] || fail "missing beat 6 captures" ;;
esac

if [ $DRY -eq 1 ]; then
  while IFS=$'\t' read -r name secs; do
    [ "$name" = TOTAL ] && { echo "=== beat $BEAT take $secs s ==="; continue; }
    echo "--- screen $name, hold $secs s ---"
    screen "$name"
  done <<< "$PLAN"
  exit 0
fi

# warm the filesystem cache so live commands do not stall on camera; output discarded
while IFS=$'\t' read -r name _; do
  [ "$name" = TOTAL ] || screen "$name" > /dev/null 2>&1
done <<< "$PLAN"

rm -f "$GO" "$P/ready"
trap 'tput cnorm 2>/dev/null; rm -f "$P/ready"' EXIT
tput civis 2>/dev/null
clear
echo "$BEAT" > "$P/ready"   # warmed and waiting; whoever triggers should wait for this
until [ -e "$GO" ]; do sleep 0.05; done
rm -f "$P/ready"
T0=$(date +%s.%N)
echo "trigger 0.00" > "$LOG"

while IFS=$'\t' read -r name secs; do
  [ "$name" = TOTAL ] && continue
  start=$(date +%s.%N)
  printf '%s %.2f\n' "$name" "$(echo "$start - $T0" | bc)" >> "$LOG"
  clear
  screen "$name"
  left=$(echo "$start + $secs - $(date +%s.%N)" | bc)
  if [ "$(echo "$left > 0" | bc)" -eq 1 ]; then sleep "$left"; fi
done <<< "$PLAN"
printf 'end %.2f\n' "$(echo "$(date +%s.%N) - $T0" | bc)" >> "$LOG"

sleep infinity   # hold the last frame; the take is trimmed to length afterwards
