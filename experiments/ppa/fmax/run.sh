#!/bin/bash
# Design-level required period and F_max, per clock, under ONE timing model.
#
# Why this exists: REPORT §8's only frequency number was core-level,
# zero-parasitic, reset false-pathed, and for P6, which is the worst transform
# at design level. That is the most favourable framing available for the least
# useful transform. This re-runs the OpenROAD flow and keeps the FULL path
# reports, so required period is read off the capture clock in the report
# rather than derived from a group WNS whose capture clock is not recorded.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../../tools/env.sh"
O=experiments/ppa/fmax/results; mkdir -p $O
NET=${1:-$HOME/bufexp/A.v}
SDC=${2:-sdc/bench_top_v2.sdc}
bash experiments/openroad_repair/run.sh "$NET" "$SDC" 2>&1 | tee $O/openroad_full.log
echo "exit: $?"
