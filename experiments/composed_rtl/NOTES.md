# Composed RTL: results

Registered in `PREREGISTRATION.md` (commit `ab2279d`) before anything here was
synthesized. Scripts committed in `94b7a21`. This file is the scorecard.

## Null control, run first

| clock | baseline | variant | delta |
|---|---|---|---|
| clk_a | −13.167 | −13.167 | **+0.000** |
| clk_b | −18.957 | −18.957 | **+0.000** |
| clk_e | −25.957 | −25.957 | **+0.000** |

Gold swapped for itself, 0.000 on every group. The deltas below are measurements
of transforms, not of flow noise.

## Zero-parasitic timing, SDC v3, one flow, one liberty

| variant | clk_a | clk_b | clk_e |
|---|---|---|---|
| A4 one-hot read select | +0.987 | **+4.925** | +4.925 |
| O2 FSM re-encoding | +0.528 | **+3.185** | +3.185 |
| O1 fanout split | +1.967 | **+1.414** | +1.414 |
| **composed A4+O2+O1** | **+1.967** | **+5.165** | **+5.165** |
| arithmetic sum of the three | +3.482 | +9.524 | +9.524 |

**A4's +4.925 is the same number under v3 as it was under v2.** That was not
guaranteed and it is why the re-measurement was registered: the three published
figures turned out to be addable after all, but that could only be known by
measuring, not by assuming.

## Scorecard

**R32. CONFIRMED.** The three-way merged file parsed, elaborated and mapped
with no hand edit, in five independent Yosys runs.

**R35. CONFIRMED.** Composed `clk_b` is **+5.165** against an arithmetic sum of
**+9.524**. The composition recovers **54.2%** of its parts.

**R36. CONFIRMED, and this is the uncomfortable part.** Composed **+5.165**
beats the best single transform's **+4.925**, by **+0.240 ns**. O2 and O1 are
worth **+4.599 ns** standing alone and contribute **+0.240 ns** on top of A4,
which is **5.2%** of their standalone value. Composition is better than the best
part, by an amount that would be inside the noise of a less careful setup. It is
not inside this one's: the null control is 0.000 to three decimals.

**R39. WRONG.** The prediction said cell count would **rise** by less than 1%.
It **fell**, from **28,844** to **28,839**, by 5 cells (−0.017%). The bound the
prediction was really testing held, and the direction it stated did not. Scored
as a miss, because a prediction is what it says and not what it meant. The
reason is H2's re-merge finding running the other way: with all three
duplications in one module, the mapper re-merges slightly more than the gold
needed, not less.

**R40. CONFIRMED.** `clk_a` moved **+1.967 ns**, reported here and never folded
into the `clk_b` claim. Note that composed `clk_a` equals O1's `clk_a` exactly,
to three decimals, while A4 and O2 each moved it less. On `clk_a` the
composition is O1 and nothing else.

**R33. WRONG.** The prediction said the composition's flop count would differ
from gold by **0**. It differs by **−2** (gold 4,386, composed 4,384). G3 passed
anyway, because branch 4 routes as `PASS(state-remap: k=0, flop delta
unconstrained)`, which is the branch existing precisely so a re-encoded state is
not judged by flop arithmetic.

**The miss was avoidable and that is the interesting part.** O2's own gate record
(`experiments/missing_classes/results/R17_O2.json`) already says `dff_delta: -2`.
The composition's −2 **is** O2's −2: composing did not change storage, one part
already had, and the registration asserted otherwise without reading the part's
own result first. A prediction written from the proposals' prose rather than from
their gate records.

**R34. PARTIAL, pending the second gate.** The obligation router did select
**branch 4 (mapped-state)**, as predicted. G4 returned **PROVEN (partial: 2 of 3
outputs)**: `ready` and `sboxw` proven, `round_key` undecidable, with the null
control reporting `REFUTES on round_key; PASSES on ready,sboxw`. That is the
same verdict shape O2 alone gets, for the reason REPORT §9 documents: Yosys does
not apply the module's async reset to `key_mem`, so the two instances start from
different arbitrary contents. **The refutation was never reported as one**,
because the null control ran first and caught it. `gate_zeroinit.sh` runs the
second gate the parts carry, under the equal-initial-state assumption.

| | gold | composed | delta |
|---|---|---|---|
| cells (gate view) | 7,975 | 8,109 | +134 |
| flops | 4,386 | 4,384 | **−2** |

**R37, R38: pending.** `repair_design` is running on both netlists.

## What this says about D4

Deliverable D4 now has **one optimized RTL file**, not four separate proven
variants: `aes_key_mem_composed.v`, rebuildable by `compose.sh` from the gold
file and the three proposals, with the rebuild checked rather than asserted.

It also says the thing a judge should hear plainly: **stacking proven transforms
does not stack their gains.** Three transforms that are worth 9.524 ns apart are
worth 5.165 ns together, and two of them are worth 0.240 ns once the third is
present. Every per-transform number in this project, ours included, is an
overstatement of what that transform contributes to a design that already has
other transforms in it.
