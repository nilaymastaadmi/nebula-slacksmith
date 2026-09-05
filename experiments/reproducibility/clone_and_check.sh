#!/bin/bash
# Clone the committed repo to a different name, a different depth, and a
# different filesystem, then run preflight and the full demo from there.
set -u
# Derive the source repo from this script's own location, not from cwd:
# the point of this file is that nothing here depends on where you run it.
SRC=${SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}
DST=$HOME/repro/some-other-name

rm -rf "$HOME/repro"; mkdir -p "$HOME/repro"
git clone -q "$SRC" "$DST" || { echo "CLONE FAILED"; exit 1; }
cd "$DST" || exit 1
echo "cloned to: $(pwd)"
echo "HEAD: $(git log --oneline -1)"
echo "line endings: $(file tools/demo_check.sh | sed 's/.*: //')"
echo

echo "=== preflight ==="
bash tools/preflight.sh; echo "preflight exit: $?"
echo
echo "=== the demo, from the clone ==="
bash tools/demo_check.sh; echo "DEMO EXIT: $?"
echo
echo "=== liberty substitution ==="
bash tools/liberty_equivalence.sh; echo "LIBEQ EXIT: $?"
