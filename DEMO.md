# Demo script (deliverable 7)

A shot list, not a storyboard. Every command below is real, runs on this
repository, and the expected output is what it actually printed. Target
runtime **5 minutes**. Record the terminal; no slides needed except beat 0.

Live compute in the demo is beat 2's loop, **83.9 to 152.7 s** across five runs
(`experiments/loop_runtime/`), plus beat 1's Yosys cross-check and beat 6's
verdict regression (`demo/PHASE1_CUT.md`, finding 8). All three are pre-run and
played back; everything else is instant or replayed from a committed log, so
nothing has to be waited on with the camera running.

---

## Beat 0. The claim, 25 seconds. One slide.

> We found no published agentic RTL optimizer that both changes latency and
> discharges a formal obligation for it, because a pipeline stage breaks
> conventional equivalence. Four neighbours come close and the report names
> them. We made transforms *typed*, so the declared type picks the proof
> obligation and latency-changing transforms become checkable.
>
> Then we measured whether the LLM half actually works. It fails two ways.

Do not oversell here. The measurements are the demo.

---

## Beat 1. The benchmark, 20 seconds.

    python3 tools/bench_size.py

Prints, from a committed netlist fixture:

    48,616 standard cells instantiated under bench_top
     8,274 flip-flops
    30,264 cells written in the netlist text across 25 modules (each module
           body once; AES is instantiated twice)
         5 clock domains, 5 in-RTL generated clocks, including odd /3 and /5
     6,639 lines of RTL across 32 files

Say: five asynchronous clock domains, each with its own async reset and its
own in-RTL generated clock including odd /3 and /5 dividers, gray-code async
FIFOs on every multi-bit crossing, an RV32I core and two AES-128 cores. Not
a toy.

The third line is there on purpose. A hierarchical netlist writes each module
once however often it is instantiated, and this design instantiates AES
twice, so counting cells in the file text undercounts it by 18,352. We made
that mistake once. `tools/demo_check.sh` has Yosys flatten the same fixture
and counts cells in the file Yosys writes; the two agree exactly (48,616
cells, 8,274 flops) and the check fails if they ever stop agreeing.

The v2 benchmark that §4 of the report describes is **55,413** cells; the
fixture here is the later buffered-and-sized netlist, which is why this
prints a different number. Quote the one on screen.

---

## Beat 2. The closed loop, one command, 50 seconds. **This is the demo.**

    python3 tools/slacksmith.py \
      --sdc sdc/bench_top_v2.sdc \
      --liberty ~/sta_work/sky130hd_tt.lib \
      --sta-bin ~/tools/OpenSTA/build/sta \
      --clock clk_a --clock clk_b --clock clk_e \
      --workdir ~/demo_run --engine sta

It runs the default `--lever-policy blunt`, which applies `buffer; upsize;
dnsize` as one step; `experiments/closure_cost/` measured `buffer` alone meeting
more groups, and the default is unchanged before submission.

Actual output, 2 iterations, **83.9 to 152.7 s across five runs on 2026-09-13**
(`experiments/loop_runtime/`; 48 to 50 s on 2026-09-03),
exactly as the command prints it:

    === iteration 1 ===
    measure: clk_a=1.333  clk_b=-4.957  clk_e=-4.957
    classify clk_b: FANOUT_DOMINATED (fanout share 0.9139) -> physical
    apply: physical lever (abc buffer/upsize/dnsize)

    === iteration 2 ===
    measure: clk_a=12.784  clk_b=12.6  clk_e=20.394
    ALL REPORTED GROUPS MEET. stopping.

`tools/show_run.py ~/demo_run/decisions.jsonl` replays the same run with the
per-cell evidence under each classify line, which is the better thing to
point at:

    it1  CLASSIFY  clk_b: FANOUT_DOMINATED (fanout share 0.9139, 30.602 ns over 9 cells) -> physical
                    21.029 ns  sky130_fd_sc_hd__nor4_1  fanout=300  u_aes_b/u_core/keymem/_07883_

Say, pointing at the classify line:

> It did not guess. 91% of that path's delay is in cells driving 32 or more
> loads, and the worst single cell burns 21 nanoseconds driving **300** loads
> inside the AES key memory. Physical buffering is built to fix a net's load
> and RTL is not, so the tool routed to a physical lever instead of spending
> an LLM proposal.

Earlier cuts of this beat said *no RTL rewrite shortens a net's load delay*.
That absolute is **retracted**: on this same 91.4%-fanout path an FSM
re-encoding bought +3.185 ns and an unattended fanout split +1.414 ns
(REPORT §1, §7.6, §7.7). Do not say it on camera.

---

## Beat 3. Why that matters, 40 seconds. Replay a committed log.

    python3 tools/show_run.py experiments/closed_loop/run_v3_final.jsonl

