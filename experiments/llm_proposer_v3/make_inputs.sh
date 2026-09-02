set -u
# Build the proposer's INPUT for batch 3 and commit it before any proposal
# exists. The target is the post-buffering clk_a path under SDC v3, which the
# closed loop classified DEPTH_DOMINATED at fanout share 0.000: the one place
# on this benchmark where an RTL transform has something to bite on.
#
# Batches 1 and 2 handed the proposer a raw OpenSTA dump. Batch 3 hands it
# the classified report (tools/classify_path.py --json) plus the full path,
# so the experiment can ask whether the router's output is actionable for a
# model and not only for a person.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
STA=$HOME/tools/OpenSTA/build/sta
LIB=$HOME/sta_work/sky130hd_tt.lib
OUT=experiments/llm_proposer_v3/inputs
mkdir -p $OUT

# The buffered, no-RTL-substitution netlist is what the loop measured at
# iteration 2 (and again at 4, 6, 8: every revert restored exactly -1.716).
NET=$HOME/slacksmith_v3b/it8/mapped.v
[ -s "$NET" ] || NET=$HOME/slacksmith_v3b/it2/mapped.v
[ -s "$NET" ] || { echo "FATAL: buffered v3 netlist not found"; exit 2; }
echo "netlist: $NET"
cp $NET $OUT/target_buffered_v3.v

cat > $OUT/q.tcl <<EOF
read_liberty $LIB
read_verilog $NET
link_design bench_top
read_sdc sdc/bench_top_v3.sdc
puts "---CLOCK:clk_a---"
report_checks -path_delay max -to [get_clocks clk_a] -group_path_count 1 -digits 3
puts "---SUMMARY---"
report_wns
report_tns
EOF
$STA -no_init -no_splash -exit $OUT/q.tcl > $OUT/path_report_clk_a.txt 2>&1
echo "slack line: $(grep -E 'slack \(' $OUT/path_report_clk_a.txt | tail -1)"

python3 tools/classify_path.py --report $OUT/path_report_clk_a.txt \
  --netlist $NET --json > $OUT/classify_clk_a.json
python3 - <<'PY'
import json
d = json.load(open("experiments/llm_proposer_v3/inputs/classify_clk_a.json"))
print(f"verdict={d['verdict']} share={d['fanout_delay_share']} "
      f"delay={d['path_delay_ns']} cells={d['cells_on_path']}")
for c in d["top_cells"]:
    print(f"  {c['incr_ns']:>7} ns  {c['cell']:<28} fanout={c['fanout']}  "
          f"{c['inst']}  [{c['module']}]")
PY
rm -f $OUT/q.tcl
ls -la $OUT
