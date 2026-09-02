# Pre-registration: a verdict-aware physical lever in the closed loop

Written 2026-09-03, before `tools/slacksmith.py` is changed or run.

## What changes

The loop's physical lever has been the combined ABC script
`buffer -N 16; upsize; dnsize`, applied once, to everything. Phase 3 of the
transfer study measured its two components separately on 15 external
designs: buffering alone is **net harmful on depth-dominated paths** (median
-0.019 ns, worse on 5 of 8) and closes 4 of 5 fanout-dominated ones; sizing
helps both, and fanout paths 5x more. On the most fanout-dominated design,
buffer-only (+18.974) beat the combined lever (+11.754).

So the classifier's verdict should choose the component. New
`--lever-policy verdict`:

| verdict | first physical step | second | then |
|---|---|---|---|
| FANOUT_DOMINATED / MIXED | buffer-only | sizing | stop, no RTL lever for fanout |
| DEPTH_DOMINATED | sizing-only | (none) | RTL proposals |

Every physical step is now **provisional**, exactly like an RTL proposal: it
is applied, the loop re-measures, and it is reverted if the group it targeted
did not improve. Until now only RTL steps had that bar; phase 3's cpu_fsm
result (sizing after buffering gave back 7.2 ns) is why physical steps get
it too. `--lever-policy blunt` keeps the old behaviour so every earlier run
reproduces.

## The comparison

Baseline: the blunt-policy v3 run already on the record,
`experiments/closed_loop/run_v3_final.jsonl` (8 iterations: physical lever
closes clk_b, clk_a stays at -1.716 through three reverted RTL proposals).

Treatment: the verdict policy, same SDC v3, same proposal pools, same
`--max-iters 8`, same engine (`sta`).

## Predictions

1. Under the verdict policy, `clk_b` still closes with buffer-only alone
   (it was FANOUT at 0.914 and the lever gain was +17.557 combined). High.
2. `clk_a` after its first physical step is **better than -1.716** (the
   blunt result), because the verdict policy applies sizing to a DEPTH group
   instead of buffering-plus-sizing. Medium.
3. At least one physical step is **reverted** by the new provisional bar
   during the run. Medium-low; registered so a miss is visible.
4. The verdict run reaches "all met" or "no lever left" in **no more**
   iterations than the blunt run's 8. Medium.
5. The loop never applies buffer-only to a group it classified
   DEPTH_DOMINATED. High; this is a check that the policy is wired right.

## Amendment 1, 2026-09-03, written at treatment iteration 2 (only iteration 1 seen, identical to the baseline)

Prediction 1 names the wrong clock. In the baseline log the group classified
FANOUT_DOMINATED at share 0.9139 in iteration 1 is **clk_e** (-25.957), not
clk_b; clk_b (-18.957) closed to +5.6 as a side effect of the same lever, and
clk_e itself ended the blunt run at **-0.606**, not closed. Prediction 1 is
scored exactly as written (clk_b at or above 0 after the first buffer-only
step). Whether clk_e closes under buffer-only is reported alongside it as an
unregistered observation, not a prediction.

## What would make this void

- Changing thresholds in `tools/classify_path.py`.
- Editing any proposal.
- Comparing against a re-run of the blunt policy instead of the committed
  log, unless the re-run reproduces it exactly (it should; the flow is
  deterministic).

## Amendment 2, 2026-09-03, after the run: the classifier's verdicts in this run were wrong

Found after run 3 and run 4 were scored. `tools/classify_path.py` as used by
this run undercounted fanout across module boundaries (see
`experiments/drrtl_transfer/PREREGISTRATION.md` amendment 4 and
`tools/classify_regression.py`). The post-buffering `clk_a` path it called
DEPTH_DOMINATED at share 0.000 has a 387-load net carrying 6.762 of its
17.131 ns and is MIXED at 0.428; the post-buffering `clk_e` path it called
DEPTH_DOMINATED at 0.000 has a 59-load net carrying 1.952 of 6.817 ns and is
MIXED at 0.286. Under the registered policy MIXED routes to buffer-only then
sizing then stop, so with a correct classifier the RTL lever would not have
fired in this run at all. Predictions 1 to 5 keep their scores: they were
scored against the verdicts the loop acted on. Prediction 5 in particular is
a wiring check and remains correct as such. The corrected-classifier run is
registered separately in `PREREGISTRATION_classifier_fixed.md`.
