# OpenROAD `repair_design`: the real version of the buffering control

Run 2026-08-31. `experiments/buffering_control/` showed that a mapping-level
ABC buffering pass closes both violated groups. That pass has no placement and
no parasitics, so it is a control, not a flow. This is the flow.

OpenROAD was the one organizer-named tool this project had never used. It is
used here because the measurement asked for it: `docs/path-classification.md`
found the binding paths were 59% to 91% fanout-attributable, and
`repair_design` is the standard answer to that.

## Method

Build `f12e2f474`, dated 2022-03-17, installed under `$HOME` via micromamba
from the litex-hub channel (this machine has no passwordless sudo, so apt was
not an option). Platform files are the sky130hd platform from
OpenROAD-flow-scripts: `sky130_fd_sc_hd.tlef`, `sky130_fd_sc_hd_merged.lef`,
`make_tracks.tcl` and `setRC.tcl`.

**The liberty is ours, not the platform's.** Their
`sky130_fd_sc_hd__tt_025C_1v80.lib` and our `sky130hd_tt.lib` have different
md5 sums, so they were diffed rather than assumed equivalent: **6 differing
lines total**, all cosmetic (`1.0` versus `1.0000000000`, and a
`default_operating_conditions` line ours declares). Using ours keeps these
numbers comparable with every other measurement in this project.

Flow, with everything except `repair_design` held identical on both sides:

    read_lef (tech + merged cells); read_liberty; read_verilog; link_design
    read_sdc sdc/bench_top_v2.sdc
    initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2.0
    make_tracks; place_pins -hor_layers met3 -ver_layers met2
    setRC.tcl          (signal met1, clock met3, the platform's own values)
    global_placement -density 0.60
    estimate_parasitics -placement
    >>> timing measured here <<<
    repair_design
    detailed_placement
    estimate_parasitics -placement
    >>> timing measured here <<<

Input netlist is `bufexp/A.v`, the **unbuffered** mapped netlist, so this
measures `repair_design` against the same starting point the ABC control used.

## Result

| clock | before `repair_design` | after | delta |
|---|---|---|---|
| clk_a | -36.723 VIOLATED | **+17.593 MET** | **+54.316** |
| clk_b | -43.438 VIOLATED | **+12.367 MET** | **+55.805** |
| clk_e | -47.683 VIOLATED | **+19.529 MET** | **+67.212** |

**All three groups close.** Design area 448,840 to 539,351 um2, **+20.2%**,
utilization 40% to 48%. That area is the price of closure and is reported as
such, not hidden.

## The number that matters more than the deltas

Look at the *before* column against everything else this project has
published. Under the same SDC, the same netlist and the same liberty:

| | clk_a | clk_b | clk_e |
|---|---|---|---|
| OpenSTA, no parasitics (every prior number in this project) | **+1.333 MET** | -4.957 | -4.957 |
| OpenROAD, placement parasitics, before repair | **-36.723** | -43.438 | -47.683 |

**Every timing number in this project before today was a zero-parasitic
number.** The design that "meets `clk_a` at +1.333 ns" misses it by 36.7 ns
once wires exist. This is disclosed rather than buried, and it does not
invalidate the earlier comparisons, which were all baseline-versus-variant
under one consistent model. It does mean the *absolute* closure claims in
`docs/measurement-methodology.md` and `experiments/buffering_control/` describe
a model without wires, and this file is the correction.

It also makes the routing finding stronger, not weaker. Wire delay is
definitionally not an RTL problem. With parasitics in the model, the share of
the violation that no RTL rewrite can touch goes **up**.

## Set against the other levers, same group, same SDC

| lever | clk_b gain | changes RTL? | real parasitics? |
|---|---|---|---|
| best LLM RTL transform, batch 1 (P2) | +0.485 | yes | no |
| best LLM RTL transform, batch 2 (A4) | +4.925 | yes | no |
| ABC `buffer; upsize; dnsize` control | +17.557 | no | no |
| **OpenROAD `repair_design`** | **+55.805** | **no** | **yes** |

The mapping-level control understated the real pass by **3.2x**. It pointed
the right way and got the magnitude wrong, which is what a control is for.

## Equivalence, checked rather than trusted

`repair_design` is documented as buffer insertion plus gate resizing. That is
a claim, so it was checked.

**Structural, flattened on both sides so the counts are comparable:**

| | flops | buffers | inverters |
|---|---|---|---|
| before | **7,959** | 0 | 247 |
| after | **7,959** | 960 | 240 |

The flop count is **identical**, which is the property that matters: a repair
pass must add no state. 960 buffers appear and 7 inverters disappear, which is
what insertion plus resizing looks like.

A first attempt at this comparison read 5,191 versus 7,959 and looked alarming.
It was wrong: `A.v` is hierarchical and `repaired.v` is flat, and the AES core
is instantiated twice, so a raw grep counts module *definitions* on one side
and *instances* on the other. Flattening both removes the artifact. Recorded
because it is the same class of mistake as the 28,844-versus-55,413 cell count
elsewhere in this project.

**Formal: not completed. Three attempts, three tooling failures, no
counterexample.** This is an open gap, and it is stated plainly rather than
rounded up to "verified".

| attempt | what happened |
|---|---|
| `equiv_make` against the hierarchical Yosys netlist | created **86** equivalence points in a 55K-cell design, proved 0 |
| `equiv_make` against OpenROAD's own `prerepair.v` | created **1** point; `repair_design` splits nets when it inserts 960 buffers, so most internal names do not survive |
| bounded primary-output miter (`miter_repair.sv`, BMC, `multiclock on`) | aborts: standard cells read from liberty stay blackbox/whitebox and are not inlined, so there is no logic to reason about |

The first two are failures of **name matching**, which is how `equiv_make`
pairs signals. The third is a Yosys liberty-to-formal plumbing problem. None
of the three produced a counterexample or any evidence of inequivalence; they
produced no evidence at all.

So what supports the result is the structural check above (identical flop
count, buffers added, inverters reduced), the fact that both runs of the flow
reproduce every number exactly, and `repair_design`'s documented contract.
That is **weaker than the 49,923-of-49,924 internal check the ABC control
received**, and the gap between them is the honest status of this experiment.

Completing it is open work. The most likely route is functional Verilog cell
models for sky130 (`sky130_fd_sc_hd.v` from the PDK) instead of
liberty-derived whiteboxes, which would make the bounded miter run.

## Honest limits

- **Ideal clocks.** No clock tree synthesis was run, so clock network delay
  and skew are zero on both sides. This is a pre-CTS check, which is the
  standard context for `repair_design`, and it is not a post-route sign-off
  number.
- **Pre-route parasitics.** `estimate_parasitics -placement` with the
  platform's `set_wire_rc -signal -layer met1`. Estimating every signal net on
  met1 is pessimistic for long nets, which a real router would put on higher
  metal. Global routing would move these numbers.
- **One floorplan.** 40% utilization, aspect ratio 1.0, one density setting.
  No sweep, so nothing here claims those are optimal.
- **A 2022 build.** OpenROAD has moved on considerably since `f12e2f474`.
- The 20.2% area cost is measured at this utilization only.

## Reproduce

    bash experiments/openroad_repair/run.sh          # flow + both timing points
    bash experiments/openroad_repair/verify.sh       # equivalence
