#!/bin/bash
# Rebuild the composed variant from the three proven transforms and the gold
# file, and fail if it differs from the committed one.
#
# The composition is a three-way merge with the GOLD file as the common
# ancestor, not a hand edit. That matters: a hand-merged file is a fourth
# transform nobody proved, and the point of this experiment is to compose the
# three that were proven, not to write a new one.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/composed_rtl
T=$SLACKSMITH_WORK/compose; rm -rf "$T"; mkdir -p "$T"

GOLD=rtl/aes/aes_key_mem.v
A4=experiments/llm_proposer_aes/proposals/aes_key_mem_A4.v
O2=experiments/missing_classes/aes_key_mem_O2.v
O1=experiments/cli_backend/results/run1/O1_aes_key_mem.v

for f in "$GOLD" "$A4" "$O2" "$O1"; do
  [ -s "$f" ] || { echo "FATAL: missing $f"; exit 2; }
done

cp "$A4" "$T/step1.v"
git merge-file -p "$T/step1.v" "$GOLD" "$O2" > "$T/step2.v" || { echo "FATAL: A4+O2 conflicted"; exit 3; }
git merge-file -p "$T/step2.v" "$GOLD" "$O1" > "$T/step3.v" || { echo "FATAL: (A4+O2)+O1 conflicted"; exit 3; }

if grep -q '<<<<<<<' "$T/step3.v"; then
  echo "FATAL: conflict markers in the merged file"; exit 3
fi

echo "gold     : $(wc -l < "$GOLD") lines"
echo "composed : $(wc -l < "$T/step3.v") lines"

if [ -f "$D/aes_key_mem_composed.v" ]; then
  if diff -q "$D/aes_key_mem_composed.v" "$T/step3.v" > /dev/null; then
    echo "COMPOSE OK: committed file matches a rebuild from the three sources"
  else
    echo "COMPOSE MISMATCH: the committed file is not what the three sources merge to"
    diff -u "$D/aes_key_mem_composed.v" "$T/step3.v" | head -40
    exit 4
  fi
else
  cp "$T/step3.v" "$D/aes_key_mem_composed.v"
  echo "wrote $D/aes_key_mem_composed.v"
fi
