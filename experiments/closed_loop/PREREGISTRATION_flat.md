# Pre-registration: run 6, the closed loop on the flat flow

Written 2026-09-03 after `experiments/flatten_control/` arms A to E were
read and before the loop is run with `--flatten`. Same SDC v3, same
proposal pools, `--lever-policy verdict --g5 total --max-iters 8`, engine
sta, corrected classifier. New: `--flatten` (synth -flatten before abc).

What is already known: arms C, D and E of the flatten control are the three
netlists this run will produce in order (no buffering; buffer-only;
buffer+size), and the flow is deterministic. The predictions below are
therefore arithmetic on those arms plus the loop's registered policy, and
are recorded so the wiring is checked and the log exists as a demo artifact.

## Predictions

29. Iteration 1 measures +9.279 / −4.065 / −15.762 (arm C) and classifies
    clk_e FANOUT_DOMINATED at 0.9547.
30. Iteration 2 measures +10.362 / +5.665 / −0.613 (arm D); the buffer
    step is confirmed (total −19.827 to −0.613); clk_e classifies MIXED at
    0.3221 and sizing is applied.
31. Iteration 3 measures +11.158 / +5.665 / −0.319 (arm E) and the sizing
    step is **confirmed**, unlike run 5, because the total improves.
32. The run stops at iteration 3 with `physical_exhausted`; the RTL lever
    never fires; final state +11.158 / +5.665 / −0.319.

## Stated limit

On a flat netlist Yosys renames every cell to a flat numeric name, so the
classifier's module attribution is None for every cell and the RTL lever's
on-path module filter would select nothing. That does not affect this run
(the RTL lever is not reached) and is not patched here.

## Run 7, registered in the same file

Same as run 6 with `--buffer-pi` (ABC `buffer -N 16 -p`, flop outputs
buffered). Its predictions depend on flatten-control arms F and G, which
have not run at the time of writing, so run 7 is registered as: iteration 1
equals arm C; iteration 2 equals arm F; iteration 3, if reached, equals arm
G; and the stop reason is `physical_exhausted` unless clk_e closes, in
which case `all_met`. Prediction 33: run 7 ends with clk_e above run 6's
−0.319. Medium.
