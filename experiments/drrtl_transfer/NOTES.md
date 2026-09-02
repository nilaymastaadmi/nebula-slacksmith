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

## Phase 2 (registered predictions 6 and 7), status

Groundwork done (`phase2_probe.sh`): `cpu_fsm`'s `PC` is an RTL register
(`output reg [7:0] PC`) with one high-fanout consumer, `IR <= imem[PC]`, which
is the textbook case for Dr. RTL skill #7. `aes`'s `o_done` (register bit,
fanout 34) is a second target. The other three FANOUT designs' top nets are
synthesis temporaries, which is skill #8's case and needs hand tracing.
Variants and results are in `phase2/` when run.

## Files

`PREREGISTRATION.md` (+3 amendments), `run_classify.sh`, `run_classify_io.sh`,
`score.py`, `phase2_probe.sh`, `results/` (scored, run 4),
`results_run1_as_registered/`, `results_run2_nodffe/`,
`results_run3_legalized/`, `results_allpaths/`.
