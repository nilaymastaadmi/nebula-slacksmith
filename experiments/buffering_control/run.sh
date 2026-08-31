set -u
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
B=$HOME/tools/oss-cad-suite/bin
STA=$(which sta || echo $HOME/tools/OpenSTA/build/sta)
LIB=$HOME/sta_work/sky130hd_tt.lib
[ -s "$LIB" ] || { echo "FATAL: liberty missing at $LIB"; exit 2; }
echo "LIB=$LIB"; echo "STA=$STA"
DU=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure; print(remeasure.dont_use_flags('$LIB'))")
NDU=$(echo $DU | wc -w)
echo "dont_use flag count: $NDU"
# Project rule: a flag-generating function gets an assertion that it is non-empty.
# An empty list here silently reintroduces the lpflow artifact.
[ "$NDU" -ge 2 ] || { echo "FATAL: dont_use returned $NDU flags, expected >=2"; exit 3; }

F=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure, os; print(' '.join(os.path.join('rtl',f) for f in remeasure.BENCH_TOP_FILES))")

W=$HOME/bufexp; rm -rf $W; mkdir -p $W

build () {  # $1=tag  $2=extra abc script or empty
  local tag=$1 sc=$2 abc
  if [ -z "$sc" ]; then abc="abc -liberty $LIB $DU"
  else abc="abc -liberty $LIB $DU -script $sc"; fi
  $B/yosys -p "read_verilog $F; hierarchy -check -top bench_top; synth -top bench_top; \
    dfflibmap -liberty $LIB; $abc; opt_clean -purge; \
    write_verilog -noattr $W/$tag.v; stat" > $W/$tag.log 2>&1
  echo "[$tag] rc=$? cells=$(grep -E '^ +Number of cells' $W/$tag.log | tail -1 | awk '{print $NF}')"
}

time build A ""
SCB='+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put;buffer,-N,16;upsize;dnsize'
time build B "$SCB"

for tag in A B; do
  [ -s $W/$tag.v ] || { echo "[$tag] NO NETLIST"; tail -20 $W/$tag.log; continue; }
  { echo "read_liberty $LIB"; echo "read_verilog $W/$tag.v"; echo "link_design bench_top";
    echo "read_sdc sdc/bench_top_v2.sdc";
    for c in clk_a clk_b clk_e; do
      echo "puts \"---CLOCK:$c---\""
      echo "report_checks -path_delay max -to [get_clocks $c] -group_path_count 1 -digits 3"
    done; } > $W/$tag.tcl
  $STA -no_init -no_splash -exit $W/$tag.tcl > $W/$tag.sta 2>&1
  echo "===== $tag ====="
  grep -E "^---CLOCK|slack \(" $W/$tag.sta
done
echo "=== B critical path head (clk_b) ==="
sed -n '/---CLOCK:clk_b---/,/slack (/p' $W/B.sta | grep -E "Startpoint|Endpoint|^ +[0-9]" | sort -k1 -g -r | head -6
