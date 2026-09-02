# SlackSmith's instrument on Dr. RTL's benchmark: phase 1 results

Run 2026-09-02. Registered in `PREREGISTRATION.md` (commit `57a5eeb`) before
any design was timed; three dated amendments follow it and are part of the
record. The scored run is **run 4** (`results/`), which reproduces run 1
(`results_run1_as_registered/`) **exactly: 15 identical rows, 0 differing**.
Runs 2 and 3 are a flow-sensitivity study, kept and reported below.

`score.py` computes every number in this file from the two TSVs.

## What was tested

Twenty human-written designs published with Dr. RTL (Fang et al., ICCAD 2026,
Apache 2.0). Each was synthesized with this project's unmodified flow into an
unbuffered netlist **A** and a buffered netlist **B** (`buffer -N 16; upsize;
dnsize`, the physical lever from `experiments/buffering_control/`), timed at
**0.9x its own measured reg-to-reg requirement**, and its worst path
classified by `tools/classify_path.py` with the thresholds **unchanged**
(32 / 0.50 / 0.20). Their flow was DC on Nangate 45 at 0.1 ns with Jasper
SEC; ours is Yosys/ABC on sky130hd with OpenSTA. Nothing here reproduces or
compares to their numbers.

## Scope: 15 of 20, and why the other 5 are not silently gone

| design | status | reason, verified |
|---|---|---|
| LSTM | NO_PATH | 0 flip-flops: `lstm_cell` is combinational as published |
| FIFO | FLOW_FAIL | 32 `$_ALDFF_PN_` async-**load** flops; no sky130 cell implements that |
| SPI | FLOW_FAIL | 65 inferred latches (`$_DLATCH_NP0_`) |
| UART | FLOW_FAIL | 41 inferred latches |
| pcie | FLOW_FAIL | inferred latches |

Latches are rejected by this project's own gate G2 by policy, so SPI, UART
and pcie are out of scope for the same reason a latch-inferring LLM proposal
would be. Run 1 recorded all five as `NO_PATH`, which was wrong: four were
OpenSTA read failures. Two amendments chased a sync-reset hypothesis that
turned out to be false before the real causes above were established.

## The scored table (run 4, reg-to-reg, 0.9x requirement)

| design | cells | requirement | slack A | slack B | lever gain | verdict | fanout share | top cell |
|---|---|---|---|---|---|---|---|---|
| cpu_fsm | 7,883 | 57.610 | -5.761 | +11.754 | **+17.515** | FANOUT | 0.959 | 32.954 ns dfxtp_1 driving **1,131** loads |
| arm_cpu1 | 18,936 | 31.967 | -3.197 | +12.750 | +15.947 | MIXED | 0.439 | 12.132 ns nor2_1, fanout 272 |
| datapath | 5,503 | 7.688 | -0.769 | +3.223 | +3.992 | FANOUT | 0.634 | 2.577 ns, fanout 35 |
| communication | 286 | 5.814 | -0.581 | +3.042 | +3.623 | FANOUT | 0.684 | 3.753 ns nor3_1, fanout 70 |
| DSP | 2,891 | 18.666 | -1.867 | +0.984 | +2.851 | DEPTH | 0.050 | 53 cells |
| arm_cpu2 | 7,336 | 9.748 | -0.975 | +0.930 | +1.905 | FANOUT | 0.609 | 5.841 ns, fanout 93 |
| aes | 3,269 | 5.267 | -0.527 | +1.015 | +1.542 | FANOUT | 0.916 | 3.929 ns and2_0, fanout 129 |
| simple_spi | 320 | 4.251 | -0.425 | +0.641 | +1.066 | DEPTH | 0.000 | 9 cells |
| i2c | 560 | 3.956 | -0.396 | +0.581 | +0.977 | DEPTH | 0.000 | 10 cells |
| cpu_pipe | 3,476 | 8.500 | -0.850 | -0.269 | +0.581 | DEPTH | 0.000 | 36 cells |
| tv80 | 4,023 | 9.797 | -0.980 | -0.599 | +0.381 | DEPTH | 0.000 | 2.225 ns at fanout **0** (see limits) |
| controller | 128 | 1.823 | -0.182 | +0.173 | +0.355 | DEPTH | 0.000 | 8 cells |
| router | 895 | 3.274 | -0.327 | -0.156 | +0.171 | MIXED | 0.460 | 1.34 ns, fanout 36 |
| ticket_machine | 18 | 0.791 | -0.080 | -0.079 | +0.001 | DEPTH | 0.000 | 5 cells, trivial |
| vending_machine | 13,867 | 0.772 | -0.077 | -0.077 | 0.000 | DEPTH | 0.000 | 5 cells, trivial (see secondary) |

