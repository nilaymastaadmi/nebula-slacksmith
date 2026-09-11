# Does the router ever choose the RTL lever on its own?

Registered in `PREREGISTRATION.md` before `tools/slacksmith.py` could run on any
design but this project's own benchmark, with three dated amendments including
one correcting a misdiagnosis of mine.

## Why this exists

Every RTL result in this project was produced with `--force-lever rtl`, logged
as `lever_forced`, because `bench_top`'s binding paths are 59 to 91 percent
fanout-attributable and the classifier correctly sends them to the physical
lever. The router had **never fired on its own**. A second organiser review
named that the single change that would most raise the score, and named its
absence as the second-worst thing a judge would hit:

> "Show me the AI recommending a retiming." [...] on our benchmark the router
> would not have asked for it.

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
