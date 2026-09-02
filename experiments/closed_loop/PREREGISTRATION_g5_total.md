# Pre-registration: G5 measured across all groups, not the targeted one

Written 2026-09-03 at iteration 5 of the verdict-policy run
(`PREREGISTRATION_verdict_lever.md`), with iterations 1 to 4 seen. Nothing in
`tools/slacksmith.py` is changed before this file is committed.

## What the verdict-policy run showed at iteration 2 and 3

| step | clk_a | clk_b | clk_e | G5 (per group) |
|---|---|---|---|---|
| baseline | -13.167 | -18.957 | -25.957 | |
| buffer-only, target clk_e | **+1.75** | +5.556 | -1.444 | confirm (+24.513) |
| sizing added, target clk_e | **-1.716** | +5.6 | -0.606 | confirm (+0.838) |

The sizing step improved the group it targeted by 0.838 ns and moved clk_a
from met to violating by 3.466 ns. The per-group G5 bar looks only at the
targeted group, so it confirmed the step. From that point on the run is the
blunt run: clk_a is the worst group, DEPTH_DOMINATED, and the RTL proposals
are tried and reverted one by one exactly as in `run_v3_final.jsonl`.

The mechanism is stated as a hypothesis, not a finding: ABC's `upsize;dnsize`
sees one delay target for the whole netlist, not three clocks, so `dnsize`
is free to shrink cells that only clk_a's constraint makes critical.

## The change

New `--g5 {target,total}`, default `target` (the bar every run so far used).
Under `total`, a provisional step (RTL or physical) is confirmed only if the
**sum over reported groups of min(worst slack, 0)** strictly improves. The
same scalar for the steps already on the record:

| step | before | after | total-G5 |
|---|---|---|---|
| buffer-only | -58.081 | -1.444 | confirm |
| sizing | -1.444 | -2.322 | **revert** |
| P1 | -2.322 | -2.632 | revert |

Nothing else changes: same verdict policy, same SDC v3, same proposal pools,
same `--max-iters 8`, engine sta.

## Predictions

6. The sizing step is reverted. This is arithmetic on data already seen and
   is registered to check the wiring, not as a forecast.
7. After that revert the worst group is clk_e at -1.444, DEPTH_DOMINATED,
   with sizing already tried, so the loop goes to the RTL lever, finds no
   proposal whose `target_module` is on the path (all 6 AES proposals target
   `aes_key_mem`; the post-buffering clk_e path is in `aes_decipher_block`
   and `aes_inv_sbox`), and stops with `no_proposal_on_path`. High.
8. Final state: clk_a +1.75, clk_b +5.556, clk_e -1.444; one group violating
   instead of two, and the run ends in at most 4 iterations. High.
9. The total-G5 run's final sum is -1.444 against the per-group run's
   -2.322. Follows from 8; recorded so the comparison number is fixed
   before it is measured.

## What this would and would not show

If 6 to 9 hold, the loop with the total bar leaves the design in a strictly
better state than with the per-group bar on this benchmark, and it does so
by refusing a step rather than by finding a better one. It does not close
clk_e; nothing in either proposal pool touches the module on that path, and
the honest end of the run is "no lever left", stated.

## What would make this void

- Changing thresholds in `tools/classify_path.py`, or any proposal.
- Any tolerance on the sum other than strict improvement. If a tolerance is
  ever added it is a new registration.

## Amendment 1, 2026-09-03, after the run: same classifier defect as run 3

The `clk_e` verdict at iterations 2 and 4 (DEPTH_DOMINATED, 0.000) is
MIXED at 0.286 with the corrected classifier; see
`PREREGISTRATION_verdict_lever.md` amendment 2. Predictions 6 to 9 keep their
scores. Prediction 7's stated reason ("no proposal on the path") is the
reason the loop gave; with a correct verdict the loop stops one step earlier
for a different reason (physical lever exhausted). The end state is the
same. Registered as prediction 11 in `PREREGISTRATION_classifier_fixed.md`.
