#!/bin/bash
# G7 run 3: crossings declared per amendment 2, depth AND Hamming, with the
# property injected into the module that owns the crossing net.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=$SLACKSMITH_WORK/cdc3; rm -rf $W; mkdir -p $W

run () {  # $1 case  $2 side  $3 top  $4 crossing net  $5 clk
  echo "================= $1 / $2   crossing=$4 ================="
  python3 tools/cdc_check.py \
    --top "$3" --crossing "$4" --rst rst_n --hamming --ham-depth 14 \
    --ham-clock "$5" --workdir "$W/$1_$2" \
    "experiments/slackbench/cases/$1/$2.v"
  echo "exit: $?"
  echo
}

run CDC-1 gold sb_cdc flag_src clk_dst
run CDC-1 gate sb_cdc flag_src clk_dst
run CDC-2 gold sb_ptr gray     clk
run CDC-2 gate sb_ptr bin      clk

echo "=== the instrumented source that was actually checked, CDC-2 gate ==="
sed -n '/injected by tools/,/^  \/\/ ---------/p' \
  "$W/CDC-2_gate/ham_bin/src_instrumented/gate.v" 2>/dev/null | head -22
