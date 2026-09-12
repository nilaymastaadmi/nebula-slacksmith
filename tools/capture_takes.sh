#!/bin/bash
# Capture the real on-screen output of every beat in DEMO.md, one file per beat,
# plus the wall-clock of each beat, into demo/takes/.
#
# Run this whenever DEMO.md, a fixture or a tool changes, then regenerate the
# duration table:
#
#     bash tools/capture_takes.sh
#     python3 tools/duration_table.py --write --width 165 --target 292
#
# Nothing here edits a command. Every command below is copied from DEMO.md
# verbatim, which is the point: if a command in DEMO.md is broken, the capture
# for that beat comes out empty and tools/duration_table.py says so. That is
# how beat 5's flatten command was found printing 0 bytes on 2026-09-12, after
# tools/demo_check.sh had reported 15 pass, 0 fail without covering beat 5.
#
# Why every beat is timed and not just beat 2: three files in this repository
# gave three different figures for beat 2's live compute and all three were
# wrong. A duration nobody re-derives is stale by default, so the timings are
# measured here and read by tools/duration_table.py rather than written into
# any document.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"

T=$REPO/demo/takes
mkdir -p "$T"

# The recording terminal width, so a capture that will wrap on the day wraps
# here too. Override to try a different geometry: COLS=205 bash tools/capture_takes.sh
export COLUMNS="${COLS:-165}"

# beat -> seconds, written as demo/takes/beatN_timing.txt so the table can read it
timed () {  # $1 beat number, then the command
  local n=$1; shift
  local s e
  s=$(date +%s.%N)
  "$@"
  e=$(date +%s.%N)
  echo "BEAT${n}_WALL_SECONDS=$(echo "$e - $s" | bc)" > "$T/beat${n}_timing.txt"
}

echo "capture at ${COLUMNS} columns into demo/takes/"

echo "### beat 1"
timed 1 bash -c "python3 tools/bench_size.py > '$T/beat1.txt' 2>&1"

echo "### beat 2 (the only live compute)"
# ~/demo_run is NOT cleared here on purpose: DEMO.md's command names that path
# and this script does not alter it. Clear it yourself before recording, or
# show_run.py replays every accumulated run (2 g0_sdc markers, 2026-09-12).
timed 2 bash -c "python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v2.sdc \
  --liberty ~/sta_work/sky130hd_tt.lib \
  --sta-bin ~/tools/OpenSTA/build/sta \
  --clock clk_a --clock clk_b --clock clk_e \
  --workdir ~/demo_run --engine sta > '$T/beat2_loop.txt' 2>&1"
python3 tools/show_run.py ~/demo_run/decisions.jsonl > "$T/beat2_showrun.txt" 2>&1

echo "### beat 3"
timed 3 bash -c "for f in run_v3_final run_v3_fixed run_v3_flat; do
  python3 tools/show_run.py experiments/closed_loop/\$f.jsonl > '$T'/beat3_\$f.txt 2>&1
done"

echo "### beat 4"
timed 4 bash -c "cat experiments/llm_proposer/PREREGISTRATION.md | head -30 > '$T/beat4_prereg.txt' 2>&1
git log --diff-filter=A --format='%ad %h %s' --date=short -- \
  experiments/llm_proposer/PREREGISTRATION.md \
  experiments/llm_proposer/proposals/ > '$T/beat4_gitlog.txt' 2>&1"

echo "### beat 5"
timed 5 bash -c "grep -E '^(A|C) ' experiments/flatten_control/results/summary.tsv | cut -f1,5,7 > '$T/beat5_flatten.txt' 2>&1
cat experiments/composed_rtl/results/post_repair_summary.txt > '$T/beat5_post_repair.txt' 2>&1
cat experiments/composed_rtl/results/abc_buffered_pair.txt > '$T/beat5_abc_pair.txt' 2>&1"

echo "### beat 6"
timed 6 bash -c "bash tools/verdict_regression.sh > '$T/beat6_verdict.txt' 2>&1
python3 tools/classify_regression.py > '$T/beat6_classify.txt' 2>&1"

echo "### beat 7"
timed 7 bash -c "bash experiments/sdc_integrity/run.sh > '$T/beat7_sdc.txt' 2>&1"

echo "### beat 8"
timed 8 bash -c "column -t -s \$'\t' experiments/slackbench/results/raw.tsv > '$T/beat8_slackbench.txt' 2>&1"

echo
echo "=== widest line per capture, against ${COLUMNS} columns ==="
for f in "$T"/*.txt; do
  case "$f" in *_timing.txt) continue;; esac
  w=$(awk '{ if (length($0) > m) m = length($0) } END { print m+0 }' "$f")
  l=$(wc -l < "$f")
  if [ "$w" -gt "$COLUMNS" ]; then flag="  WRAPS"; else flag=""; fi
  if [ "$l" -eq 0 ]; then flag="$flag  NO OUTPUT"; fi
  printf '%-30s %4d cols  %4d lines%s\n' "$(basename "$f")" "$w" "$l" "$flag"
done
echo
echo "=== measured wall clock per beat ==="
for f in "$T"/beat*_timing.txt; do
  [ -e "$f" ] && printf '  %s\n' "$(cat "$f")"
done
echo
echo "CAPTURE DONE. Now: python3 tools/duration_table.py --write --width ${COLUMNS} --target 292"
