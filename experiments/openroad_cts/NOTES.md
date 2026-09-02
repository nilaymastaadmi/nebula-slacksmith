# Does the closure survive a clock tree? Post-CTS and post-route timing

Run 2026-09-01. `experiments/openroad_repair/` closed all three groups with
`repair_design`, using **ideal clocks**: no clock tree, zero insertion delay,
zero skew. That is the standard context for `repair_design` and it is not a
signoff number. This benchmark has five asynchronous domains and five in-RTL
generated clocks including odd /3 and /5 dividers, so there was no reason to
assume the closure survives real clock trees.

It does.

## Method

One flow, three measurement points, everything else identical. Same OpenROAD
build (`f12e2f474`), same sky130hd platform, same liberty (ours), same
`sdc/bench_top_v2.sdc`, same unbuffered input netlist.

    floorplan 40% -> place_pins -> setRC -> global_placement
    estimate_parasitics -placement -> repair_design -> detailed_placement
    >>> point 1: ideal clocks
    clock_tree_synthesis -buf_list <clkbuf_1..16> -root_buf clkbuf_16
    set_propagated_clock [all_clocks]
    detailed_placement -> estimate_parasitics -placement
    >>> point 2: propagated clocks
    set_routing_layers -signal met1-met5 -clock met3-met5
    global_route -> estimate_parasitics -global_routing
    >>> point 3: routed parasitics

`set_propagated_clock` is the line that makes point 2 mean anything. Without
it OpenROAD keeps using ideal clocks after building the tree and the numbers
look unchanged for entirely the wrong reason.

The CTS buffer list is the plain `clkbuf` family. The `lpflow_clkbufkapwr`
cells are excluded, which matches both this project's own `dont_use` policy
(`docs/measurement-methodology.md` finding 1) and, independently, the
sky130hd platform's own `DONT_USE_CELLS`.

## Result

| point | clk_a | clk_b | clk_e | clock network | area (um2) |
|---|---|---|---|---|---|
| 1. post-place | +17.593 | +12.367 | +19.529 | **ideal** | 539,351 |
| 2. post-CTS | **+17.616** | **+8.694** | **+18.428** | **propagated** | 547,184 |
| 3. post-global-route | **+17.117** | **+8.987** | **+18.647** | **propagated** | 547,184 |

**Every group meets at every point.** The clock trees cost **7,833 um2**
(+1.45%, 48% to 49% utilization) and 1,547 clock buffers (1,440 `clkbuf_1`,
107 `clkbuf_16`).

## That the clocks are genuinely propagated was checked, not assumed

A flow that silently skipped `set_propagated_clock` would produce a
flattering table. Three independent confirmations:

- The path reports print **6** `clock network delay (ideal)` lines (point 1,
  three clocks times launch and capture) and **12** `clock network delay
  (propagated)` lines (points 2 and 3).
- Insertion delay is exactly `0.0 / 0.0` at point 1 and nonzero afterwards.
- CTS logged buffers created per domain (546, 113, 19, 17, 9, 5, ...) and the
  written netlist contains 1,547 `clkbuf` instances.

## What the clock tree costs, and why

Launch and capture insertion delay, post-CTS:

| clock | launch | capture | imbalance | slack change |
|---|---|---|---|---|
| clk_a | 2.463 | 2.373 | 0.090 | **+0.023** |
| clk_b | 6.457 | 2.943 | **3.514** | **-3.673** |
| clk_e | 3.589 | 0.000 | n/a | -1.101 |

`clk_b` pays 3.673 ns for its clock tree and the mechanism is visible in the
same report: its launch path sits 3.514 ns deeper in the tree than its
capture path. That imbalance is the cost, not the absolute insertion delay,
which is why `clk_a` at 2.463 ns of insertion is essentially free (0.090 ns
imbalance, +0.023 ns net).

This is the ordinary reason CTS hurts setup timing, and seeing the imbalance
and the slack loss agree to within 0.16 ns is the check that the numbers are
describing the same thing.

Global routing then moves everything by less than 0.5 ns in either direction:
routed parasitics are close to the placement estimates on this design.

## Honest limits

- **`report_clock_skew` printed headers with no rows** on this 2022 OpenROAD
  build, for every clock, at both points. Rather than report a skew number we
  do not have, the imbalance column above is derived from launch and capture
  insertion delay in the path reports themselves. A real skew report would be
  better and we do not have one.
- **`clk_e` shows 0.000 capture insertion at point 2** and 2.725 at point 3.
  That is not explained here. It is flagged rather than smoothed over, and it
  is why `clk_e`'s row has no imbalance figure.
- **Global route, not detailed route.** No DRC, no signoff extraction. These
  are good pre-signoff numbers, not tapeout numbers.
- **One floorplan.** 40% utilization, aspect ratio 1.0, one CTS buffer list.
  No sweep, so nothing here claims those are optimal.
- Same 2022 build caveat as `experiments/openroad_repair/`.

## Reproduce

    bash experiments/openroad_cts/run.sh                      # v2 SDC, default netlist
    bash experiments/openroad_cts/run.sh <netlist.v> <sdc>    # anything else