Under a target the flow cannot already clear, both branches fire. In this
log the classifier of the day called the residual `clk_a` violation
DEPTH_DOMINATED and routed it to RTL (corrected 2026-09-03: the path is
MIXED at 0.428, see below), and then:

    it2  GATE    P1 (operator_sharing_addsub) G4=PROVEN
    it3  REVERT  P1: clk_a -1.716 -> -2.026, G5_no_improvement
    it5  REVERT  P2: clk_a -1.716 -> -2.201, G5_no_improvement
    it7  REVERT  P3: clk_a -1.716 -> -2.02,  G5_no_improvement

Then the run that refuses a physical step, 20 seconds:

    python3 tools/show_run.py experiments/closed_loop/run_v3_fixed.jsonl

    it2  MEASURE   clk_a=1.75    clk_b=5.556  clk_e=-1.444   physical=buffer   total=-1.444
    it2  CLASSIFY  clk_e: MIXED (fanout share 0.2864, 6.816 ns over 15 cells) -> physical
    it3  MEASURE   clk_a=-1.716  clk_b=5.6    clk_e=-0.606   physical=buffer+size  total=-2.322
    it3  G5 TOTAL  -1.444 -> -2.322 (not improved)
    it3  REVERT    size: clk_e -1.444 -> -0.606, G5_total_no_improvement
    it4  STOP      physical_exhausted

Say: sizing gained 0.838 ns on the group it was aimed at and cost `clk_a`
3.466 ns. The earlier bar, which only looked at the target group, kept it. This
one measures every group and reverted it: 4 iterations instead of 8, 1 group
violating instead of 2, and it says so when it runs out of levers. Then the
flat flow, 10 seconds: `python3 tools/show_run.py
experiments/closed_loop/run_v3_flat.jsonl`, 3 iterations, both physical
steps confirmed, `clk_a` +11.158, `clk_b` +5.665, `clk_e` −0.319. If asked
why the earlier logs say DEPTH_DOMINATED here: the classifier was
undercounting fanout across module boundaries, we found it by reading our
own log against the OpenSTA report, and the correction is in the repo with
the wrong logs kept.

Say:

> Three transforms, all formally proven correct, all making the number worse.
> The loop reverted all three by itself. Passing a formal gate means correct.
> It does not mean useful, and those are separate bars.

---

## Beat 4. The refutation, 60 seconds. The single best beat.

    cat experiments/llm_proposer/PREREGISTRATION.md | head -30
    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/llm_proposer/PREREGISTRATION.md \
      experiments/llm_proposer/proposals/

Show that the registration commit precedes the proposals commit, which
precedes every result. Then:

> P4 rewrote the ALU's shift arms into one ternary. It parses, elaborates,
> passes every precondition, and saves 208 cells. It is also wrong: a
> conditional operator's signedness comes from both branches, so pairing a
> signed branch with an unsigned one silently degrades `>>>` to a logical
> shift and SRA breaks for every negative operand.
>
> The file it edited carries a six-line comment warning about exactly this,
> ten lines above the code it changed.

| checker | verdict |
|---|---|
| EQY formal | **CAUGHT** in 46 s, counterexample `a=ae19f605, shamt=7` |
| the design's own shipped firmware, 400 cycles | **MISSED** |
| 20,000 random instruction words | **MISSED** |
| directed SRAI on a negative operand | CAUGHT |

> The verdict tracks stimulus quality, not bug severity. Every one of those
> simulation gates is what a real agentic RTL tool ships with today.

---

## Beat 5. The lever nobody measured, 45 seconds.

| lever, same clock group, same SDC | clk_b gain | changes RTL? | parasitics? |
|---|---|---|---|
| best LLM RTL transform, batch 1 | +0.485 | yes | no |
| best LLM RTL transform, batch 2 | +4.925 | yes | no |
| ABC buffering control | +17.557 | no | no |
| **OpenROAD `repair_design`** | **+55.805** | **no** | **yes** |

> We spent the project optimizing RTL on paths that were 59 to 91 percent
> fanout. Like for like, one SDC and one timing model, on clk_b: our best
> RTL transform buys +3.185 ns while the physical lever takes the same group
> from −18.957 to +5.6 in the same run. About one eighth.

The rows above mix SDC versions and parasitic regimes, which is why the
`parasitics?` column exists and why the spoken ratio is the in-model pair,
not 55.805 over 4.925. Quoting across the table gives anything from a third
to a seventeenth (REPORT §1).
>
> And every number we published before that was zero-parasitic. With wires,
> the baseline we reported as "+1.333, meets" is actually **−36.7**.

Then the one that is worse for us than any of those. One flag on the
synthesis command, no buffering, no RTL, no placement:

    grep -P "^(A|C)\t" experiments/flatten_control/results/summary.tsv | cut -f1,5,6