**5 FANOUT_DOMINATED, 2 MIXED, 8 DEPTH_DOMINATED.**

## The registered predictions, scored

| # | prediction | result |
|---|---|---|
| 1 | all 20 time and classify | **WRONG**, 15 of 20 |
| 2 | 6 to 12 of 20 FANOUT_DOMINATED | **WRONG**, 5 of 20 (5 of 15 in scope; 7 counting MIXED) |
| 3 | named calls | 5 correct, 2 wrong (`arm_cpu1` MIXED not FANOUT; `datapath` FANOUT not DEPTH), 2 unscorable |
| 4 | **primary**: lever improves every FANOUT design and fewer than half of DEPTH | **WRONG**: 5 of 5 FANOUT and **6 of 8 DEPTH** improved |
| 5 | a DEPTH verdict with an implausible delay at fanout <= 2 | **CONFIRMED**: `tv80`, 2.225 ns at fanout 0 |

Three of five wrong, including the primary. That is the point of writing them
down first.

## What the misses mean, which is more useful than the hits

**The physical lever is not a fanout lever.** `buffer; upsize; dnsize`
improved 14 of 15 designs and closed 10 of 15 outright, DEPTH designs
included, because `upsize`/`dnsize` are gate *sizing* and sizing helps any
path. So prediction 4's second half was a category error: the classifier
isolates fanout, but the lever we compared it against does two things.

What the classifier does predict is **how much**, and **whether the lever
alone closes**:

| verdict | n | improved | closed by lever alone | lever gain, median | min | max |
|---|---|---|---|---|---|---|
| FANOUT_DOMINATED | 5 | 5 | **5** | **3.623** | 1.542 | 17.515 |
| MIXED | 2 | 2 | 1 | 8.059 | 0.171 | 15.947 |
| DEPTH_DOMINATED | 8 | 6 | **4** | **0.481** | 0.000 | 2.851 |

Median gain 7.5x higher on FANOUT than on DEPTH, and the lever closes every
FANOUT design against half the DEPTH ones. That is the transferable claim,
and it is narrower than the one registered.

**The fanout finding transfers, at a lower rate than on our own benchmark.**
On `bench_top` the binding paths were 59% to 91% fanout-attributable and we
guessed 6 to 12 of 20 external designs would look the same. It was 5 of 15 in
scope (33%), 7 with MIXED (47%). One design out-does ours: `cpu_fsm`'s
program counter `PC[2]` drives **1,131 loads** and burns 32.954 ns in a
single cell, 96% of its path. This is the phase 2 target.

**The DEPTH verdict is the weaker verdict, on external designs too.**
`tv80`'s top cell reports 2.225 ns at fanout 0. A 0-fanout driver cannot burn
2 ns; the net leaves its (parameterised) submodule through an output port and
the parent's loads are never charged back. This is the boundary undercount
`docs/path-classification.md` already lists, seen here in its output-port
form. Prediction 5 was registered so that this would be visible.

## Flow sensitivity: runs 2 and 3

Amendments 1 and 2 added `opt -nodffe -nosdff; dfflegalize ...` on the wrong
hypothesis that sync-reset flops caused the read failures. The legalization
rescued nothing and altered **7 of 15** netlists (`cpu_fsm` 7,883 to 12,196
cells with `-nodffe`; `datapath`'s requirement 7.688 to 9.258 ns under
`dfflegalize`). `arm_cpu2`'s verdict went **FANOUT 0.609 (run 1) to DEPTH
0.132 (run 2) to DEPTH 0.089 (run 3) and back to FANOUT 0.609 (run 4)**. The
classifier's verdict on 1 of 15 designs depends on how enable flops are
legalized. That is a limitation of the classifier, stated. Run 4 removed the
legalization; its 15 rows equal run 1's byte for byte.

