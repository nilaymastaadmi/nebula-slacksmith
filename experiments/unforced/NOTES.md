# Does the router ever choose the RTL lever on its own?

Registered in `PREREGISTRATION.md` before `tools/slacksmith.py` could run on any
design but this project's own benchmark, with three dated amendments including
one correcting a misdiagnosis of mine.

## Why this exists

Every RTL result in this project was produced with `--force-lever rtl`, logged
as `lever_forced`, because `bench_top`'s binding paths are 59 to 91 percent
fanout-attributable and the classifier correctly sends them to the physical
lever. The router had **never fired on its own**, so on this benchmark it would
never have asked for a retiming.

## Setup, frozen before the loop saw anything

| | |
|---|---|
| design | `i2c_master_top` from the Dr. RTL set, 560 cells |
| prior classification | **DEPTH**, fanout share **0.000** (`experiments/drrtl_transfer/`) |
| measured requirement | **3.956 ns**, matching that study's published figure exactly |
| frozen target | **3.560 ns**, 0.9x, the same rule applied to all 20 designs there |
| binding path | `byte_controller/bit_controller/_394_`, **−0.396 ns**, register to register |

Chosen for three reasons stated in advance: depth-dominated so the router should
pick RTL unforced; third-party IP rather than anything we wrote; and small
enough that a sequential miter closes, which `rv32i_core` at 2,048 flops does
not.

## The headline

    classify wb_clk_i: DEPTH_DOMINATED (fanout share 0.0) -> rtl

**No `--force-lever`. No `lever_forced`.** The router selected the RTL lever on
its own, on a real register-to-register violation, at a target frozen before it
ran. That is U1 and it is the deliverable claim.

## It took four runs, and the three failures are worth more than the success

Every one was a defect in this project's own tooling, invisible for the life of
the project because it had only ever been pointed at one design.

| run | outcome | defect | why `bench_top` hid it |
|---|---|---|---|
| 1 | `NO_ACTION` on a violating design | `classify_path.parse_path()` took the **first** slack line, not the worst. `report_checks -group_path_count 1` returns one path per **path group** | `sdc/bench_top_v3.sdc` sets no input or output delay, so every report has one block |
| 2 | `stop: module_not_in_file_list` | the loop resolved a binding module to `<module>.v` | our benchmark is one module per file; `i2c.v` declares three |
| 3 | `G4=HARNESS_ERROR` | the gate suffixed only the **target** module, so the other two collided: `Re-definition of module i2c_master_byte_ctrl` | same |
| 4 | see below | | |

**None of them affects a published result.** All four were found by the first
design that was not ours, which is the argument for this experiment independent
of what the proposal did.

## A misdiagnosis of mine, inside run 3

Seeing `Path Group: asynchronous` and `recovery check` in the prompt, I recorded
that the router had fired at a reset recovery check and blamed my own SDC.
Measured, both queries on the same netlist:

    REG-TO-REG   byte_controller/bit_controller/_394_   -0.396  VIOLATED
    RECOVERY     arst_i -> _257_                        +3.688  MET

**The recovery check meets.** The router was right and I was wrong, in the
direction of blaming the setup for something the tool was doing correctly.

The real defect was narrower: the classifier had been fixed to score the worst
block, and **the prompt had not**, so the router and the proposer were looking
at different paths. `classify_path.worst_block()` is now shared by both. The
tell was an evidence table listing `bit_controller` cells directly above a path
report for a different path, and I read past it.

## What the model proposed, unattended, on a design it had never seen

    def_id : onehot_idle_bit_recode
    branch : 4 (mapped-state equivalence)
    k      : 0

Its own rationale:

> `c_state` is 17 bits encoding 18 states as one-hot-except-idle, so every
> `case(c_state)` arm needs a full 17-bit equality compare, which the mapper
> builds as a 3-level tree of wide gates (`or4/nor4b/or4b/o41ai` on the reported
> path).

**Those are the cells the classifier reported.** It reached for obligation
branch 4, which did not exist in this project twelve hours earlier, and it is
an **FSM optimization**, one of the four classes the problem statement names.

## Run 6: the complete loop, and what it returned

    measure:  wb_clk_i = -0.396
    classify: DEPTH_DOMINATED (fanout share 0.0) -> rtl
    binding module i2c_master_bit_ctrl found in i2c.v
    online proposal O1: fsm_explicit_idle_one_hot_bit (declared k=0)
    gate O1: G1=PASS G2=PASS G3=PASS(state-remap) G4=UNRESOLVED
    no proposal passed the gate.

**Measure, classify, route, propose, gate, refuse. No human at any step, and no
`--force-lever`.** The obligation did not close inside the gate's budget, so the
loop declined the transform. `UNRESOLVED` is never a pass, which is the rule
this project has had since batch 1.

Run 5 is recorded separately: the CLI exceeded a hardcoded 600 s timeout on a
25 KB module, which is an environmental failure, and the budget is now a flag.

## Scorecard

| # | registered | outcome |
|---|---|---|
| **U1** | the router selects RTL unforced | **CONFIRMED**, on a real register-to-register violation |
| **U2** | the CLI returns a usable proposal on an unseen design | **CONFIRMED**, three times, three different transforms |
| **U3** | the proposal reaches a G4 verdict, not UNRESOLVED or CANNOT | **WRONG.** `UNRESOLVED` |
| **U4** | the proposal does not improve the binding path | **VOID.** Nothing passed the gate, so nothing was timed |
| **U5** | the loop terminates cleanly on a design that is not `bench_top` | **CONFIRMED**, after six repairs |
| U6, U7, U10, U11 | the fixes change no `bench_top` result | **CONFIRMED**, `classify_regression.py` 5 of 5 and the verdict regression unchanged |
| U8, U9 | registered against a misdiagnosis | **VOID** |

## What this does and does not establish

**Establishes.** The two-router design is a measurement rather than an
architecture: given a depth-dominated path the classifier selects the RTL lever
with no override, and the generative half produces a typed, gateable proposal
on third-party IP it has never seen. Three runs produced `onehot_idle_bit_recode`,
`parallel_case_onehot_decode` and `fsm_explicit_idle_one_hot_bit`, all attacking
the same thing the classifier reported: `c_state` encodes 18 states in 17 bits
as one-hot-except-idle, so every `case` arm is a wide equality compare.

**Does not establish.** That the engine improves `i2c`. One complete run, one
proposal, `UNRESOLVED`. A second proposal, `parallel_case_onehot_decode` from
run 4, **is PROVEN by EQY** when the gate is run by hand, but that was a
by-hand gate run during a repair, not a loop result, and it is reported as
such rather than promoted.

**And the variance is the point.** Same model, same prompt, same design, three
different transforms and at least two different gate outcomes. The report's
"one sample per proposal, no best-of-n" is no longer a disclaimer; it is an
observation.
