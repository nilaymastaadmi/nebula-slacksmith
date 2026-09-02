# Pre-registration: run 5, the corrected classifier under the verdict policy and the total bar

Written 2026-09-03 before the run. Same SDC v3, same proposal pools, same
`--lever-policy verdict --g5 total --max-iters 8`, engine sta. The only
change is `tools/classify_path.py` (bus and concatenation connections
expanded; OpenSTA's fanout column read when present) and the two query
strings that now ask `report_checks` for `-fields {fanout}`.

Baseline: run 4, `run_v3_g5total.jsonl`.

What is already known: the run-4 iteration-4 netlist is a regression fixture
(`experiments/classifier_regression/v3_bufonly_it4*`) and classifies MIXED at
0.2864 with the corrected code. Prediction 10 is therefore arithmetic on data
already seen, registered so the wiring is checked.

## Predictions

10. Iteration 2 classifies `clk_e` MIXED at fanout share 0.286 (was
    DEPTH_DOMINATED at 0.000).
11. The run stops with `physical_exhausted`, not `no_proposal_on_path`,
    because MIXED routes to the physical lever and both components have been
    applied or reverted by then. High.
12. The RTL lever never fires (no `gate` record in the log). High.
13. Final state identical to run 4: clk_a +1.75, clk_b +5.556, clk_e
    -1.444, in 4 iterations. High.
14. Iteration 1 still classifies `clk_e` FANOUT_DOMINATED at 0.9139: the
    key-memory nets were inside one module and were never undercounted.
    High.

## What this shows if it holds

The loop's end state on this benchmark does not change; its reason does. The
RTL proposals were never the right lever for the residual violation, and the
earlier runs applied them to a path the classifier had misjudged. That is
reported as a correction, not as a result.