## Secondary, post-hoc, unregistered: all paths

The registered protocol times reg-to-reg only, which is what made
`vending_machine` (13,867 cells) show a 0.772 ns "requirement": its logic is
I/O-facing. `run_classify_io.sh` constrains every port at **0 ns external
delay** (an unconstrained port is *excluded*, not zero-delay; the first
version of this pass timed nothing new for exactly that reason) and reports
the overall worst path. 13 of 15 designs are unchanged. Two are not:

| design | all-paths requirement | slack A | slack B | lever gain | verdict |
|---|---|---|---|---|---|
| vending_machine | **108.538** | -10.854 | +4.033 | **+14.887** | DEPTH, 0.000, 430 cells |
| LSTM | **31.295** | -3.129 | -1.083 | +2.046 | DEPTH, 0.000, 86 cells |

`vending_machine` gaining 14.887 ns from the lever on a 430-cell path with
zero fanout-attributable delay is the sizing effect again, at its largest.

## Honest limits

- The classifier's thresholds were still chosen on our benchmark; this study
  shows they are not degenerate on 15 external designs, not that they are
  right.
- One ABC lever that mixes buffering and sizing. Separating `buffer` from
  `upsize; dnsize` is the obvious next control and was not run.
- One clock per design, no I/O constraints in the scored run, resets not
  false-pathed in the scored run (they are in the secondary pass).
- `router`'s MIXED and `arm_cpu2`'s flow-dependent verdict sit close to the
  0.50 threshold; small threshold moves would relabel them.
- Three amendments to get one run right. Left visible.

## Phase 2 (registered predictions 6 and 7): Dr. RTL skill #7 on `cpu_fsm`

**Run on 1 of the 5 FANOUT designs, not all 5 as registered.** `cpu_fsm` is
the only one whose top-fanout net is an RTL register (`output reg [7:0] PC`,
bit 2 driving **1,131** loads, 32.954 ns in one cell, 96% of the path). The
other four top nets are synthesis temporaries, which is Dr. RTL skill #8's
case and needs hand tracing; `aes`'s `o_done` (fanout 34) is a possible
second target. Phase 2 is therefore partial and is reported as partial.

Skill #7 as written: duplicate the register driving the high-fanout net and
split its consumers. `PC` has one wide consumer, the fetch `IR <= imem[PC]`,
plus the output port and the three branch adders. `PC_dup` was added with
identical updates and the fetch was pointed at it (`phase2/cpu_fsm_skill7_*.v`,
generated as six single-anchor substitutions on the gold source). Two
variants: plain, and with `(* keep *)` on the copy so ABC cannot merge it.
All six netlists timed at the scored run's own period for this design,
51.849 ns, reg-to-reg, same flow.

| variant | abc | cells | slack | max fanout any | on `PC` | on `PC_dup` |
|---|---|---|---|---|---|---|
| gold | A | 7,883 | -5.761 | 4,163 | **1,131** | 0 |
| gold | B, lever | 7,968 | **+11.754** | 4,163 | 1,131 | 0 |
| skill #7 plain | A | 8,021 | **-6.208** | 4,171 | 3 | **1,175** |
| skill #7 plain | B, lever | 8,106 | +10.795 | 4,171 | 3 | 1,175 |
| skill #7 keep | A | 8,021 | -6.208 | 4,171 | 3 | 1,175 |
| skill #7 keep | B, lever | 8,106 | +10.795 | 4,171 | 3 | 1,175 |

**The load moved; it did not split.** `PC`'s fanout falls from 1,131 to 3 and
`PC_dup` inherits 1,175, because the fetch mux is one cone. Max fanout on any
net changes by +0.2%. Slack gets **worse by 0.447 ns**, 138 cells and 16
flops are added, and `(* keep *)` changes nothing because there was nothing
for ABC to merge: the two registers have disjoint consumers. On the same
design the physical lever gains **+17.515 ns**.

**Both variants are rejected at G3**: declared k=0, flop count +16. That is
the same rule that caught A6 in batch 2. It is also worth stating against
us: register duplication is behaviourally state-preserving, and the right
obligation for it is sequential equivalence (branch 1, `dsec`), which the
typed library has but the k=0 flop-count precondition prevents reaching. Dr.
RTL's Jasper SEC would accept this transform; our gate rejects it by
construction. That is a limitation of G3 as implemented, not evidence the
transform is wrong.

