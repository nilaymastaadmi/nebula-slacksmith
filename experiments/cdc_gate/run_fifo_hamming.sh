#!/bin/bash
# C3: are bench_top's six gray-pointer crossings Hamming safe?
#
# Checked MODULARLY, on async_fifo itself, rather than on the six flattened
# instances in bench_top. After `flatten` the pointers carry hierarchical names
# like u_fifo_a2b.rgray_r, which cannot be referenced as plain identifiers by an
# assertion injected into a module. Proving the property of async_fifo is also
# the stronger claim: it holds for every instantiation, including the three in
# bench_top and any future one, rather than for six particular copies.
#
# No --ham-clock and no --rst. Both are derived per crossing from the flop that
# drives it, because a single global clock override checked rgray_r against
# wclk and returned a confident REFUTED on a correct design. See NOTES.md.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=${1:-$SLACKSMITH_WORK/cdc_fifo}
rm -rf "$W"; mkdir -p "$W"

echo "=== async_fifo, both gray pointers, clocks derived from the design ==="
python3 tools/cdc_check.py \
  --top async_fifo --crossing wgray_r --crossing rgray_r \
  --hamming --ham-module async_fifo --ham-depth 16 --ham-timeout 600 \
  --workdir "$W" \
  rtl/async_fifo.v rtl/sync2ff.v
echo "exit: $?"
