# Demo script (deliverable 7)

A shot list, not a storyboard. Every command below is real, runs on this
repository, and the expected output is what it actually printed. Target
runtime **5 minutes**. Record the terminal; no slides needed except beat 0.

Total live compute in the demo is about **50 seconds** (beat 2). Everything
else is either instant or replayed from a committed log, so nothing has to be
waited on with the camera running.

---

## Beat 0. The claim, 25 seconds. One slide.

> Every published agentic RTL optimizer that holds a formal gate refuses to
> change latency, because a pipeline stage breaks conventional equivalence.
> We made transforms *typed*, so the declared type picks the proof obligation
> and latency-changing transforms become checkable.
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

Actual output, 2 iterations, **48 to 50 s across two runs on 2026-09-03**,
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
> inside the AES key memory. No RTL rewrite shortens a net's load delay, so
> the tool routed to a physical lever instead of spending an LLM proposal.

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
> fanout. A pass that changes zero lines of RTL beats our best proven
> transform by 11x and closes the design, at 20.2% area.
>
> And every number we published before that was zero-parasitic. With wires,
> the baseline we reported as "+1.333, meets" is actually **−36.7**.

Then the one that is worse for us than any of those. One flag on the
synthesis command, no buffering, no RTL, no placement:

    grep -E "^(A|C) " experiments/flatten_control/results/summary.tsv | cut -f1,5,7

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

## Before recording

    bash tools/demo_check.sh

Runs every command in this file, including beat 2's live compute, and fails
if any exits non-zero or prints something other than what is written above.
A demo script last verified days ago is a liability on stage.

## Recording notes

- Terminal at 110 columns or wider, or the classify lines wrap badly.
- Beat 2 is the only live compute. If the room is slow, pre-run it into a
  file and `cat` it, but say that you are doing so.
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
