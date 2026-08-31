set -u
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
STA=$HOME/tools/OpenSTA/build/sta
LIB=$HOME/sta_work/sky130hd_tt.lib
W=$HOME/bufexp
C=$HOME/classify; mkdir -p $C

# The classifier called both violated paths FANOUT_DOMINATED. That is either
# a true statement about this design or a classifier that cannot say anything
# else. This distinguishes the two: take the BUFFERED netlist, where the
# fanout has already been repaired, and tighten the clock until it violates
# again. If the classifier still says FANOUT_DOMINATED it is degenerate. If it
# says DEPTH_DOMINATED it is discriminating, and the buffered design's
# remaining problem is genuine logic depth.
sed -e 's/^set PERIOD_B .*/set PERIOD_B 6.0/' sdc/bench_top_v2.sdc > $C/tight.sdc 2>/dev/null || true
# The SDC is literal, so rewrite the create_clock periods directly.
python3 - <<'PY'
import re, os
src = open("sdc/bench_top_v2.sdc").read()
def shrink(m):
    return m.group(1) + str(round(float(m.group(2)) / 6.0, 3)) + m.group(3)
out = re.sub(r"(-period\s+)([0-9.]+)(\s|$)", shrink, src, flags=re.M)
open(os.path.expanduser("~/classify/tight.sdc"), "w").write(out)
print("periods divided by 6; create_clock lines:")
for l in out.splitlines():
    if "create_clock" in l or "create_generated_clock" in l:
        print("   ", l.strip()[:100])
PY

for c in clk_b clk_a; do
  { echo "read_liberty $LIB"; echo "read_verilog $W/B.v"; echo "link_design bench_top";
    echo "read_sdc $C/tight.sdc";
    echo "report_checks -path_delay max -to [get_clocks $c] -group_path_count 1 -digits 3"; } > $C/tight_$c.tcl
  $STA -no_init -no_splash -exit $C/tight_$c.tcl > $C/tight_$c.rpt 2>&1
  echo
  echo "########## BUFFERED netlist, period/6, $c ##########"
  python3 tools/classify_path.py --report $C/tight_$c.rpt --netlist $W/B.v
done
