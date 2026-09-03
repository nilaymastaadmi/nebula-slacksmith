# Pre-registration: repair_design on the flat netlist

Written 2026-09-03, before OpenROAD is run on any flat netlist.

## Why

`experiments/flatten_control/` left one violation under SDC v3: `clk_e` at
−0.319 ns, whose worst path starts at a flop output driving **136 loads**.
ABC's `buffer -N 16` does not touch it, and `-p` was measured to be a no-op
(arms F and G byte-identical to D and E). OpenROAD's `repair_design` does
repair max-fanout and max-slew violations on flop outputs, and on the
hierarchical netlist it was worth +55.805 ns on `clk_b`
(`experiments/openroad_repair/`). This asks what it does on the flat one.

## Arms and the comparison that is valid

Two netlists, both flat, from `~/flatexp`:

| arm | netlist | ABC |
|---|---|---|
| **OR-C** | `~/flatexp/C/mapped.v` | default (no buffering) |
| **OR-E** | `~/flatexp/E/mapped.v` | buffer + upsize + dnsize |

Both run the flow in `experiments/openroad_repair/run.sh` unchanged except
for the netlist and SDC v3: floorplan at 40% utilization, `make_tracks`,
`place_pins`, the platform `setRC.tcl`, global placement,
`estimate_parasitics -placement`, timing, then `repair_design`,
`detailed_placement`, parasitics again, timing again.

**Only before-versus-after within one arm is a valid comparison.** These
numbers carry placement parasitics and the flatten-control numbers do not.
The hierarchical flow already showed the size of that difference: `clk_a`
read +1.333 zero-parasitic and −36.723 with parasitics. Any sentence
comparing an OpenROAD slack to an OpenSTA slack across that boundary is
wrong, and none will be written.

## Predictions

34. On OR-C, `repair_design` improves every one of the three groups.
    High; it did hierarchically.
35. On OR-C after repair, no cell on any of the three worst paths drives
    more than 32 loads. Medium-high. This is the mechanism claim: the tool
    that reaches flop outputs is this one, not ABC.
36. OR-C closes all three groups under SDC v3 (all slacks at or above 0
    after repair). Medium. It closed all three under v2 on a worse netlist,
    and v3 is roughly 10% tighter than the post-buffering requirement.
37. OR-C's area increase is **below** the hierarchical run's +20.2%,
    because the flat netlist has 25,920 cells against 28,844 and fewer
    high-fanout nets to fix. Medium.
38. OR-E after repair is better than OR-C after repair on `clk_e`, that is,
    ABC's buffering and sizing still helps once `repair_design` has run.
    Low-medium. The plausible alternative is that `repair_design` subsumes
    it and the two end within noise of each other, which would say the ABC
    lever is redundant in a flow that has this tool.

## Stated limit, carried forward unchanged

`repair_design`'s output has **no equivalence proof**. Four attempts are
recorded in `experiments/openroad_repair/NOTES.md` and none finished. That
is why the physical lever is reported as a flow step and never as a proven
transform, and this experiment does not change it.

## What would make this void

- Any change to the flow script other than the netlist and the SDC.
- Comparing an OpenROAD slack with an OpenSTA slack.
