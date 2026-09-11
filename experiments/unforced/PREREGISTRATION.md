# Pre-registration: does the router ever choose the RTL lever on its own?

Registered 2026-09-11, **before** `tools/slacksmith.py` is changed to accept an
external design and before any external design has been run through the loop.

    git log --diff-filter=A -- experiments/unforced/PREREGISTRATION.md
    git log -- tools/slacksmith.py

## Why

The second organiser review names this the single change that would most raise
the score, above everything else except the video:

> **One unforced RTL-lever run.** Take a depth-dominated design from the Dr. RTL
> transfer set, run `slacksmith.py` with the `cli` backend and no
> `--force-lever`, and report whatever happens, including a refutation. This
> turns the two-router claim from an architecture into a measurement.

And it names the absence as the second-worst thing a judge will hit:

> **"Show me the AI recommending a retiming."** [...] on our benchmark the
> router would not have asked for it.

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

## Run 3, observed mid-run: the router fired, and the path it fired at is a recovery check

The prompt the loop handed the model carries this path:

    Startpoint: arst_i (input port clocked by wb_clk_i)
    Endpoint:   _257_ (recovery check against rising-edge clock wb_clk_i)
    Path Group: asynchronous
    Path Type:  max

**That is an asynchronous-reset recovery check, not a logic path.** Its −0.396
ns is the margin on reset deassertion. No RTL transform is the right answer to
it; a reset synchronizer or a declared false path is.

### Two separate problems, and they belong to different parties

**1. A setup error of mine.** `experiments/unforced/i2c.sdc` does not false-path
the async reset. This project knows to do that: REPORT §8's core-level
measurement says "reset false-pathed, otherwise the recovery check masks the
data path". I did not apply the same care to a design I set up in twenty
minutes, and the result is that the loop optimised the wrong thing.

**2. A defect in the classifier, which is the more interesting one.**
`classify_path.py` has **no notion of path kind**. It read a path whose report
says `Path Group: asynchronous` and `recovery check`, scored its fanout share,
returned `DEPTH_DOMINATED` and routed it to an LLM. A router that cannot tell a
data path from a recovery check will confidently spend a proposal on something
no RTL rewrite can fix. On `bench_top` that never arose, because
`sdc/bench_top_v3.sdc` declares `set_clock_groups -asynchronous` and the resets
never produced the worst path.

### How this is being handled, stated before the run finishes

- **Run 3 stands as recorded.** Whatever the model returns is reported. It is
  evidence about the router and about the classifier, and it is not evidence
  about whether GenAI can improve `i2c`'s data path.
- **U1 is scored CONFIRMED with a qualifier**: the router selected RTL with no
  override, and the path it selected was one it should have excluded. Both
  halves are true and reporting only the first would be the misreport this
  registration exists to prevent.
- **Adding a false path and re-running is a SEPARATE experiment** with its own
  registration. Editing this SDC after seeing where the path landed is exactly
  the void condition written above, and the fact that the edit is defensible
  does not make it exempt.
- The classifier defect is fixed on its own merits, not to rescue this run.

| # | prediction, registered now |
|---|---|
| **U8** | `classify_path.py` gains a path-kind check and returns a distinct verdict for non-data paths; re-running run 3 unchanged then yields that verdict rather than `DEPTH_DOMINATED` |
| **U9** | No `bench_top` classification changes, because no report there has ever carried a `recovery check` or an `asynchronous` path group |
