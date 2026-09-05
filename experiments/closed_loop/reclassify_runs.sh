set -u
# Re-derive every classify record of the three v3 closed-loop runs with the
# corrected classifier (2026-09-03). Same saved per-iteration netlist, same
# SDC, report_checks asked for its fanout column. Writes reclassified.tsv.
#
#   usage: bash experiments/closed_loop/reclassify_runs.sh
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
STA=$STA_BIN
LIB=$LIBERTY
SDC=/mnt/c/Users/toshn/Projects/slacksmith-benchmark/sdc/bench_top_v3.sdc
OUT=experiments/closed_loop/reclassified.tsv
printf "run\titer\tclock\told_verdict\told_share\tnew_verdict\tnew_share\ttop_cell\ttop_incr\told_top_fanout\tnew_top_fanout\n" > $OUT

for pair in "run_v3_final:$HOME/slacksmith_v3b" "run_v3_verdict:$HOME/slacksmith_v3_verdict" "run_v3_g5total:$HOME/slacksmith_v3_g5total"; do
  run=${pair%%:*}; W=${pair#*:}
  [ -f $W/decisions.jsonl ] || { echo "$run: no decisions.jsonl at $W"; continue; }
  python3 - $W/decisions.jsonl <<'PY' | while IFS=$'\t' read -r it clk ov os ofo; do
import json, sys
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r.get("step") == "classify":
        t = (r.get("top_cells") or [{}])[0]
        print(f"{r['iter']}\t{r['clock']}\t{r['verdict']}\t{r.get('fanout_delay_share')}\t{t.get('fanout')}")
PY
    net=$W/it$it/mapped.v
    [ -f $net ] || { echo "$run it$it: no netlist"; continue; }
    cat > $W/it$it/reclass_$clk.tcl <<EOF
read_liberty $LIB
read_verilog $net
link_design bench_top
read_sdc $SDC
report_checks -path_delay max -to [get_clocks $clk] -group_path_count 1 -digits 3 -fields {fanout}
exit
EOF
    $STA -no_init -no_splash -exit $W/it$it/reclass_$clk.tcl 2>&1 | sed -n '/^Startpoint/,$p' > $W/it$it/reclass_$clk.rpt
    python3 tools/classify_path.py --report $W/it$it/reclass_$clk.rpt --netlist $net --top bench_top --json > $W/it$it/reclass_$clk.json
    python3 - $run $it $clk "$ov" "$os" "$ofo" $W/it$it/reclass_$clk.json >> $OUT <<'PY'
import json, sys
run, it, clk, ov, os_, ofo, p = sys.argv[1:8]
n = json.load(open(p)); t = (n.get("top_cells") or [{}])[0]
print("\t".join(str(x) for x in [run, it, clk, ov, os_, n.get("verdict"), n.get("fanout_delay_share"), t.get("cell"), t.get("incr_ns"), ofo, t.get("fanout")]))
PY
    echo "$run it$it $clk: $ov $os -> $(tail -1 $OUT | cut -f6,7)"
  done
done
echo; column -t -s $'\t' $OUT 2>/dev/null || cat $OUT
