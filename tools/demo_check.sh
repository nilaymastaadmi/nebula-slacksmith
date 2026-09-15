set -u
# Run every command in DEMO.md and check it prints what the script claims.
#
# A demo script whose commands were last run days ago is a liability on stage.
# This runs all of them, including the one live-compute beat, and fails loudly
# if any command exits non-zero or any claimed string is missing.
#
#   usage: bash tools/demo_check.sh
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
PASS=0; FAIL=0
# One scratch tree per run, keyed by PID. These were two fixed paths, each
# wiped with rm -rf at start, so two demo_check runs at once delete each other's
# evidence mid-flight. A check that cannot be run twice at once cannot be used
# to compare two trees, which is the job it was given on 2026-09-12 when a
# verification run from a fresh clone of the remote was run alongside one in the
# working tree, which scored 13 of 15 against the tree's 15. Measured after
# this fix, both run concurrently: 15 pass, 0 fail each (REPORT section 9).
RUN=${DEMO_CHECK_RUN:-$$}
W=$SLACKSMITH_WORK/demo_run/$RUN; rm -rf $W
# Scratch for this script's own output. Previously $HOME, which dumped a dozen
# stray .txt files into the home directory of anyone who ran it.
D=$SLACKSMITH_WORK/demo_check/$RUN; rm -rf $D; mkdir -p $D
echo "scratch: $D"
echo "run dir: $W"


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
python3 tools/bench_size.py > $D/b1.txt 2>&1
cat $D/b1.txt
chk "beat 1 bench_size.py" $D/b1.txt "standard cells instantiated" "flip-flops" "clock domains"

# Cross-check the instantiated count by having Yosys flatten the same fixture
# and counting cells in the file it writes. Direct counts of a real file on
# both sides, no parser inference and no dependence on the wording of any
# Yosys report. A hierarchy-aware count that disagrees with the synthesizer
# is the exact failure this project already made once.
zcat experiments/classifier_regression/v3_bufsize_it3.v.gz > $D/fix.v
yosys -p "read_verilog $D/fix.v; hierarchy -top bench_top; flatten; \
          opt_clean -purge; write_verilog -noattr $D/fix_flat.v" \
      > $D/b1_flatten.log 2>&1
YCELLS=$(grep -cE '^\s*sky130_fd_sc_hd__' $D/fix_flat.v)
YFLOPS=$(grep -cE '^\s*sky130_fd_sc_hd__(dfrtp|dfstp|dfxtp|edfxtp|dlrtp|sdfrtp)' $D/fix_flat.v)
MCELLS=$(grep -oE '^ *[0-9,]+ standard cells instantiated' $D/b1.txt | tr -dc '0-9')
MFLOPS=$(grep -oE '^ *[0-9,]+ flip-flops' $D/b1.txt | tr -dc '0-9')
echo "yosys flatten: $YCELLS cells, $YFLOPS flops   bench_size.py: $MCELLS cells, $MFLOPS flops"
if [ "$YCELLS" = "$MCELLS" ] && [ "$YFLOPS" = "$MFLOPS" ]; then
  echo "CROSSCHECK OK" > $D/b1_cmp.txt
else
  echo "CROSSCHECK MISMATCH yosys=$YCELLS/$YFLOPS mine=$MCELLS/$MFLOPS" > $D/b1_cmp.txt
fi
cat $D/b1_cmp.txt
chk "beat 1 count agrees with yosys flatten" $D/b1_cmp.txt "CROSSCHECK OK"

echo "=== beat 2: the closed loop, live (about two minutes on one core, REPORT 1.1)"
/usr/bin/time -f "%e s" python3 -u tools/slacksmith.py \
  --sdc sdc/bench_top_v2.sdc \
  --liberty $LIBERTY \
  --sta-bin $STA_BIN \
  --clock clk_a --clock clk_b --clock clk_e \
  --expect-sdc-sha 3164f5796363d98c \
  --workdir $W --engine sta > $D/b2.txt 2>&1
tail -12 $D/b2.txt
chk "beat 2 loop closes v2 in 2 iterations" $D/b2.txt \
  "clk_b=-4.957" "FANOUT_DOMINATED" "ALL REPORTED GROUPS MEET"

# G0 refusal, checked rather than asserted: the same registered digest against
# a copy of the SDC with one multicycle line appended, the edit experiments/
# sdc_integrity/ measured as worth +5.179 ns. The loop must stop before timing.
echo "=== G0 refuses a changed SDC (not a beat)"
cp sdc/bench_top_v2.sdc $D/tampered_v2.sdc
echo 'set_multicycle_path 2 -setup -from [get_clocks clk_e] -to [get_clocks clk_e]' >> $D/tampered_v2.sdc
python3 -u tools/slacksmith.py --sdc $D/tampered_v2.sdc --expect-sdc-sha 3164f5796363d98c \
  --liberty $LIBERTY --sta-bin $STA_BIN --clock clk_e \
  --workdir $W.g0 --engine sta > $D/g0.txt 2>&1
echo "exit code $?" >> $D/g0.txt
tail -2 $D/g0.txt
chk "G0 refuses a changed SDC given the registered digest" $D/g0.txt "Refusing to report slack" "exit code 1"

echo "=== beat 3: replay three committed logs"
for f in run_v3_final run_v3_fixed run_v3_flat; do
  python3 tools/show_run.py experiments/closed_loop/$f.jsonl > $D/b3_$f.txt 2>&1