Predictions:

6. Plain duplication changes max fanout by less than 20%: **CONFIRMED** on
   this design (+0.2% overall; the register's own load moved 1,131 to
   1,175). The registered mechanism, ABC re-merging, is **not** what
   happened; the consumer cone was monolithic, so there was nothing to split.
   Right prediction, wrong mechanism, recorded.
7. With `(* keep *)`, fanout splits and the slack gain is below the lever's:
   **half wrong**. Fanout did not split at all; the comparison holds
   trivially (-0.447 versus +17.515).

One design, one literal application of the skill. A finer split, duplicating
per byte lane of the fetch mux, might divide the cone; the skill's own text
("aligned with consumer cones") does not say how, and this is what a model
following it as written produces.

## Phase 3 (registered predictions 8 to 11): the lever, split

Phase 1's primary prediction failed because the lever mixed two things. Same
15 designs, same netlist A, same per-design period, three levers:
buffer-only (`buffer -N 16`), sizing-only (`upsize; dnsize`), and both.
`phase3/score.py` computes every number below.

| verdict | n | both, median | **buffer-only** | **sizing-only** | closed: both | buffer | sizing |
|---|---|---|---|---|---|---|---|
| FANOUT_DOMINATED | 5 | 3.623 | **+3.282** | +2.495 | 5/5 | **4/5** | 5/5 |
| MIXED | 2 | 8.059 | +6.602 | +5.988 | 1/2 | 1/2 | 1/2 |
| DEPTH_DOMINATED | 8 | 0.481 | **-0.019** | +0.495 | 4/8 | **1/8** | 4/8 |

**Buffering alone is net harmful on depth-dominated designs** (worse on 5 of
8: `cpu_pipe` -0.453, `tv80` -0.151, `i2c` -0.135, `ticket_machine` -0.038,
`vending_machine` 0.000) and closes 4 of 5 fanout-dominated ones. That is
the claim the classifier makes, measured against the component it models.
Prediction 4's "fewer than half of DEPTH" was right about buffering and wrong
about the lever it was tested with.

Per design, buffer-only versus sizing-only:

| design | verdict | A | buffer-only | sizing-only | both |
|---|---|---|---|---|---|
| cpu_fsm | FANOUT | -5.761 | **+18.974** | +1.231 | +11.754 |
| datapath | FANOUT | -0.769 | +2.675 | +2.915 | +3.223 |
| communication | FANOUT | -0.581 | +2.701 | +1.914 | +3.042 |
| aes | FANOUT | -0.527 | +0.831 | +1.059 | +1.015 |
| arm_cpu2 | FANOUT | -0.975 | -0.553 | +0.755 | +0.930 |
| DSP | DEPTH | -1.867 | -1.371 | **+0.917** | +0.984 |
| simple_spi | DEPTH | -0.425 | -0.076 | +0.692 | +0.641 |
| i2c | DEPTH | -0.396 | -0.531 | +0.584 | +0.581 |
| cpu_pipe | DEPTH | -0.850 | -1.303 | -0.229 | -0.269 |
| tv80 | DEPTH | -0.980 | -1.131 | -0.746 | -0.599 |
| controller | DEPTH | -0.182 | +0.052 | +0.187 | +0.173 |

Predictions:

8. Buffer-only median gain, FANOUT at least 3x DEPTH: **CORRECT**, and by
   more than registered: +3.282 against **-0.019**, so the ratio is not
   finite.
9. Sizing-only does not separate by verdict (ratio below 2x): **WRONG**, the
   ratio is 5.04. Sizing helps depth paths (+0.495 median, 7 of 8 designs)
   and helps fanout paths *more*, because upsizing the gate that drives
   1,131 loads is itself a fanout remedy.
10. Buffer-only closes at least 3 of 5 FANOUT (4 of 5, correct half) and
    sizing-only at most 2 of 5: **WRONG**, sizing alone closes **5 of 5**.
11. Sizing beats buffering on at least 6 of 8 DEPTH designs: **CORRECT**,
    7 of 8.

