set -u
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
B=$HOME/tools/oss-cad-suite/bin
LIB=$HOME/sta_work/sky130hd_tt.lib
W=$HOME/bufexp
echo "===== yosys stat, both netlists ====="
for t in A B; do
  echo "--- $t ---"
  $B/yosys -qp "read_liberty -lib $LIB; read_verilog $W/$t.v; stat -top bench_top" 2>&1 \
    | grep -E "Number of cells|Number of wires" | head -2
done
echo
echo "===== formal equivalence: A (gold) vs B (gate) ====="
$B/yosys -p "
  read_liberty -lib $LIB
  read_verilog $W/A.v
  prep -top bench_top -flatten
  design -stash gold
  read_liberty -lib $LIB
  read_verilog $W/B.v
  prep -top bench_top -flatten
  design -stash gate
  design -copy-from gold -as gold bench_top
  design -copy-from gate -as gate bench_top
  equiv_make gold gate equiv
  hierarchy -top equiv
  equiv_simple -seq 3
  equiv_induct -seq 3
  equiv_status -assert
" > $W/equiv.log 2>&1
rc=$?
echo "equiv exit code: $rc"
grep -E "Found [0-9]+ effective|equivalent|unproven|Equivalence check|ERROR" $W/equiv.log | tail -12
