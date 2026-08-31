set -u
# Bounded primary-output equivalence of bench_top before and after
# OpenROAD repair_design.
#
# Two name-based attempts failed for matching reasons, not for circuit
# reasons, and both are reported in NOTES.md rather than discarded:
#   1. repaired.v vs the hierarchical Yosys netlist: equiv_make created 86
#      equivalence points in a 55K-cell design and proved none.
#   2. repaired.v vs OpenROAD's own prerepair.v: equiv_make created 1 point.
#      repair_design splits nets when it inserts 960 buffers, so most internal
#      names do not survive.
#
# So this compares the only names guaranteed stable, the module's own ports,
# with the liberty read as WHITEBOX (-wb) so the standard cells carry logic
# rather than being blackboxes, and hierarchy/flatten instead of prep so the
# blackbox check does not abort first. -ignore_miss_func skips LIBRARY cells
# whose function Yosys cannot derive (dlclkp_1, a clock gate); that is a
# property of the liberty, not of this design.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
W=$HOME/or_miter; rm -rf $W; mkdir -p $W
LIB=$HOME/sta_work/sky130hd_tt.lib

cp $HOME/bufexp/A.v            $W/gold_raw.v
cp $HOME/or_repair/repaired.v  $W/gate_raw.v
cp experiments/openroad_repair/miter_repair.sv $W/
cp $LIB $W/lib.lib

cat > $W/m.sby <<'EOF'
[options]
mode bmc
depth 5
multiclock on

[engines]
smtbmc --keep-going yices

[script]
read_liberty -wb -ignore_miss_func lib.lib
read_verilog gold_raw.v
rename bench_top bench_top_gold
read_verilog gate_raw.v
rename bench_top bench_top_gate
read_verilog -formal miter_repair.sv
hierarchy -top miter_repair
proc
flatten
opt -fast

[files]
lib.lib
gold_raw.v
gate_raw.v
miter_repair.sv
EOF

cd $W
echo "=== bounded miter, depth 5, multiclock, whitebox cells ==="
timeout 3000 sby -f m.sby > $W/sby.out 2>&1
echo "sby exit: $?"
grep -E "DONE|Assert failed|Checking assert|reached|ERROR" $W/sby.out | tail -12
