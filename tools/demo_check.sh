set -u
# Run every command in DEMO.md and check it prints what the script claims.
#
# A demo script whose commands were last run days ago is a liability on stage.
# This runs all of them, including the one live-compute beat, and fails loudly
# if any command exits non-zero or any claimed string is missing.
#
#   usage: bash tools/demo_check.sh
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
PASS=0; FAIL=0
W=$HOME/demo_run; rm -rf $W

chk () {  # $1 label, $2 file to search, $3.. expected substrings
  local label=$1 f=$2; shift 2
  local bad=0
  for want in "$@"; do
    grep -qF -- "$want" "$f" || { echo "    MISSING: $want"; bad=1; }
  done
  if [ $bad -eq 0 ]; then echo "  PASS  $label"; PASS=$((PASS+1));
  else echo "  FAIL  $label"; FAIL=$((FAIL+1)); fi
}

echo "=== beat 1: the benchmark"
python3 tools/bench_size.py > $HOME/b1.txt 2>&1
cat $HOME/b1.txt
chk "beat 1 bench_size.py" $HOME/b1.txt "standard cells instantiated" "flip-flops" "clock domains"

# Cross-check the instantiated count by having Yosys flatten the same fixture
# and counting cells in the file it writes. Direct counts of a real file on
# both sides, no parser inference and no dependence on the wording of any
# Yosys report. A hierarchy-aware count that disagrees with the synthesizer
# is the exact failure this project already made once.
zcat experiments/classifier_regression/v3_bufsize_it3.v.gz > $HOME/fix.v
yosys -p "read_verilog $HOME/fix.v; hierarchy -top bench_top; flatten; \
          opt_clean -purge; write_verilog -noattr $HOME/fix_flat.v" \
      > $HOME/b1_flatten.log 2>&1
YCELLS=$(grep -cE '^\s*sky130_fd_sc_hd__' $HOME/fix_flat.v)
YFLOPS=$(grep -cE '^\s*sky130_fd_sc_hd__(dfrtp|dfstp|dfxtp|edfxtp|dlrtp|sdfrtp)' $HOME/fix_flat.v)
MCELLS=$(grep -oE '^ *[0-9,]+ standard cells instantiated' $HOME/b1.txt | tr -dc '0-9')
MFLOPS=$(grep -oE '^ *[0-9,]+ flip-flops' $HOME/b1.txt | tr -dc '0-9')
echo "yosys flatten: $YCELLS cells, $YFLOPS flops   bench_size.py: $MCELLS cells, $MFLOPS flops"
if [ "$YCELLS" = "$MCELLS" ] && [ "$YFLOPS" = "$MFLOPS" ]; then
  echo "CROSSCHECK OK" > $HOME/b1_cmp.txt
else
  echo "CROSSCHECK MISMATCH yosys=$YCELLS/$YFLOPS mine=$MCELLS/$MFLOPS" > $HOME/b1_cmp.txt
fi
cat $HOME/b1_cmp.txt
chk "beat 1 count agrees with yosys flatten" $HOME/b1_cmp.txt "CROSSCHECK OK"

echo "=== beat 2: the closed loop, live (this is the 60 s of compute)"
/usr/bin/time -f "%e s" python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v2.sdc \
  --liberty $HOME/sta_work/sky130hd_tt.lib \
  --sta-bin $HOME/tools/OpenSTA/build/sta \
  --clock clk_a --clock clk_b --clock clk_e \
  --workdir $W --engine sta > $HOME/b2.txt 2>&1
tail -12 $HOME/b2.txt
chk "beat 2 loop closes v2 in 2 iterations" $HOME/b2.txt \
  "clk_b=-4.957" "FANOUT_DOMINATED" "ALL REPORTED GROUPS MEET"

echo "=== beat 3: replay three committed logs"
for f in run_v3_final run_v3_fixed run_v3_flat; do
  python3 tools/show_run.py experiments/closed_loop/$f.jsonl > $HOME/b3_$f.txt 2>&1
done
chk "beat 3 run_v3_final"  $HOME/b3_run_v3_final.txt "REVERT    P1" "REVERT    P2" "REVERT    P3"
chk "beat 3 run_v3_fixed"  $HOME/b3_run_v3_fixed.txt "G5 TOTAL" "REVERT    size" "physical_exhausted"
chk "beat 3 run_v3_flat"   $HOME/b3_run_v3_flat.txt "clk_a=11.158" "CONFIRM   size" "physical_exhausted"

