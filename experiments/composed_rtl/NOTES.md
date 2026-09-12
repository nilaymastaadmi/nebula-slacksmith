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

## After `repair_design`: the measurement REPORT §1 said was missing

Both netlists through the identical OpenROAD flow, SDC v3, placement
parasitics, separate work dirs.

| clk_b | gold | composed | composed minus gold |
|---|---|---|---|
| zero-parasitic, unbuffered | −18.957 | −13.792 | **+5.165** |
| with parasitics, unbuffered | −57.438 | −38.646 | **+18.792** |
| with parasitics, **after `repair_design`** | **+5.283** | **+5.046** | **−0.237** |

All three groups, after `repair_design`:

| clock | gold | composed | marginal RTL gain |
|---|---|---|---|
| clk_a | +3.093 | +2.235 | **−0.858** |
| clk_b | +5.283 | +5.046 | **−0.237** |
| clk_e | −1.471 | −1.792 | **−0.321** |

**R37. CONFIRMED.** The marginal gain after buffering is smaller than the
unbuffered gain, by any of the three comparisons above.

**R38. WRONG.** It is not positive. It is **negative on every clock group**.
After `repair_design`, the composed optimized RTL is slightly *worse* than the
untouched gold RTL, by 0.237 ns on the group the whole project has been
optimizing.

### What that means, said plainly

`repair_design` saturates. Starting it from a design that is already 18.792 ns
better does not finish 18.792 ns better; it finishes 0.237 ns worse. The
physical lever fixes what the RTL was fixing, and then some, and the RTL's
remaining contribution is inside the noise of where the buffering happens to
land.

**The RTL is not worthless after buffering, but what it buys is area, not
time.** Repair grew the gold design by **90,511 u²** (+20.2%) and the composed
design by **87,732 u²** (+19.6%): the composition needed **2,779 u² less
buffering**, 3.1% less, and the final design is **3,851 u² smaller**. The
honest sentence is that three formally proven RTL transforms, composed, bought
**0.7% area at a cost of 0.237 ns** once a standard physical flow had run.

This is the number REPORT §1 named as the most important one the project had
not measured, and it is the one that most constrains what this project may
claim. Every RTL gain reported anywhere in this repository is an unbuffered
gain. **On this design, under this flow, none of it survives buffering.**

`clk_e` does not close under v3 in either design (−1.471 gold, −1.792
composed), so v3 remains a target the flow does not meet, which is why it was
chosen.

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

## Amendment 1 result: the control changes two of the three numbers above

**R47. CONFIRMED.** The gold netlist through the identical flow a second time
returns **+3.093 / +5.283 / −1.471** and **539,351 u²**, identical to the first
run in every digit. The physical flow is deterministic here, so nothing below is
run-to-run variation.

**R48. CONFIRMED on `clk_b`, and it rescues nothing.** A5, the registered
do-nothing transform, through the same flow:

| post-repair | gold | A5 control | composed | control moves | composed moves |
|---|---|---|---|---|---|
| clk_a | +3.093 | **+3.950** | +2.235 | **+0.857** | −0.858 |
| clk_b | +5.283 | **+5.277** | +5.046 | **−0.006** | **−0.237** |
| clk_e | −1.471 | **−1.399** | −1.792 | **+0.072** | −0.321 |
| area | 539,351 | **536,403** | 535,500 | **−2,948** | −3,851 |

### What this forces

**On `clk_b` the regression is real.** A transform that does nothing on the read
path moves the post-repair number by **0.006 ns**. The composition moves it by
**−0.237 ns**, forty times the control. **R38's WRONG stands**, and the finding
stands with it: after `repair_design` the composed optimized RTL is genuinely,
measurably slightly worse than the untouched RTL.

**On `clk_a` the regression is withdrawn.** The control moves `clk_a` by
**+0.857 ns** and the composition by **−0.858 ns**. Those are the same size. The
post-repair `clk_a` number is not resolvable below roughly 0.86 ns for any RTL
edit at all, so "the composition costs 0.858 ns on `clk_a`" is not a measurement
and is not claimed. `clk_e` sits in between at 4.5x its control and is reported
with that ratio attached rather than on its own.

**The area result is mostly not ours, and that is the correction that matters
most.** Earlier in this file the composition's **3,851 u²** smaller final design
was called the surviving benefit. The do-nothing control is **2,948 u²**
smaller. So **903 u², 0.17%**, is attributable to three formally proven
transforms; the rest is what a physical flow does when handed any perturbed
netlist. The "0.7% area" framing was wrong and is withdrawn here rather than
left standing in a file nobody re-reads.

### The honest final position on this experiment

