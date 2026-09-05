set -u
# Re-derive every phase-1 verdict with the corrected classifier (2026-09-03,
# see PREREGISTRATION.md amendment 4). Same saved netlist (A.v), same period
# (read back from the saved tight_A.rpt.tcl), one change: report_checks is
# asked for its fanout column and the classifier reads it. Nothing is
# re-synthesized. Writes results_reclassified/<design>/ and a comparison TSV.
#
#   usage: bash experiments/drrtl_transfer/reclassify.sh
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
STA=$STA_BIN
LIB=$LIBERTY
W=$HOME/drrtl_run
RES=experiments/drrtl_transfer/results_reclassified
OLD=experiments/drrtl_transfer/results
mkdir -p $RES

printf "design\told_verdict\told_share\tnew_verdict\tnew_share\ttop_cell\ttop_incr\told_top_fanout\tnew_top_fanout\tnetlist_top_fanout\tdisagreements\n" > $RES/summary.tsv

while IFS=$'\t' read -r name top clk rst ext; do
  d=$W/$name
  [ -f $d/tight_A.rpt.tcl ] || { echo "$name: no tight_A.rpt.tcl (out of scope in phase 1)"; continue; }
  [ -f $OLD/$name/classify.json ] || { echo "$name: no phase-1 classify.json"; continue; }
  sed 's/-group_path_count 1 -digits 3$/-group_path_count 1 -digits 3 -fields {fanout}/' $d/tight_A.rpt.tcl > $d/tight_A.fanout.tcl
  $STA -no_init -no_splash -exit $d/tight_A.fanout.tcl > $d/tight_A.fanout.rpt 2>&1
  python3 tools/classify_path.py --report $d/tight_A.fanout.rpt --netlist $d/A.v --top $top --json > $d/classify_fixed.json 2>$d/classify_fixed.err
  mkdir -p $RES/$name; cp $d/tight_A.fanout.rpt $d/classify_fixed.json $RES/$name/
  python3 - $name $OLD/$name/classify.json $d/classify_fixed.json >> $RES/summary.tsv <<'PY'
import json, sys
name, oldp, newp = sys.argv[1:4]
o = json.load(open(oldp)); n = json.load(open(newp))
ot = (o.get("top_cells") or [{}])[0]; nt = (n.get("top_cells") or [{}])[0]
print("\t".join(str(x) for x in [name, o.get("verdict"), o.get("fanout_delay_share"),
      n.get("verdict"), n.get("fanout_delay_share"), nt.get("cell"), nt.get("incr_ns"),
      ot.get("fanout"), nt.get("fanout"), nt.get("netlist_fanout"), n.get("fanout_disagreements")]))
PY
  echo "$name: $(tail -1 $RES/summary.tsv | cut -f2-5)"
done < $W/designs.tsv

echo; column -t -s $'\t' $RES/summary.tsv 2>/dev/null || cat $RES/summary.tsv
