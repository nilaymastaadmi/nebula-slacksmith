# Pre-registration: the composed optimized RTL, and the marginal gain after buffering

Registered 2026-09-12, before the composition was synthesized or timed.
Scored in `NOTES.md` in this directory. Predictions are R32 to R40; R1 to R31
are in the earlier registrations.

## Why this experiment exists

REPORT §1 names one quantity as the most important thing this project has not
measured:

> every RTL number here is taken from the unbuffered baseline, while the router
> runs the levers in sequence, so the *marginal* RTL gain after buffering is
> known for exactly one transform (P2, which flipped sign) and is unmeasured for
> batch 3.

And deliverable D4 ships **four proven variants, not one optimized RTL**. An
external review on 2026-09-12 named both, and they are the same experiment:
compose the transforms that help onto one file, then measure that file twice,
once with no wires and once after `repair_design` has already fixed the loads
the RTL was trying to fix.

## What is composed

Three proven transforms, all on `rtl/aes/aes_key_mem.v`, merged three-way
against the gold file as the common ancestor:

| transform | class | source | gain as previously reported |
|---|---|---|---|
| A4 one-hot read select | combinational restructure | `experiments/llm_proposer_aes/proposals/aes_key_mem_A4.v` | +4.925 ns `clk_b`, **SDC v2** |
| O2 FSM state re-encoding | FSM optimization | `experiments/missing_classes/aes_key_mem_O2.v` | +3.185 ns `clk_b`, SDC v3 |
| O1 fanout split | control-cone duplication | `experiments/cli_backend/results/run1/O1_aes_key_mem.v` | +1.414 ns `clk_b`, SDC v3, measured outside the loop |

**Already observed before registering, and therefore not predicted:** the
three-way merge produces 0 conflicts and a 513-line file against the gold's 434.
Nothing has been synthesized, elaborated, timed or proven.

**The three previously reported gains are not addable as they stand.** A4 was
measured under SDC v2 and the other two under v3. So this experiment
**re-measures all three individually under one SDC, one liberty and one flow**,
in the same batch as the composition. The sum below means the sum of those
re-measurements, not the sum of the table above. Quoting the table's numbers as
a sum would be the cross-regime arithmetic §1 already retracted once.

## The measurement

`tools/remeasure.py`, `--sdc sdc/bench_top_v3.sdc`, zero-parasitic, groups
`clk_a`, `clk_b`, `clk_e`, one shared baseline cache, exactly as
`experiments/missing_classes/time_all.sh` does it. Then
`experiments/openroad_repair/run.sh` on the gold netlist and on the composed
netlist under the same SDC, for the after-buffering pair.

**Null control first.** The gold netlist is measured against its own cache
before any delta is reported. If that is not 0.000 on every group, this
experiment reports `CANNOT` and no number here is published. §5's rule stands:
a transform's effect is the delta in the group it touches, and movement
elsewhere is reported separately.

## Predictions

**R32.** The composed variant passes G1 (parse) and G2 (elaborate) with no
hand edits to the merged file.

**R33.** G3 precondition passes: the composed variant's flop count differs from
gold by **0**. Each part is k = 0 and each claims to preserve storage; if the
composition changes flop count, at least one of those claims was wrong in a way
none of the three single-transform runs could expose.

**R34.** G4 returns **PROVEN**, and the obligation router selects **branch 4
(mapped-state)**, because O2 re-encodes the state register and a re-encoded
state leaves no flop correspondence for EQY.

**R35 (the main one).** The composed `clk_b` gain is **strictly less than the
sum** of the three individually re-measured `clk_b` gains. Reason to expect
sub-additivity: O2 and O1 act on the *same* net. O2 removes a 3-bit decode from
the `round_key_update` enable path; O1 duplicates that same control cone. The
second lever to act has less left to remove.

**R36.** The composed `clk_b` gain is nonetheless **greater than or equal to the
best single transform's** re-measured gain. If this misses, composition is
actively harmful and D4 should ship the best single variant instead, which is a
publishable answer and would be reported as one.

**R37 (the quantity §1 names).** The **marginal** gain of the composed RTL
measured *after* `repair_design`, that is composed-buffered minus
gold-buffered on `clk_b`, is **strictly less than** its unbuffered gain.
Buffering fixes load; the RTL here is mostly fixing load.

**R38.** That marginal gain is **positive**. If it is negative, the honest
headline is that this project's RTL work does not survive the physical flow,
and §1's ratio becomes a ceiling rather than a measurement.

**R39.** The composed variant's unbuffered **cell count rises by less than 1%**
against gold. H2 already found that synthesis re-merges A4's duplicated cones
while keeping O1's, so some growth is expected and a large jump would mean the
mapper stopped re-merging once the two duplications were in the same file.

**R40.** At least one of `clk_a` or `clk_e` moves by more than 0.5 ns in either
direction, because three transforms in one module give ABC more to re-map
globally than any one of them did. Reported separately, never folded into the
`clk_b` claim.

## What would make this experiment worthless

If the null control is not 0.000, or if the composed file needs a hand edit to
elaborate, the result is a report of that and nothing else. Both are recorded
either way; the run directory is preserved whatever the verdict.

---

## Amendment 1, registered 2026-09-12 after R37 and R38 were scored

R38 missed: the marginal gain after `repair_design` is **−0.237 ns** on `clk_b`,
not positive. Before that number is reported as a finding it has to clear the
bar this project sets for every other number, and it does not yet.

**§5 established a noise floor for the synthesis and STA flow: swapping a module
for itself returns 0.000 on every group. No equivalent control exists for the
physical flow.** −0.237 ns is 4% of the +5.283 ns margin it sits in. Reporting it
as "the RTL is worse after buffering" assumes the OpenROAD flow is repeatable to
better than that, and nothing here has ever measured whether it is.

So two controls run before R38's verdict is allowed to stand.

**R47.** The flow is repeatable: the gold netlist through the identical
OpenROAD flow a second time gives post-repair slacks identical to the first run
on all three groups, delta **0.000**.

**R48.** A5 moves post-repair `clk_b` by **less than 0.237 ns** against gold.
A5 is the registered do-nothing control from `experiments/llm_proposer_aes/`:
it unrolls a reset loop, touches nothing on the read path, and still moved
`clk_b` by +0.436 ns zero-parasitic, which is why it exists. It is the right
probe for the question "how much does the post-repair number move for an RTL
edit that should not matter".

**What each outcome means, declared now rather than after seeing it:**

- Both hold: **R38's WRONG stands**. −0.237 is a real regression, the composed
  RTL is genuinely slightly worse after buffering, and that is the finding.
- **R48 misses** (A5 moves post-repair `clk_b` by 0.237 ns or more): **R38
  becomes VOID**, not WRONG. The honest claim is then that the marginal gain
  after buffering is **below the flow's own sensitivity to an irrelevant RTL
  edit**, which is a weaker and more defensible statement than either "it helps"
  or "it hurts", and the area result becomes the reportable one.
- **R47 misses** (the flow is not deterministic): every post-repair number in
  this project, including §8's closure table, acquires an error bar that has
  never been stated, and that gets written up as its own correction.

No result already recorded is withdrawn pending this. R37 stands either way:
the marginal gain is smaller than the unbuffered gain by 5 to 19 ns, which no
plausible noise floor reaches.
