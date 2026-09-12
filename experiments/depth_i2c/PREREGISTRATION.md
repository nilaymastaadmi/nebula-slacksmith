# Pre-registration: does an RTL gain survive the physical lever on a depth-dominated design?

Registered 2026-09-12, before any run in this directory. Predictions R54 to
R60; R1 to R53 are in the earlier registrations. Scored in `NOTES.md` here.

## Why this experiment exists

`experiments/composed_rtl/` measured that three formally proven RTL transforms,
composed, are worth +5.165 ns on `clk_b` before wires and −0.237 ns after
`repair_design` (R38, WRONG; amendment 2 is re-testing whether −0.237 is even
resolvable). Every one of those transforms was aimed at a path
`tools/classify_path.py` scores **FANOUT_DOMINATED** at 0.914 and routes to the
physical lever; every RTL result on `bench_top` was produced by overriding that
router with `--force-lever rtl`.

So the negative result has two readings, and the difference between them is
the difference between "the RTL half did not work" and "the router was right":

1. RTL optimization does not survive a physical flow, full stop.
2. RTL optimization does not survive a physical flow **on paths the classifier
   sends elsewhere**, and survives it on paths the classifier sends to RTL.

Only the second reading makes the classifier a decision procedure: a
prediction, made before any model call, of whether RTL work on a given design
will pay after buffering. Nothing in the repository tests it. This does.

## Design under test

`i2c_master_top` from the Dr. RTL set, exactly as `experiments/unforced/`
froze it: 560 cells, **DEPTH_DOMINATED**, fanout share 0.000, requirement
3.956 ns, SDC frozen at 0.9x = 3.560 ns, binding path −0.396 ns register to
register in `i2c_master_bit_ctrl`. The unforced experiment already confirmed
(U1) that the router selects RTL on it with no override. Chosen because it is
the one depth-dominated design the loop has ever run on, and the registration
there forbids picking a second design after seeing the first.

**What `experiments/unforced/` left open, and why this cannot reuse it.** That
directory reports a proposal, `parallel_case_onehot_decode`, as "PROVEN by
EQY, by a gate run by hand during a repair". The file does not exist: not in
the repository, not in the scratch tree, because `run.sh` wipes its work
directory on every run. A proven transform with no artifact is not evidence
and REPORT §7.2 is corrected to say so. This experiment generates its own.

## What is run

**Phase 1, generate.** Three unattended runs of `tools/slacksmith.py` with the
`cli` backend, **no `--force-lever`**, `--max-online 1 --max-iters 2 --g5
total`, the same flags `experiments/unforced/` run 6 used, into three separate
work directories. Three because the same request has returned three different
transforms on this design (`unforced/NOTES.md`), one sample per run, no
best-of-n within a run. Every request, reply, variant and gate log is copied
into `results/runN/` whatever the verdict.

**Phase 2, measure survival**, for every phase-1 proposal that reached
`PROVEN` inside the loop, and for the control:

| column | netlist | lever |
|---|---|---|
| A | `synth; dfflibmap; abc` | none, zero-parasitic |
| B | same, `abc -script` `buffer -N 16; upsize; dnsize` | the loop's physical lever, zero-parasitic |
| C | A through OpenROAD floorplan, placement, `estimate_parasitics`, `repair_design` | the real flow, placement parasitics |

Gold, each proven variant and the control go through all three, identical
flow, reg-to-reg path only, under the frozen `i2c.sdc`. The control is
`rtl_control/i2c.v`: two independent always blocks in `i2c_master_bit_ctrl`
exchanged in source order, a semantic no-op built by `make_control.py` and
checked against its definition. It is the i2c analogue of A5.

The fanout-dominated cell of the same table is R53 in
`experiments/composed_rtl/PREREGISTRATION.md` amendment 2 (column B) and R37,
R38 there (column C).

## Predictions

**R54.** The router selects the RTL lever unforced in **3 of 3** runs, and
`lever_forced` is absent from every log. Prior: high, U1 held.

**R55.** At least **1 of 3** proposals reaches `PROVEN` inside the loop. Prior:
medium. Of the three transforms this design has drawn so far, one was proven
by hand and one came back `UNRESOLVED` in the loop; the third was never gated.

**R56.** The proven proposal improves the unbuffered reg-to-reg slack (column
A, variant minus gold) by **more than +0.050 ns**. Prior: uncertain. U4
registered that it would not; but every prediction this project has made that
RTL would not move a *depth* path (R18, C3) was wrong.

**R57, the main one.** After the ABC buffering lever, the marginal gain
(column B, variant minus gold) is **at least 50% of the unbuffered gain**
(column A). This is the depth-dominated cell of the survival table. Its
fanout-dominated partner is R53: composed minus gold after the same lever,
predicted under 20% of the unbuffered +5.165. If R57 holds and R53 holds, the
classifier's verdict predicts survival and §1 of the report may say so. If
R57 misses, reading 1 above stands: RTL work does not survive buffering on
either pathology, and the classifier is a cost-saver, not a decision procedure.
Prior: medium-high, because `experiments/drrtl_transfer/` phase 3 measured
buffering alone as net harmful on depth paths (median −0.019 ns), so there is
little for the lever to take away from an RTL gain there.

**R58.** After `repair_design` (column C), the marginal gain is **positive and
larger than the control's** post-repair movement on this design. Prior:
medium.

**R59.** The control moves post-repair slack by **less than 0.050 ns**. Prior:
medium; on `bench_top` A5 moved one group by 0.006 and another by 0.857.

**R60.** Gold through the i2c OpenROAD flow **twice** returns identical
post-repair slack, as R47 did on `bench_top`. Prior: high.

## Declared fallback, so it is not a post-hoc choice

If R55 misses and no unattended proposal reaches `PROVEN`, phase 2 runs on a
**handoff-tier** proposal: the model driving this session writes one typed
transform against the same request the loop produced, through the same gate.
R56 to R58 are then scored at that tier and every number carries the label
"handoff, not unattended", as `missing_classes/` O1 and O2 do. R55 stays
WRONG. If that proposal is not `PROVEN` either, phase 2 is **VOID** and this
directory reports that.

## Void conditions

- Any change to the design, the SDC, the classifier thresholds, or the flags
  between runs.
- A fourth unattended sample. Three is the count.
- Gating an `UNRESOLVED` proposal by hand with a larger budget and reporting it
  as proven. The loop's verdict is the verdict.
- Phase 2 on any proposal that was not `PROVEN` inside the loop, except under
  the declared fallback.

## What this does not establish

One design, one pathology on each side of the table. A 2x2 with one design per
cell is a hypothesis with a data point in each cell, not a decision procedure;
the report will say "on the one depth-dominated design measured", and the
number of designs needed to say more is a question this experiment cannot
answer.
