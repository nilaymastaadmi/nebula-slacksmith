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
