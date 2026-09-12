# Pre-registration: the depth cell, on an instrument that can show it

Registered 2026-09-12. **The floor was measured first and is quoted below; the
predictions were written after seeing it and before any proposal ran**, which is
the order this block requires and the opposite of the usual order for a reason:
a prediction about "a gain above the floor" is meaningless until the floor is a
number. Predictions **R76 to R81**.

## Why tv80 and not `i2c`

`experiments/depth_i2c/` ran the loop end to end, unforced, on external IP and
every decision was right. The gain was **0.000**, so the depth-dominated cell of
the survival table is empty. It could not have been otherwise: `i2c` is 560
cells and a null edit moved its unbuffered slack by **0.424 ns**, so there was
no room for a real effect to show above the noise.

`tv80s` from `hutch31/tv80` (MIT-style licence), 3,447 cells, is the second
attempt. **The physical lever does not close it**, which is the case where RTL
should matter: unbuffered **−0.894**, after the ABC lever **−0.296**, after
`repair_design` **−2.021**.

## The floor, measured before these predictions were written

Three null controls, all functionally identical to gold by construction:

| control | what it changes | A unbuffered | B ABC lever | C after repair | cells |
|---|---|---|---|---|---|
| gold | — | −0.894 | −0.296 | −2.021 | 3,447 |
| `ctrl_rename` | module name and its instantiation | −0.894 | −0.296 | −2.021 | 3,447 |
| `ctrl_reorder` | that module's position in the file | −0.894 | −0.296 | −2.021 | 3,447 |
| **`ctrl_flip`** | one ternary rewritten as its complement | **−1.046** | −0.269 | **−1.646** | 3,429 |

**Two of the three controls turned out to be no-ops and that is recorded, not
hidden.** `ctrl_reorder` produces a netlist **byte-identical** to gold: Yosys
elaborates by hierarchy, not by file position, so moving a module's text is not
a perturbation at all. `ctrl_rename` produces a different netlist, because
module names propagate into instance names, and identical timing to three
decimals. Neither changes structure, so neither can tell you whether the
instrument resolves a structural effect. `ctrl_flip` was added for that and is
the only one of the three that measures anything.

**Floor, from `ctrl_flip`:** **0.152 ns unbuffered**, 0.027 after the ABC lever,
**0.375 ns after `repair_design`**.

**Usability test, declared by this block before the floor was known:** unusable
if the largest excursion exceeds 5% of the period. The period is 8.044 ns, so
the bar is **0.402 ns**. The largest excursion is **0.375 ns**. **tv80 passes,
and it passes narrowly**, by 0.027 ns on the post-repair column. The unbuffered
column, where the RTL gain is first seen, has far more room at 1.9% of period.

`gold_run2` reproduces gold exactly, so the OpenROAD flow is deterministic here
as it was on the benchmark (R47).

## Predictions

**R76.** The classifier routes to **RTL unforced in 3 of 3 runs**. *Prior:
strong. The transfer study scored this design DEPTH with a fanout share of
0.000, and the router sends depth-dominated paths to RTL.*

**R77.** **At least 1 of 3** proposals reaches **PROVEN inside the loop**.
*Prior: moderate. On `i2c` one of three did.*

**R78.** A proven proposal's unbuffered gain exceeds **3x the floor, 0.456 ns**.
*Prior: weak, and this is the one the block exists to answer. `i2c` returned
0.000 and the composed benchmark work returned gains that did not survive.*

**R79, the survival cell.** The gain after the ABC lever retains **at least 50%**
of the unbuffered gain. *Prior: weak. On the benchmark's fanout-dominated paths
the retained fraction was 0%.*

**R80.** The gain after `repair_design` exceeds the control's post-repair
excursion of **0.375 ns**. *Prior: weak. Nothing in this project has yet beaten
a post-repair floor.*

**R81.** The in-loop G5 **confirms rather than reverts**. *Prior: moderate.*

## Declared fallback, on the quantity and not the gate

If **no proposal produces a positive unbuffered gain above 0.152 ns** for any
reason at all, including none proposed, refused, refuted, undecidable, or proven
and null, then **one handoff-tier proposal is written and run through the same
gate, labelled as handoff tier**, and the depth cell is reported at that
provenance. The fallback is declared now so that using it later is a disclosed
step rather than a rescue.

## What would void this

- Editing anything under `tools/` while the three runs are in flight. A repair
  waits until run 3 exits, is registered as an amendment, and every sample is
  replayed through the repaired tool.
- A proposal whose artifacts are not copied out of scratch in the same turn is
  **not counted**, whatever its verdict. `experiments/depth_i2c/` lost a PROVEN
  to a wiped scratch directory and reported it as absent.
- Three runs is three runs. No fourth run because the first three were
  unflattering.

## Scope

One design, three samples, one model, one machine. tv80 is a different artifact
from the `cpu_pipe` the plan named and from the tv80 netlist the transfer study
measured: this is upstream source at 3,447 cells and 8.938 ns, against that
study's 4,023 cells and 9.797 ns, so its DEPTH verdict is re-derived here rather
than inherited.