done
chk "beat 3 run_v3_final"  $D/b3_run_v3_final.txt "REVERT    P1" "REVERT    P2" "REVERT    P3"
chk "beat 3 run_v3_fixed"  $D/b3_run_v3_fixed.txt "G5 TOTAL" "REVERT    size" "physical_exhausted"
chk "beat 3 run_v3_flat"   $D/b3_run_v3_flat.txt "clk_a=11.158" "CONFIRM   size" "physical_exhausted"

echo "=== beat 4: registration precedes proposals precedes results"
cat experiments/llm_proposer/PREREGISTRATION.md | head -30 > $D/b4c.txt 2>&1
chk "beat 4 registration file opens with its claim" $D/b4c.txt "before any proposer code or any proposal exists"
git log --diff-filter=A --format='%ad %h %s' --date=short -- \
  experiments/llm_proposer/PREREGISTRATION.md \
  experiments/llm_proposer/proposals/ > $D/b4.txt 2>&1
cat $D/b4.txt
python3 - <<'PY' >> $D/b4.txt 2>&1
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
chk "beat 4 registration ordering" $D/b4.txt "ORDER OK"

# Beat 5 had no section here until 2026-09-13, while
# REPORT section 10 and DEMO.md both said this script runs every command in
# DEMO.md. Its flatten command printed nothing as written (a space where the
# file has a tab), which is exactly what this script exists to catch.
echo "=== beat 5: flatten control, composed RTL after the physical flow, PPA"
grep -P "^(A|C)\t" experiments/flatten_control/results/summary.tsv | cut -f1,5,6 > $D/b5f.txt 2>&1
cat $D/b5f.txt
chk "beat 5 flatten moves clk_a from -13.167 to +9.279" $D/b5f.txt $'A\tclk_a\t-13.167' $'C\tclk_a\t9.279'
cat experiments/composed_rtl/results/post_repair_summary.txt > $D/b5p.txt 2>&1
chk "beat 5 composed vs gold after repair" $D/b5p.txt "repair_gold" "clk_b=5.283" "repair_composed" "clk_b=5.046"
cat experiments/composed_rtl/results/abc_buffered_pair.txt > $D/b5a.txt 2>&1
chk "beat 5 ABC pair is +0.000 on clk_b" $D/b5a.txt "+0.000"
cat experiments/ppa/fmax/results/table.md > $D/b5t.txt 2>&1
chk "beat 5 PPA factor" $D/b5t.txt "3.32x" "1.184x"

echo "=== beat 6: the standing verdict regression"
bash tools/verdict_regression.sh > $D/b6.txt 2>&1
tail -6 $D/b6.txt
chk "beat 6 verdict regression" $D/b6.txt "P4" "A2"

echo "=== gate defect 3 guard (not a beat): parameter overrides are refused"
bash tools/param_guard_regression.sh > $D/pg.txt 2>&1
cat $D/pg.txt
chk "tv80_mcode with a #( override reads CANNOT" $D/pg.txt "CANNOT (parameter override at instantiation"
chk "benchmark modules untouched by the guard" $D/pg.txt "rv32i_core: None" "aes_key_mem: None"
chk "parameters from an included header are refused too" $D/pg.txt \
  "pi_child: tools/fixtures/param_include/pi_top.v" "pi_lone: None"

export D
echo "=== beat 7: the cheat no equivalence checker can catch"
bash experiments/sdc_integrity/run.sh > $D/b7s.txt 2>&1
grep -E "constraint variant|baseline_honest|mcp_whole_clk_e|cell count" $D/b7s.txt
chk "beat 7 one SDC line closes the group" $D/b7s.txt \
  "baseline_honest" "mcp_whole_clk_e" "26958 cells"
python3 - <<'PY' > $D/b7cmp.txt 2>&1
import os, re
t = open(os.environ["D"] + "/b7s.txt", encoding="utf-8", errors="replace").read()
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
cat $D/b7cmp.txt
chk "beat 7 claim still true" $D/b7cmp.txt "BEAT7 OK"

echo "=== beat 8: the exam"
column -t -s $'\t' experiments/slackbench/results/raw.tsv > $D/b8.txt 2>&1
head -3 $D/b8.txt
python3 - <<'PY' > $D/b8cmp.txt 2>&1
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
cat $D/b8cmp.txt
chk "beat 8 claims still true" $D/b8cmp.txt "BEAT8 OK"

echo "=== the interactive demo is built from the logs, and is not stale"
python3 demo/build.py > $D/b9.txt 2>&1
cat $D/b9.txt
chk "demo builds from the logs" $D/b9.txt "5 runs, 6 proposals, 56 benchmark rows"
# A generated page committed alongside its generator can silently go stale: edit
# a log, forget to rebuild, and the demo shows numbers the repo no longer holds.
# Rebuilding must produce no diff against what is committed.
if git diff --quiet -- demo/explorer.html 2>/dev/null; then
  echo "EXPLORER FRESH" > $D/b9d.txt
else
  echo "EXPLORER STALE: demo/explorer.html differs from a rebuild, run demo/build.py" > $D/b9d.txt
fi
cat $D/b9d.txt
chk "committed demo matches a rebuild" $D/b9d.txt "EXPLORER FRESH"
# and the page really carries the counterexample it claims to show
grep -c "ae19f605" demo/explorer.html > $D/b9c.txt 2>&1
chk "demo carries P4's counterexample" $D/b9c.txt "1"

echo "=== classifier regression (not a beat, but the demo cites it)"
python3 tools/classify_regression.py > $D/b7.txt 2>&1
tail -2 $D/b7.txt
chk "classifier regression" $D/b7.txt "5 of 5 fixtures pass"

echo
echo "=== demo check: $PASS pass, $FAIL fail ==="
[ $FAIL -eq 0 ] || exit 1