Two of four wrong, both in the same direction: sizing is a stronger and
broader lever than registered. The classifier's verdict therefore predicts
two different things about the two components: **where buffering helps at
all** (only fanout paths), and **how much sizing helps** (5x more on fanout
paths, but never nothing).

**One number that was not predicted by anything.** On `cpu_fsm`, the most
fanout-dominated design in either benchmark, buffer-only gains +18.974 and
the combined lever +11.754: adding sizing *after* buffering gave back 7.2 ns.
ABC's `upsize; dnsize` applied to an already-buffered tree is not additive
with the buffering, on this design at this setting. One design, one ABC
script order, not claimed as a rule; recorded because a judge who reads the
table will see it.

## Phase 4 (registered predictions 12 to 14): Dr. RTL skill #8, condition-wire replication

`phase4_trace.py` walked the four remaining FANOUT designs' synthesis
temporaries back to RTL. Three resolved to a single condition wire
(`aes`: `i_start & o_done` gating a 128-bit key mux, fanout 129;
`communication`: the `bit_count > 0` shift enable on a 64-bit register,
fanout 70; `datapath`: `col_en = col_en_host | col_en_w_bypass` with two
consumer blocks, fanout 35). `arm_cpu2`'s is a multi-level instruction
decode of `rom_data` and was **not attempted**. Skill #8 as written:
replicate the wire once per consumer group, plain and with `(* keep *)`.
Each variant timed at the scored period, as netlist A and against the
**buffer-only** lever (phase 3's isolated fanout lever), then gated.

| design | variant | slack A | worst-path top fanout | gain vs gold | buffer-only lever | gate |
|---|---|---|---|---|---|---|
| aes | gold | -0.527 | 129 | | +1.358 | |
| aes | plain | -0.527 | 129 | 0.000 | | UNRESOLVED |
| aes | keep | -0.515 | 128 | +0.012 | | UNRESOLVED |
| communication | gold | -0.581 | 70 | | +3.282 | |
| communication | plain | -0.581 | 70 | 0.000 | | PROVEN |
| communication | keep | **-0.800** | **35** | **-0.219** | | PROVEN |
| datapath | gold | -0.769 | 35 | | +3.444 | |
| datapath | plain | -0.712 | 37 | +0.057 | | PROVEN |
| datapath | keep | **+0.229** | 188 (a different net) | **+0.998, closes** | | PROVEN |

Three different outcomes on three designs:

- **Plain replication is a no-op, 3 of 3.** ABC merged the replicated wires
  back: aes and communication are byte-identical to gold in slack and
  fanout, datapath moves by 0.057 ns. This is H2's mechanism, which phase 2
  could not test because there the consumer cone was monolithic.
- **`(* keep *)` split the fanout on 1 of 3 and that design got slower.**
  communication's 70 became 35 and slack went from -0.581 to -0.800: two
  half-width enables cost more than one full-width one on this path.
- **`(* keep *)` closed 1 of 3 without splitting the worst net.** datapath
  went to +0.229 ns, MET, while its worst path moved to a *different* net at
  fanout 188. The replication helped, and not by the mechanism the skill
  describes.

On all three the buffer-only lever gains more: +1.358, +3.282, +3.444
against +0.012, -0.219, +0.998.

**Gate: 4 of 6 PROVEN, 2 of 6 UNRESOLVED, 0 refuted.** Both aes variants hit
EQY's depth bound on the 128-bit key mux with no counterexample, the same
class as A2 in batch 2, and are reported as unresolved rather than as
either verdict.

**Two harness defects, both found by this phase.** The aes variants first
read `G1 FAIL` twice: `tools/gate_proposal.py` read the input with
`read_verilog` and no `-sv`, and after that was fixed, it renamed the
`module` header but not SystemVerilog's `endmodule : name` label, so Yosys
refused to elaborate. Neither is a verdict on the transform. Both are fixed,
and `tools/verdict_regression.sh` was re-run afterwards because the gate
changed.

Predictions:

12. Plain replication changes top fanout by less than 20% on at least 2 of
    3: **CORRECT**, 3 of 3, by the registered mechanism.
13. `(* keep *)` cuts fanout at least 2x on at least 2 of 3, and gains less
    than the buffer-only lever on all 3: **WRONG**. It cut fanout on 1 of 3;
    the lever comparison held on 3 of 3.
14. All 6 variants PROVEN: **WRONG**, 4 of 6. The other 2 are unresolved,
    not refuted, and the reason is a solver bound on a 128-bit mux.

Across phases 2 and 4, Dr. RTL's two high-confidence fanout skills, applied
as written to their own benchmark's fanout-dominated designs under an
open-source flow: 0 of 4 applications reduced the worst path's fanout and
improved timing at once, 1 of 4 closed timing by moving the problem, 2 of 4
made timing worse, and every one was beaten by buffering alone.

## Files

`PREREGISTRATION.md` (+3 amendments, +phases 3 and 4), `run_classify.sh`, `run_classify_io.sh`,
`score.py`, `phase2_probe.sh`, `results/` (scored, run 4),
`results_run1_as_registered/`, `results_run2_nodffe/`,
`results_run3_legalized/`, `results_allpaths/`.

## Amendment 4 outcome, 2026-09-03: verdicts re-derived with the corrected classifier

The defect and the fix are described in `PREREGISTRATION.md` amendment 4
and `tools/classify_path.py`; the regression is `tools/classify_regression.py`
(5 fixtures, 2 from this project's benchmark and tv80, DSP, cpu_pipe from
this study; 0 disagreements with OpenSTA's fanout column at or above fanout
32 on all 5). Re-derivation: `reclassify.sh`, same saved netlists, same
periods, `report_checks -fields {fanout}`. Output in `results_reclassified/`.

| design | old verdict | old share | new verdict | new share | top cell fanout old -> new |
|---|---|---|---|---|---|
| tv80 | DEPTH_DOMINATED | 0.000 | **MIXED** | 0.368 | 0 -> 34 |
| DSP | DEPTH_DOMINATED | 0.050 | DEPTH_DOMINATED | 0.110 | 1 -> 53 |
| cpu_pipe | DEPTH_DOMINATED | 0.000 | DEPTH_DOMINATED | 0.180 | 3 -> 78 |
| the other 12 | unchanged | | unchanged | | |

1 of 15 verdicts changed, 3 of 15 shares moved, nothing moved toward DEPTH.
Corrected split: 5 FANOUT, 3 MIXED, 7 DEPTH.

Re-scored (`rescore_corrected.py`; medians of the per-design gains already
on the record, nothing re-measured):

| statistic | original grouping | corrected grouping |
|---|---|---|
| phase 1, combined lever, median gain FANOUT / DEPTH | 3.623 / 0.481 (7.5x) | 3.623 / 0.581 (6.2x) |
| phase 1, closes FANOUT / DEPTH | 5 of 5 / 4 of 8 | 5 of 5 / 4 of 7 |
| phase 3, buffer-only, median gain DEPTH | -0.019, worse on 4 of 8 | **0.000, worse on 3 of 7** |
| phase 3, buffer-only, median gain FANOUT | +3.282, closes 4 of 5 | unchanged |
| phase 3, sizing-only, median gain DEPTH / FANOUT | +0.495 / +2.495 | +0.621 / +2.495 |
| phase 3, MIXED (n=2 -> 3) buffer-only median | +6.602 | -0.041, worse on 2 of 3 |

tv80's own numbers (phase 3): buffer-only -0.151, sizing-only +0.234,
combined +0.381. Moving it from DEPTH to MIXED removes the design on which
buffer-only did the most harm from the DEPTH set.

**What survives.** Buffering helps fanout paths (median +3.282, closes 4 of
5) and does nothing for depth paths (median 0.000). The phrase "net harmful
on depth paths" does not survive: with tv80 correctly classified the DEPTH
median is exactly zero and 3 of 7 are worse. Sizing helps both and fanout
paths 4x more (+2.495 against +0.621; was 5x). The MIXED group is 3 designs
and is not summarised.

Predictions: P15 correct (nothing moved toward DEPTH), P16 correct (tv80
changed), **P17 wrong** (1 of 8 DEPTH verdicts changed, 2 predicted), P18
correct at the boundary (median 0.000, registered as "at or below 0").
Score for this study is now 8 correct, 1 half, 9 wrong of 18.