> Synthesizing flat instead of hierarchically moves `clk_a` by **+22.4 ns**.
> Across the module boundary the mapper can see that our own wrapper ties
> twenty instruction bits together, and it deletes the decode logic we had
> been trying to optimize. The 387-load net we were chasing does not get
> buffered. It stops existing.
>
> Every number before that slide is a hierarchical-flow number, and they are
> all labelled. On this benchmark the flow was a bigger lever than anything
> we proposed.

---

Then the composed result, the report's headline negative, replayed from a
committed file (added 2026-09-12; the video must not tell a cleaner story than
the report):

    cat experiments/composed_rtl/results/post_repair_summary.txt
    cat experiments/composed_rtl/results/abc_buffered_pair.txt

> We composed our three proven transforms into one file. Before wires they are
> worth 5.165 nanoseconds together, fifty-four percent of the sum of the parts.
> After the ABC buffering lever, zero. After repair_design, minus 0.237 against
> a 0.24 nanosecond floor from five perturbed netlists. The classifier had
> routed that path to buffering before any of it was measured, and it was right.

Point at the `composed` row against `gold`, and at the `+0.000` on clk_b in the
ABC pair. Do not say "worse": amendment 2 made R38 VOID, not WRONG
(`experiments/composed_rtl/NOTES.md`).

---

## Beat 6. What we caught in ourselves, 40 seconds.

> Six defects, all found by running things rather than reading them.
> Two worth naming. Our own gate reported a solver **timeout** as a
> **refutation**, because EQY prints the same line for both. We only noticed
> because a partition failed while all 128 partitions feeding it had passed.

    bash tools/verdict_regression.sh

> That is now a standing regression: P4 must read REFUTED, A2 must read
> UNRESOLVED, and any change that moves either is wrong.

> The second is worse. Our path classifier undercounted fanout across module
> boundaries. Its own docstring named the tell, "a 6.762 nanosecond cell at
> fanout 1", and that exact number sat in every log we produced for three
> days under a DEPTH verdict. The cell drives 387 loads.

    python3 tools/classify_regression.py

> Five fixtures, checked cell by cell against OpenSTA's own fanout column,
> zero disagreements above the threshold. Every wrong log is still in the
> repository next to the corrected verdicts.

Close on:

> The gate is not the contribution. The measurement is. We can tell you which
> of our numbers we trust and exactly why.

---

## Beat 7. The cheat no equivalence checker can catch, 30 seconds.

    bash experiments/sdc_integrity/run.sh

One netlist, 26,958 cells, identical in every row. Only the constraints vary.

    baseline_honest           11.158     5.665    -0.319
    mcp_whole_clk_e           11.158     5.665     4.860

> One line of SDC closes the group. It is worth 5.179 nanoseconds, for
> changing nothing at all. (The comparison to our best proven RTL transform
> is withdrawn, REPORT §5.2: different fixtures.) Every equivalence checker we own would call these two
> designs equivalent, correctly, because they are the same file. Proof of
> equivalence is necessary and nowhere near sufficient for believing a
> timing number.
>
> So the loop hashes the SDC, counts its timing exceptions, and refuses to
> report slack measured under constraints that are not the registered ones.

---

## Beat 8. We built the exam, 45 seconds.

    column -t -s $'\t' experiments/slackbench/results/raw.tsv

> Eight transform pairs with ground truth we declared before running any
> checker, each built to defeat a specific checker's abstraction. One wrong
> transform survived forty thousand simulated cycles. Combinational and
> sequential equivalence checking could not even express five of the eight
> questions. Two checkers confidently rejected a pair that is provably
> equivalent.
>
> And ours declines rather than answers on one case. An induction-only
> shortcut in this harness was wrong twice; the shipped gate discharges with
> BMC plus PDR and scores seven of eight. We registered in advance that it
> should not sweep its own suite, because a benchmark its author aces tells
> you about the benchmark, not the tool.

---

## Before recording

    bash tools/demo_check.sh

Runs every command in this file, including beat 2's live compute, and fails
if any exits non-zero or prints something other than what is written above.
A demo script last verified days ago is a liability on stage.

## Recording notes

- Terminal at 165 columns and 40 rows or larger. 110 was measured too narrow
  for the classify lines on 2026-09-13 (`demo/PHASE1_CUT.md`, finding 4).
- Beats 1, 2 and 6 are live compute, not only beat 2 (`demo/PHASE1_CUT.md`,
  finding 8). Pre-run all three into files and play them back, and say so
  wherever the narration implies the output is live or fast.
- Do not read the tables aloud. Point at one number per table.
- If asked "did you close the design", the honest answer is: **under the v2
  target, yes, at the placement level with `repair_design`, and
  `experiments/openroad_cts/` shows what a clock tree does to that. Under
  the tighter v3 target, no: two of three groups close and `clk_e` ends
  0.319 ns short zero-parasitic, 0.952 ns short with placement parasitics.
  We know exactly which net it is and that our SDC never set a max-fanout
  limit for `repair_design` to repair against. We did not add one, because
  changing a frozen constraint to improve our own number is the thing the
  freeze exists to prevent.**
