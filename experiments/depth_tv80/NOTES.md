# The depth cell, second attempt: tv80

Registered in `PREREGISTRATION.md` (`93e4294`), floor measured before the
predictions were written, two amendments registered before each repair.

## The three runs

Three unattended runs, **no `--force-lever`**, one online proposal each, two
iterations so the loop's own accept-or-revert step runs.

| run | transform proposed | G1 | G2 | G3 | G4 | gate time | G5 |
|---|---|---|---|---|---|---|---|
| 1 | `onehot_mcycle_tail_case_merge` | PASS | PASS | PASS (state-remap) | **UNRESOLVED** | 898 s | — |
| 2 | `casez_parallel_case_hint` | PASS | PASS | PASS | **PROVEN** | 466 s | **REVERT**, −0.894 → −0.894 |
| 3 | `flatten_mcycle_tail_override_priority` | PASS | PASS | PASS | **PROVEN** | 1,091 s | **REVERT**, −0.894 → **−1.162** |

**Three runs, three different transforms**, all aimed at the same structure the
classifier reported: the binding path runs through `tv80_mcode`, a parameterised
microcode decoder, and every proposal attacks its `case` tail one way or
another.

## Scorecard

**R76. CONFIRMED.** The classifier routed to **RTL unforced in 3 of 3**, at a
fanout share of **0.1602** on an 8.856 ns path through 27 cells. No human, no
flag, on a design the loop had never seen.

**R77. CONFIRMED.** **2 of 3** reached PROVEN inside the loop.

**R78. WRONG.** A proven proposal's unbuffered gain was predicted to exceed 3x
the floor, **0.456 ns**. Run 2 delivered **0.000** and run 3 delivered
**−0.268**. Neither cleared the floor, let alone three times it.

**R81. WRONG.** G5 was predicted to confirm. It **reverted both** proven
transforms, which is the loop doing exactly what it should: proof and profit are
separate bars and it applied the second one.

**R82. CONFIRMED** (amendment 1). All three replays unmangled
`$paramod$...\tv80_mcode` to `tv80_mcode` and found it in `tv80.v`.

**R85. CONFIRMED** (amendment 2). All three replays reached a G4 verdict.

**R79 and R80: VOID.** Both ask what fraction of an unbuffered gain survives a
lever. **There is no positive unbuffered gain to survive anything.** Recorded as
void rather than as a hit, because a prediction that cannot fail is not
evidence.

**Four confirmed, two wrong, two void.**

## What this says, and it is the second time it has said it

**The depth cell is empty again, on a design chosen because the first one could
not have filled it.** `i2c` returned 0.000 with a 0.424 ns floor on 560 cells.
tv80 is 3,447 cells with a **0.152 ns unbuffered floor**, the physical lever does
**not** close it (−0.894 → −0.296), and the loop still found nothing that helps:
one proposal worth exactly 0.000 and one worth **−0.268**.

So the two-row table this project wanted reads:

| path pathology | RTL gain before wires | after the physical lever |
|---|---|---|
| fanout-dominated (benchmark) | +5.165 ns composed | **0.000, inside the floor** |
| **depth-dominated (`i2c`, tv80)** | **0.000 and −0.268** | nothing to carry |

**The classifier is not yet a decision procedure, and this is the second design
that says so.** It routes correctly, it saves proposals on paths RTL cannot fix,
and on the paths it sends RTL to, RTL has not helped either. That is a weaker
claim than the one this experiment was built to test, and it is the claim the
measurements support.

## Two harness defects, neither touching a published result

Both found by pointing the loop at a design larger and less regular than the
benchmark, both registered before the tool was edited, both replayed across all
three samples afterwards.

1. **`module_not_in_file_list`.** Yosys renames a parameterised module
   `$paramod$<hash>\name`; no source declares that. Same class as the `i2c`
   repair, one layer deeper.
2. **`OSError: Argument list too long`.** The prompt went in argv and carries
   the module's whole source; `tv80_mcode` is ~2,600 lines, past Linux's 128 KB
   per-argument ceiling. Now on stdin.

**A third limitation is disclosed rather than fixed**: G7 reports `SKIPPED,
module not in the file list` on all three runs. The unmangling repair reached
the lever's lookup and not G7's own. `tv80s` has one clock, so no crossing
existed for G7 to check, but the skip is a lookup failure rather than a reasoned
skip and it is recorded as one.

The failed runs are kept under `results/prerepair/` and `results/prerepair2/`.
