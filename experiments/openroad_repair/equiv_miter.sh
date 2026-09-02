set -u
# Bounded primary-output equivalence of bench_top before and after
# OpenROAD repair_design, using REAL functional cell models.
#
# Three earlier attempts failed for tooling reasons, all recorded in NOTES.md:
#   1. equiv_make against the hierarchical Yosys netlist: 86 equivalence
#      points across a 55K-cell design, 0 proved.
#   2. equiv_make against OpenROAD's own prerepair.v: 1 point. repair_design
#      splits nets when it inserts 960 buffers, so internal names do not
#      survive and a name-based matcher has nothing to match.
#   3. bounded miter with `read_liberty -wb`: liberty-derived cells stay
#      blackbox/whitebox and never inline, so there is no logic to reason
#      about.
#
# The fix for (3) is to stop deriving models from the liberty. oss-cad-suite
# ships real sky130 functional models with its own EQY example, together with
# formal_pdk_proc.py, which is the preprocessing step EQY itself uses to make
# them formal-friendly. Coverage was checked before relying on it: 79 of 79
# cell types in A.v and 220 of 220 in repaired.v are defined by those models,
# zero missing.
#
# async2sync is in the script because this design's flops are all
# asynchronously reset, and it is what the upstream EQY example does too.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
EX=$HOME/tools/oss-cad-suite/examples/eqy/spm
W=$HOME/or_miter; rm -rf $W; mkdir -p $W

DEPTH=${1:-4}

cp $HOME/bufexp/A.v            $W/gold_raw.v
cp $HOME/or_repair/repaired.v  $W/gate_raw.v
cp experiments/openroad_repair/miter_repair.sv $W/
cp $EX/primitives.v $EX/sky130_fd_sc_hd.v $EX/formal_pdk_proc.py $W/

cd $W
echo "=== preprocessing sky130 cell models the way EQY does ==="
python3 formal_pdk_proc.py primitives.v sky130_fd_sc_hd.v -o formal_pdk.v
[ -s formal_pdk.v ] || { echo "FATAL: formal_pdk.v not produced"; exit 2; }
echo "formal_pdk.v: $(stat -c%s formal_pdk.v) bytes, $(grep -c '^module ' formal_pdk.v) modules"

cat > m.sby <<EOF
[options]
mode bmc
depth $DEPTH
multiclock on

[engines]
smtbmc --keep-going bitwuzla

[script]
read -sv formal_pdk.v
read_verilog gold_raw.v
rename bench_top bench_top_gold
read_verilog gate_raw.v
rename bench_top bench_top_gate
read_verilog -formal miter_repair.sv
hierarchy -check -top miter_repair
prep -top miter_repair
async2sync
opt -fast

[files]
formal_pdk.v
gold_raw.v
gate_raw.v
miter_repair.sv
EOF

echo "=== bounded miter, depth $DEPTH, multiclock, real cell models ==="
# sby puts each engine in its own process group, so `timeout` killing sby
# leaves yosys-smtbmc running. Attempt 4 orphaned a bitwuzla solver for over
# an hour that way. Run sby in its own session and kill the whole session on
# timeout, which is what tools/run_proof.py already does.
setsid bash -c 'exec sby -f m.sby' > sby.out 2>&1 &
SBY_PID=$!
SID=$(ps -o sid= -p $SBY_PID | tr -d ' ')
( sleep 3000; pkill -9 -s "$SID" >/dev/null 2>&1 ) &
WATCH=$!
wait $SBY_PID; RC=$?
kill $WATCH >/dev/null 2>&1 || true
pkill -9 -s "$SID" >/dev/null 2>&1 || true
echo "sby exit: $RC (137 = killed at the 3000 s wall)"
grep -E "DONE|Assert failed|Checking assert|reached|ERROR|Status" sby.out | tail -14