After a standard physical flow, three composed formally proven RTL transforms
leave the design **0.237 ns slower on the group they targeted and 903 u²
smaller**, and their large unbuffered gains (+5.165 zero-parasitic, +18.792 with
parasitics) do not survive. On this design, on these paths, RTL optimization is
not the lever.

**This project's own classifier said so before any of it was measured.**
`classify_path.py` routes these paths `FANOUT_DOMINATED` to the physical lever,
and every RTL result in this repository was obtained by overriding it with
`--force-lever rtl`. The negative result is not a surprise the project
uncovered; it is the project's own routing decision, confirmed the expensive
way.

## Amendment 2 result: four more perturbation points, and R38 is VOID

Registered before running (`PREREGISTRATION.md` amendment 2, commit `8872a26`).
`noise_floor2.sh` and `abc_pair.py`, raw logs in `results/repair_*.txt`,
`results/post_repair_summary.txt` and `results/abc_buffered_pair.txt`.

Post-repair, every netlist through the identical flow, gold twice:

| netlist | clk_a | clk_b | clk_e | area u² | Δ clk_b | Δ area |
|---|---|---|---|---|---|---|
| gold, run 1 and run 2, identical | +3.093 | +5.283 | −1.471 | 539,351 | | |
| A5, do-nothing edit | +3.950 | +5.277 | −1.399 | 536,403 | **−0.006** | −2,948 |
| A4 alone | +3.163 | +5.287 | −1.713 | 534,184 | **+0.004** | −5,167 |
| O2 alone | +4.290 | +5.098 | −1.478 | 541,150 | **−0.185** | **+1,799** |
| O1 alone | +1.865 | +5.139 | −1.959 | 537,927 | **−0.144** | −1,424 |
| composed A4+O2+O1 | +2.235 | +5.046 | −1.792 | 535,500 | **−0.237** | −3,851 |

**R49. CONFIRMED.** A4 +0.004, O2 −0.185, O1 −0.144, all within ±0.30 of
gold. No single proven transform survives `repair_design` on `clk_b` either.

**R50. WRONG, by 0.004 ns.** The spread across the five perturbed netlists is
**0.241**, not under 0.237. By the rule amendment 2 declared before running,
**R38 is VOID**: the composition's −0.237 is not distinguishable from what
perturbing the netlist does.

The registration was flawed and the flaw is the registrant's: the five
included the composition itself, so the test misses whenever the composition
is the extreme point, which is exactly the case it was meant to separate.
Scored as written, because a prediction is what it says. Stated so a reader
can judge it anyway: excluding the composition, the other four span **0.189**
(+0.004 to −0.185), and the composition sits 0.048 beyond that range. The two
netlists that touch the read path, O2 and O1, move in the composition's
direction; the two that do not, A5 (a do-nothing edit) and A4 (whose
duplicated cones the mapper re-merges), sit at ±0.006. That is consistent
with a small real cost from O2 and O1 that composing does not add to. It is
not resolvable as one at N = 5, and it is not claimed.

**R51. CONFIRMED.** `clk_a` spans **2.425 ns** across the five (+1.197 to
−1.228). No RTL edit's effect on post-repair `clk_a` is resolvable in this
flow, which generalises amendment 1's withdrawal.

**R52. WRONG, 2 of 3.** O2 alone is **1,799 u² larger** than gold after
repair; A4 is 5,167 smaller. Perturbed netlists land on both sides of gold by
more than the composition's −3,851, so the composition's area is not a
transform effect. The miss strengthens the withdrawal of the area headline
rather than weakening it.

**R53. CONFIRMED, at exactly zero.** After the ABC buffering lever
(`buffer -N 16; upsize; dnsize`, the loop's physical lever), gold and
composed both time `clk_b` at **+5.600**: delta **0.000**. The unbuffered
+5.165 survives the mapping-level lever at 0%. `clk_a` −0.272 and `clk_e`
0.000, reported separately. Cells 30,264 against 30,275.

### The honest final position, revised on N = 5

After the mapping-level buffering lever, the composed RTL is worth **0.000
ns** on `clk_b`. After the full physical flow it is worth **−0.237 ns against
a five-netlist perturbation spread of 0.24 ns**, with every transform-bearing
netlist at or below gold and the do-nothing edit at −0.006. The unbuffered
+5.165 and the with-parasitics +18.792 survive neither lever. "Genuinely,
measurably slightly worse", written above on the strength of one control, is
**withdrawn**; what N = 5 supports is *no timing benefit survives, and the
direction, where it resolves at all, is not positive*. Area is not reportable
in either direction (R52).

That is the fanout-dominated row of a two-row table. The depth-dominated row,
the same measurement on a design the classifier routes to RTL, is
`experiments/depth_i2c/`.
