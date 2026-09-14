# Pre-registration: does the router ever choose the RTL lever on its own?

Registered 2026-09-11, **before** `tools/slacksmith.py` is changed to accept an
external design and before any external design has been run through the loop.

    git log --diff-filter=A -- experiments/unforced/PREREGISTRATION.md
    git log -- tools/slacksmith.py

## Why

One unforced RTL-lever run: take a depth-dominated design from the Dr. RTL
transfer set, run `slacksmith.py` with the `cli` backend and no `--force-lever`,
and report whatever happens, including a refutation. That turns the two-router
claim from an architecture into a measurement. Without it, on our benchmark, the
router would never have asked for a retiming.

Every RTL result in this project was produced with `--force-lever rtl`, logged
as `lever_forced`, because `bench_top`'s binding paths are 59 to 91 percent
fanout-attributable and the classifier correctly routes them to the physical
lever. **The router has never fired on its own.** That is a property of the
benchmark, and the fix is to point it at a design with the opposite pathology.

## Design under test

`i2c` from the Dr. RTL set: `i2c_master_top`, 560 cells, classified **DEPTH**
with fanout share **0.000** in `experiments/drrtl_transfer/results/`. Chosen
before any loop run, for three stated reasons: it is depth-dominated so the
router should select RTL unforced; it is real third-party IP rather than
anything we wrote; and it is small enough that a sequential miter closes, which
`rv32i_core` at 2,048 flops does not (R19).

**If the router routes it to `physical` anyway, that is the result** and it is
reported. Trying a second design after seeing the first route to physical is a
void condition, because picking designs until one routes to RTL is the search
this project's registrations exist to forbid.

## Predictions

| # | prediction | prior |
|---|---|---|
| **U1** | The classifier routes `i2c`'s binding path to **RTL**, unforced, and `lever_forced` is absent from the log | high, it scored 0.000 fanout share, but that was measured by the standalone classifier and not inside the loop |
| **U2** | The `cli` backend returns a usable proposal on a design the model has never seen and that carries no project context | uncertain; `aes_key_mem` is a well-known core, `i2c_master_top` less so |
| **U3** | The proposal reaches a **G4 verdict**, not `UNRESOLVED` or `CANNOT`, because 560 cells is well inside what the miter closes | high |
| **U4** | The proposal **does not improve** the binding path | genuinely uncertain, and this is the one worth watching. Every prediction of this shape this project has made about a *fanout* path was right; the two it made about RTL touching a *depth* path (R18, C3) were both wrong |
| **U5** | Whatever happens, the loop **terminates cleanly** rather than crashing on a design that is not `bench_top` | low. Nothing outside `bench_top` has ever been through the full loop, and `rtl_files` is hardcoded to `remeasure.BENCH_TOP_FILES` |

## What counts

The deliverable claim is **U1 alone**: that the router selects RTL without being
told to. U2 through U4 describe what the engine then does with it, and a
refuted or useless proposal still satisfies U1.

**A crash is not a result.** If U5 fails the run is repaired and re-run, and the
repair is recorded, as with the `cli` backend's first attempt.

## Void conditions

- Trying another design after seeing this one route to physical.
- Adjusting the classifier thresholds, which are frozen and were chosen on
  `bench_top`.
- Choosing the SDC target after seeing where the path lands. The target is
  0.9x the design's own measured requirement, the same rule
  `experiments/drrtl_transfer/` used for all 20 designs.

---

## Run 1, 2026-09-11: the router did not route, and the reason is a defect in the classifier

    measure: wb_clk_i=-0.396
    classify wb_clk_i: NO_ACTION (fanout share 0.0) -> none
    no lever for verdict NO_ACTION.

| # | registered | outcome |
|---|---|---|
| **U1** | the router selects RTL unforced | **NOT ANSWERED.** It selected neither lever |
| **U5** | the loop terminates cleanly on a design that is not `bench_top` | **CONFIRMED.** `exit: 0`, no crash, `--rtl-files` worked first time |
| U2, U3, U4 | about the proposal | **VOID.** No proposal was requested |

### The defect

`report_checks -to [get_clocks wb_clk_i] -group_path_count 1` returns **one path
per path group**, and this SDC has two: input-to-register and
register-to-register. The report therefore ends with two slack lines:

       3.688   slack (MET)
      -0.396   slack (VIOLATED)

`classify_path.parse_path()` finds the slack with `re.search`, which returns the
**first** match, so it read `3.688 MET` and returned `NO_ACTION`.
`remeasure.sta_slack()` uses `re.findall` and takes the **last**, which is why
the same run printed `-0.396` one line earlier. **Two parsers in this project
disagree about which path is the path**, and the classifier takes the one that
is not.

Worse, `parse_path` collects its cell rows with `finditer` over the whole
report, so on a multi-block report the rows are **mixed from both paths** while
the slack comes from one of them. The 11 cells and 3.89 ns it reported are not
necessarily one path.

### Why this never surfaced on `bench_top`

`sdc/bench_top_v3.sdc` sets no input or output delay, so every clock's report
carries a single register-to-register group and a single slack line. The defect
needs a second path group to appear, and this project's own benchmark has never
had one. **The first external design tried exposed it immediately.**

### Consequence for published results

None of this project's published classifications is affected: they were all run
on reports with one block. That is asserted from the SDC's contents and is
checked below rather than assumed.

| # | prediction |
|---|---|
| **U6** | Every `bench_top` classification re-runs unchanged after the fix, because each report has one path block |
| **U7** | With the fix, `i2c` classifies **DEPTH_DOMINATED** and routes to **RTL**, unforced, matching the standalone verdict in `experiments/drrtl_transfer/` |

The run is repeated after the fix. Per this registration, a crash or a defect
is repaired and re-run; it is the *design* that may not be swapped.

---

## Run 3, and a misdiagnosis of mine, corrected within the hour

**What I wrote first, and it was wrong.** Seeing `Path Group: asynchronous` and
`recovery check` in the prompt the loop handed the model, I recorded that the
router had fired at a reset recovery check, blamed my own SDC for not
false-pathing the reset, and called it a classifier defect.

**Measured, both queries on the same netlist and SDC:**

    REG-TO-REG   byte_controller/bit_controller/_394_   -0.396  VIOLATED
    RECOVERY     arst_i -> _257_                        +3.688  MET

**The recovery check meets.** The violating path is a genuine
register-to-register data path inside `i2c_master_bit_ctrl`. The classifier
selected it correctly, and `U1` needs no qualifier: **the router routed a real
data path to the RTL lever with no override.**

My SDC does not need a reset false path either. Both halves of the earlier
entry were wrong, and both were wrong in the direction of blaming the setup for
something the tool was doing right.

### The real defect, which is narrower and in a different place

The **classifier** was fixed earlier today to score the worst block. **The
prompt was not.** `slacksmith.py` passed `reports[worst]` verbatim, so the model
was shown the report's *first* block: the recovery check that meets. The router
and the proposer were looking at different paths, and the proposer's was the
wrong one.

That is why the prompt's own evidence table lists `bit_controller` cells, from
the binding path, directly above a path report for a different path entirely.
The inconsistency was visible in the prompt and I read past it.

`classify_path.worst_block()` is now shared by both, so there is one answer to
"which path is the path" instead of two.

| # | prediction, registered now |
|---|---|
| **U10** | Re-running shows the model a report whose `Startpoint` is in `i2c_master_bit_ctrl`, matching the evidence table above it |
| **U11** | No `bench_top` result changes; its reports have one block, so `worst_block()` returns what was already being passed |

U8 and U9, registered against the wrong diagnosis, are **VOID**.

