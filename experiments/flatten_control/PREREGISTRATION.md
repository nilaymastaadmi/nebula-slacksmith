# Pre-registration: flatten before ABC, so the buffering pass can see across module boundaries

Written 2026-09-03, before `tools/remeasure.py` gains a flatten switch and
before any arm is synthesized.

## Why

The classifier correction (`docs/path-classification.md`, limit 2) showed
that the two residual violations under SDC v3 after buffer-only are both
MIXED because of one net each, and both nets cross a module boundary:

| group | net | driver | loads | delay on path | boundary |
|---|---|---|---|---|---|
| clk_a | `imem_data[2]` in `rv32_load` | `and2_1` | 387 | 6.762 of 17.131 ns | concatenated into `u_core.imem_data` |
| clk_e | `tmp_sboxw[16]` in `aes_decipher_block` | `a21oi_1` | 59 | 1.952 of 6.817 ns | whole-bus into `inv_sbox_inst.sboxw` |

This flow synthesizes hierarchically: `synth -top bench_top` keeps the
module tree and `abc` runs per module. Inside `rv32_load` the `imem_data[2]`
net has 1 visible load (the submodule port), so `buffer -N 16` has nothing
to split, and 387 leaf pins on the other side of the port never see a
buffer. Same for the 59-load S-box input. That is the hypothesis: the
physical lever was blind to exactly the two nets it needed to fix.

## Arms

All five: same RTL, same SDC v3, same liberty, same dont_use list, same
`opt_clean -purge`; the only differences are `-flatten` on `synth` and the
ABC script.

| arm | flatten | ABC script |
|---|---|---|
| A | no | default (`-liberty` only) |
| B | no | buffer-only (`BUF_ONLY` in `tools/slacksmith.py`) |
| C | yes | default |
| D | yes | buffer-only |
| E | yes | buffer + upsize + dnsize (`BOTH`) |

A and B are reproductions of numbers already on the record and serve as
checks. Every arm is timed on clk_a, clk_b, clk_e with
`report_checks -fields {fanout}` and classified by the corrected classifier.

## Predictions

19. A reproduces −13.167 / −18.957 / −25.957 and B reproduces
    +1.75 / +5.556 / −1.444 exactly. High; a miss voids the experiment.
20. D improves clk_e over B (above −1.444). Medium-high. Mechanism: the
    59-load net becomes visible to the buffer pass.
21. D improves clk_a over B (above +1.75). Medium. Mechanism: the 387-load
    net.
22. On D, no cell on any of the three worst paths has fanout above 100.
    Medium. The registered check that the mechanism is what changed.
23. D closes clk_e (at or above 0). Low-medium: 1.444 ns has to come out of
    a path whose fanout-bound cell is 1.952 ns.
24. C differs from A by less than 2 ns on every group: flattening alone is
    not the lever, buffering across the boundary is. Low-medium; ABC's
    optimisation on a bigger cone could move things on its own, and if it
    does, that is the finding.
25. E's clk_a is below D's clk_a. Medium. Mechanism as in closed-loop run 3:
    `dnsize` sees one delay target for the whole netlist and shrinks cells
    only clk_a's constraint makes critical.

## What this would change

If 20 and 21 hold, the loop's physical lever should run on a flattened
netlist, and every earlier v3 physical number is a hierarchical-flow number
and will be labelled so. The RTL lever's module filter needs instance-path
prefixes instead of module ownership on a flat netlist; that is a separate
change and is not made here.

## What would make this void

- Prediction 19 failing.
- Any change to the RTL, the SDC, the thresholds, or the ABC scripts other
  than choosing among the three registered ones.
