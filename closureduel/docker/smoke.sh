#!/usr/bin/env bash
# One design, end to end, inside the container. Phase 3 step 1's gate:
# "verify by running one design end to end inside the container before
# writing anything else."
#
#   docker run --rm -v "$HOME/Projects/Dr_RTL:/designs:ro" closureduel:dev <design>
#
# Mirrors experiments/drrtl_transfer/run_classify.sh (the committed, scored
# flow) for synthesis and register-to-register STA, including every guard it
# carries, so the container's number is comparable to the committed row.
# Prints KEY=VALUE lines, one per measurement, for a caller to diff.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/toolpaths.sh"

DESIGN=${1:?usage: smoke.sh <design>}
DR=${DESIGNS_DIR:-/designs}
W=$(mktemp -d)

# --- the seal, enforced structurally rather than by convention -------------
# Single source of truth: the SEALED map in select_holdout.py.
HOLDOUT=$("$PYTHON" -c "import sys; sys.path.insert(0,'$HERE/../tools'); import select_holdout as s; print(' '.join(s.SEALED))")
[ -n "$HOLDOUT" ] || { echo "BROKEN: holdout list came back empty" >&2; exit 3; }
for h in $HOLDOUT; do
  [ "$DESIGN" = "$h" ] && { echo "REFUSED: $DESIGN is in the sealed holdout (SPEC.md 2.3). No run touches it before v1.0." >&2; exit 4; }
done

# --- design config, from the dataset's own manifest ------------------------
[ -f "$DR/syn_flow/design_all.json" ] || { echo "BROKEN: $DR/syn_flow/design_all.json not found - is Dr_RTL mounted at $DR?" >&2; exit 3; }
read -r TOP CLK EXT < <("$PYTHON" -c "
import json,sys
d=json.load(open('$DR/syn_flow/design_all.json'))
if '$DESIGN' not in d: sys.exit('unknown design: $DESIGN')
top,clk,rst,ext=d['$DESIGN']; print(top,clk,ext)") || exit 3
SRC=$DR/rtl_dataset/$DESIGN.v0.$EXT
[ -s "$SRC" ] || { echo "BROKEN: source missing or empty: $SRC" >&2; exit 3; }

echo "DESIGN=$DESIGN"; echo "TOP=$TOP"; echo "CLK=$CLK"
echo "SRC_SHA256=$(sha256sum "$SRC" | cut -d' ' -f1)"
echo "STA_KIND=$STA_KIND"
echo "LIBERTY_SHA256=$(sha256sum "$LIBERTY" | cut -d' ' -f1)"

# --- dont_use: same exclusion and same non-empty guard as the committed flow
DU=$("$PYTHON" -c "import sys; sys.path.insert(0,'$HERE/../../tools'); import remeasure; print(remeasure.dont_use_flags('$LIBERTY'))")
NDU=$(echo $DU | wc -w)
[ "$NDU" -ge 2 ] || { echo "FATAL: dont_use returned $NDU flags" >&2; exit 3; }

# --- synthesis: run_classify.sh synth(), run 1 flow, no legalization -------
RV="read_verilog"; [ "$EXT" = "sv" ] && RV="read_verilog -sv"
NET=$W/A.v
"$YOSYS" -p "$RV $SRC; hierarchy -check -top $TOP; synth -top $TOP; dfflibmap -liberty $LIBERTY; abc -liberty $LIBERTY $DU; opt_clean -purge; write_verilog -noattr $NET; stat" \
  > "$W/synth.log" 2>&1
if [ ! -s "$NET" ]; then echo "RESULT=SYNTH_FAIL"; tail -20 "$W/synth.log" >&2; exit 1; fi
sed -i -E 's/^(\s*(input|output|inout|wire|reg))\s+signed\s+/\1 /' "$NET"
if grep -qE '^\s*always|^\s*(input|output|inout|wire|reg)\s+signed' "$NET"; then
  echo "RESULT=FLOW_FAIL"; exit 1
fi
echo "MAPPED_CELLS=$(grep -cE 'sky130_fd_sc_hd__' "$NET")"

# --- STA: run_classify.sh sta_r2r(), unchanged ------------------------------
LEF_TCL=""
[ "$STA_KIND" = openroad-embedded ] && LEF_TCL="read_lef $TECH_LEF
read_lef $SC_LEF"
sta_r2r () {  # $1 period $2 out
  cat > "$2.tcl" <<EOF
$LEF_TCL
read_liberty $LIBERTY
read_verilog $NET
link_design $TOP
create_clock -name clk -period $1 [get_ports $CLK]
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -digits 3
EOF
  "$STA" -no_init -no_splash -exit "$2.tcl" > "$2" 2>&1
  if grep -qE 'syntax error' "$2"; then echo READ_FAIL; return; fi
  if grep -qE 'report_checks command failed' "$2"; then return; fi
  # Any other tool error is an instrument failure. The first container run
  # hit "[ERROR ORD-2010]" and, with no branch for it, reported NO_PATH on a
  # design whose register path the host had just measured.
  if grep -qE '^\[ERROR|^Error' "$2"; then echo STA_ERROR; return; fi
  local s
  # Dash FIRST inside the bracket; "[\-0-9.]" aborts POSIX grep.
  s=$(grep -E "(-?[0-9.]+)[[:space:]]+slack \((MET|VIOLATED)\)" "$2" | tail -1 | awk '{print $1}')
  # No error and no slack line is unexplained, so it is a broken instrument,
  # never a design fact. NO_PATH is reserved for the one recognised cause.
  [ -n "$s" ] && echo "$s" || echo STA_ERROR
}

_sta_fail () {  # $1 label $2 report
  echo "RESULT=$1"; echo "--- $2 ---" >&2; tail -20 "$2" >&2; exit 3
}
S1=$(sta_r2r 1000 "$W/loose.rpt")
[ "$S1" = "READ_FAIL" ] && _sta_fail STA_READ_FAIL "$W/loose.rpt"
[ "$S1" = "STA_ERROR" ] && _sta_fail STA_ERROR "$W/loose.rpt"
[ -z "$S1" ] && { echo "RESULT=NO_PATH"; exit 1; }
REQ=$("$PYTHON" -c "print(round(1000.0 - ($S1), 3))")
PER=$("$PYTHON" -c "print(round(0.9 * ($REQ), 3))")
SA=$(sta_r2r "$PER" "$W/tight.rpt")
case "$SA" in
  ""|READ_FAIL|STA_ERROR) _sta_fail "STA_FAIL_TIGHT" "$W/tight.rpt" ;;
esac

echo "REQUIRED_NS=$REQ"
echo "PERIOD_NS=$PER"
echo "SLACK_NS=$SA"
echo "RESULT=OK"
rm -rf "$W"
