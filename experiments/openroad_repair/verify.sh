set -u
# Did repair_design change the circuit? Structural check first, then formal.
# repair_design is documented as buffer insertion plus gate resizing, which is
# a claim, not evidence. The ABC buffering control in
# experiments/buffering_control/ got the same treatment.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
Y=$HOME/tools/oss-cad-suite/bin/yosys
LIB=$HOME/sta_work/sky130hd_tt.lib
W=$HOME/or_repair
A=$HOME/bufexp/A.v
R=$W/repaired.v

[ -s "$R" ] || { echo "FATAL: repaired.v missing"; exit 2; }

echo "=== structural comparison ==="
for f in "$A:before" "$R:after"; do
  p=${f%%:*}; t=${f##*:}
  tot=$(grep -cE "sky130_fd_sc_hd__" $p)
  ff=$(grep -coE "sky130_fd_sc_hd__(df|dl)[a-z0-9_]*" $p)
  buf=$(grep -coE "sky130_fd_sc_hd__(buf|clkbuf)_[0-9]+" $p)
  inv=$(grep -coE "sky130_fd_sc_hd__(inv|clkinv)_[0-9]+" $p)
  echo "$t: cell_refs=$tot flops=$ff buf=$buf inv=$inv"
done

echo
echo "=== flop count must be identical: a repair pass adds no state ==="
$Y -qp "read_liberty -lib $LIB; read_verilog $A; hierarchy -top bench_top; flatten; select -count t:sky130_fd_sc_hd__df*" 2>&1 | tail -2
$Y -qp "read_liberty -lib $LIB; read_verilog $R; hierarchy -top bench_top; flatten; select -count t:sky130_fd_sc_hd__df*" 2>&1 | tail -2

echo
echo "=== formal equivalence, flattened both sides ==="
$Y -p "
  read_liberty -lib $LIB
  read_verilog $A
  prep -top bench_top -flatten
  design -stash gold
  read_liberty -lib $LIB
  read_verilog $R
  prep -top bench_top -flatten
  design -stash gate
  design -copy-from gold -as gold bench_top
  design -copy-from gate -as gate bench_top
  equiv_make gold gate equiv
  hierarchy -top equiv
  equiv_struct
  equiv_simple -seq 5
  equiv_induct -seq 5
  equiv_status
" > $W/equiv.log 2>&1
echo "exit: $?"
grep -E "Found [0-9]+ unproven|Proved [0-9]+|equivalent|ERROR" $W/equiv.log | tail -8