echo "=== beat 4: registration precedes proposals precedes results"
git log --diff-filter=A --format='%ad %h %s' --date=short -- \
  experiments/llm_proposer/PREREGISTRATION.md \
  experiments/llm_proposer/proposals/ > $HOME/b4.txt 2>&1
cat $HOME/b4.txt
python3 - <<'PY' >> $HOME/b4.txt 2>&1
import subprocess
def added(path):
    out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%at",
                          "--date=short", "--", path],
                         capture_output=True, text=True).stdout.split()
    return int(out[-1]) if out else None
reg = added("experiments/llm_proposer/PREREGISTRATION.md")
props = added("experiments/llm_proposer/proposals/")
print("ORDER OK" if reg is not None and props is not None and reg <= props
      else f"ORDER WRONG reg={reg} props={props}")
PY
chk "beat 4 registration ordering" $HOME/b4.txt "ORDER OK"

echo "=== beat 6: the standing verdict regression"
bash tools/verdict_regression.sh > $HOME/b6.txt 2>&1
tail -6 $HOME/b6.txt
chk "beat 6 verdict regression" $HOME/b6.txt "P4" "A2"

echo "=== beat 7: the cheat no equivalence checker can catch"
bash experiments/sdc_integrity/run.sh > $HOME/b7s.txt 2>&1
grep -E "constraint variant|baseline_honest|mcp_whole_clk_e|cell count" $HOME/b7s.txt
chk "beat 7 one SDC line closes the group" $HOME/b7s.txt \
  "baseline_honest" "mcp_whole_clk_e" "26958 cells"
python3 - <<'PY' > $HOME/b7cmp.txt 2>&1
import os, re
t = open(os.path.expanduser("~/b7s.txt"), encoding="utf-8", errors="replace").read()
def row(name):
    m = re.search(rf"^{name}\s+(\S+)\s+(\S+)\s+(\S+)", t, re.M)
    return [float(x) for x in m.groups()] if m else None
h, c = row("baseline_honest"), row("mcp_whole_clk_e")
# the claim the narrator makes: clk_e goes from violated to met on an
# identical netlist, and clk_a/clk_b do not move at all.
ok = (h and c and h[2] < 0 < c[2] and h[0] == c[0] and h[1] == c[1])
print(f"honest {h}  tampered {c}  gain {round(c[2]-h[2],3) if h and c else '?'}")
print("BEAT7 OK" if ok else "BEAT7 CLAIM BROKEN")
PY
cat $HOME/b7cmp.txt
chk "beat 7 claim still true" $HOME/b7cmp.txt "BEAT7 OK"

echo "=== beat 8: the exam"
column -t -s $'\t' experiments/slackbench/results/raw.tsv > $HOME/b8.txt 2>&1
head -3 $HOME/b8.txt
python3 - <<'PY' > $HOME/b8cmp.txt 2>&1
import csv, os
rows = list(csv.DictReader(open("experiments/slackbench/results/raw.tsv",
                                encoding="utf-8"), delimiter="\t"))
def v(case, ck):
    for r in rows:
        if r["case"] == case and r["checker"] == ck:
            return r["verdict"]
# the three claims beat 8 makes out loud
esc = v("STIMULUS-1", "sim_lazy") == "ACCEPT" and v("STIMULUS-1", "sim_aggr") == "ACCEPT"
cannot = sum(1 for r in rows if r["checker"] == "cec" and r["verdict"] == "CANNOT")
false_alarm = v("CDC-2", "cec") == "REJECT" and v("CDC-2", "dsec") == "REJECT"
ours_wrong = sum(1 for r in rows if r["checker"] == "miter_k"
                 and ((r["truth"] == "EQUIVALENT") != (r["verdict"] == "ACCEPT"))
                 and r["verdict"] != "CANNOT")
print(f"escaped both sims: {esc}   cec CANNOT count: {cannot}   "
      f"cec+dsec false alarm on CDC-2: {false_alarm}   induction wrong: {ours_wrong}")
print("BEAT8 OK" if (esc and cannot == 5 and false_alarm and ours_wrong == 2)
      else "BEAT8 CLAIM BROKEN")
PY
cat $HOME/b8cmp.txt
chk "beat 8 claims still true" $HOME/b8cmp.txt "BEAT8 OK"

echo "=== classifier regression (not a beat, but the demo cites it)"
python3 tools/classify_regression.py > $HOME/b7.txt 2>&1
tail -2 $HOME/b7.txt
chk "classifier regression" $HOME/b7.txt "5 of 5 fixtures pass"

echo
echo "=== demo check: $PASS pass, $FAIL fail ==="
[ $FAIL -eq 0 ] || exit 1
