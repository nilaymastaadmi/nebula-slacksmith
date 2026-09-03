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

**Attempt 4, 2026-09-02: real cell models, and the proof simply did not
finish.** oss-cad-suite ships sky130 functional models with its own EQY
example, plus `formal_pdk_proc.py`, the preprocessing EQY itself uses.
Coverage was checked first: 79 of 79 cell types in `A.v` and 220 of 220 in
`repaired.v` are defined, zero missing, before and after preprocessing. With
those models `prep` completed (the wall attempt 3 hit), the SMT2 model was
built in 10 s, and `yosys-smtbmc` with bitwuzla started BMC at depth 4 with
`multiclock on` across five clocks and roughly 16,000 flops. It had not
finished **step 0** after more than 60 minutes of wall time and was killed.
`timeout` had killed `sby` at 3,000 s but orphaned the engine, the same
solver-in-its-own-process-group problem `tools/run_proof.py` already handles
with a session kill; `equiv_miter.sh` now does the same.

| attempt | what happened |
|---|---|
| 4. bounded miter, real sky130 models, BMC depth 4, multiclock | reads, elaborates, solver did not complete step 0 in 60+ min; **no counterexample, no proof** |

Attempt 4 is a different kind of failure from the first three: the obligation
was correctly formed and the tool ran out of time, not out of plumbing. It
also surfaced a caveat that would have to be handled before any result from
this route could be trusted: OpenROAD's Verilog writer emits named constant
nets (`u_aes_b/one_`, `u_aes_b/zero_`, one pair per module instance, 899
connections in total) with **no drivers**, because this 2022 build has no
`insert_tiecells`. In a formal model an undriven net is a free variable, so
even a completed run would need those nets tied before a counterexample could
be believed.

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

---

# Attempt 5: PROVEN, 2026-09-03

    Found 5832 $equiv cells in equiv:
      Of those cells 5832 are proven and 0 are unproven.
      Equivalence successfully proven!

    38.10 s, 2.67 GB peak, Yosys 0.67, no commercial tool.

`repair_design`'s output is formally equivalent to its input. The pair is
the `MF16-C` arm of `experiments/max_fanout/`: OpenROAD's own `prerepair.v`
(25,920 cells) against `repaired.v` (27,578 cells), so **1,658 cells were
added and the logic is unchanged**. Script: `lec_openlane.ys`, which is
OpenLane's `scripts/yosys/logic_equiv_check.tcl` recipe adapted.

## Why four attempts failed, each for its own reason

A literature check on 2026-09-03 diagnosed all four. None of them was the
hard research problem we had assumed.

**1 and 2. `equiv_make` matches wire names, not compare points.** It walks
every wire and pairs same-named ones. Comparing a Yosys *hierarchical*
netlist against an OpenROAD *flat* one leaves almost no names in common,
because flat writing renames every instance (`b1.r1` becomes `\b1/r1`). That
is the whole explanation for 86 equivalence points in a 55K-cell design:
not a solver limit, a naming mismatch. Feeding it two netlists **both
written by OpenROAD**, in one name domain, gives **5,800** points instead of
86, a 67x increase, and shrinks every proof cone accordingly.

**3. We asked a sequential question.** A k-padded miter under `sby prove` is
k-induction over the entire design. Buffer insertion and gate resizing are
**combinational** once you cut at the flops, so we had handed the solver a
problem exponentially harder than the one we actually had.

**4. `formal_pdk_proc.py` was unnecessary.** `read_liberty` **without**
`-lib` builds real functional models from each cell's `function` attribute.
We had spent an attempt substituting models by hand that Yosys will build
itself from the same liberty file.

**And one more, found by running attempt 5 and reading the error.** Yosys'
SAT backend has no model for an asynchronous flop:

    ERROR: No SAT model available for async FF cell ($_DFF_PN0_).
    Consider running `async2sync` or `clk2fflogic` first.

Every flop in this benchmark has an async active-low reset, by the RTL's own
stated rule, so this was guaranteed to fire. `async2sync` fixes it in one
line. It is applied to the merged `equiv` module, so gold and gate are
transformed identically and the comparison stays sound. `clk2fflogic` is the
heavier alternative and is exactly what made the divider proof intractable
in `experiments/fsm_reencode/`, so the light one is also the right one.

## The insight that makes it easy

**A buffer is never a compare point.** Compare points are primary outputs,
register data inputs and black-box inputs. Insert ten thousand buffers and
you add zero compare points; you only lengthen combinational cones, which
structural hashing collapses. The compare-point set is fixed by the flop and
port set, and `repair_design` changes neither. That is why commercial LEC
tools treat post-placement netlists as routine, and why this should always
have been a 38-second job.

## What this does and does not establish

**Does:** the logic of this netlist pair is unchanged. The +55.805 ns and
+40.665 ns physical results are no longer an unverified transformation.

**Does not:** prove `repair_design` correct in general. This is
**translation validation per run**, re-proving each pair rather than proving
the algorithm, which is exactly what OpenROAD itself does and what the
industry does. It also says nothing about whether the timing improvement is
real; that is a separate claim resting on separate evidence.

**Not yet run on every pair.** Only `MF16-C` is proven. The check is cheap
enough to run on all of them and that is the obvious next step.

## The route we did not need

OpenROAD's current flow uses **kepler-formal** (GPL-3.0) for exactly this
check, wired into `flow/scripts/cts.tcl` after `repair_timing`, and its
`src/tst/include/tst/lec.h` records that the older EQY-based harness sat
inert for years for the same name-matching reason we hit. Worth knowing, and
we did not need it: the Yosys already in this repository was enough.

## The boundary of this method, measured not assumed

Two controls were run through `tools/lec_check.py`:

| pair | what differs | result |
|---|---|---|
| `prerepair.v` vs `repaired.v` | `repair_design` added 1,658 cells | **PROVEN**, 5,832 points, 38 s |
| flat arm C vs flat arm E | two independent ABC runs, different scripts | **TIMEOUT at 1,800 s** |

The second is the honest limit. Arm C and arm E come from the same RTL and
are almost certainly equivalent, but each was technology-mapped by its own
ABC invocation, so cell and net names diverge everywhere. `equiv_make` pairs
wires by name, finds few anchors, and the proof cones become the whole
design again. **Thirty minutes without a verdict is not evidence of
inequivalence**; it is evidence that this method does not reach that case.

This is exactly the precondition the OpenROAD flow states for gate-level
LEC: no change of sequential boundaries, and no change in the names of
hierarchical instances, sequential instances and top terminals.
`repair_design` satisfies it because it only inserts buffers and resizes
gates. A fresh ABC mapping does not satisfy it at all.

**So G6 is wired into the OpenROAD engine and not into the ABC path**, and
that was a measurement rather than a guess. The ABC buffering lever in the
`sta` engine remains unverified, and the report says so.

## Every arm, not just one

`lec_all_arms.sh` re-runs each `repair_design` arm this project reports and
proves its own netlist pair. Results in `lec_arms/summary.tsv`.

| arm | SDC | verdict | compare points | unproven | seconds |
|---|---|---|---|---|---|
| OR-C | v3 | **PROVEN** | 5,832 | 0 | 43 |
| OR-E | v3 | **PROVEN** | 5,832 | 0 | 39 |
| MF16-E | v3 + max fanout 16 | **PROVEN** | 5,832 | 0 | 40 |
| MF8-E | v3 + max fanout 8 | **PROVEN** | 5,832 | 0 | 41 |
| MF32-E | v3 + max fanout 32 | **PROVEN** | 5,832 | 0 | 40 |
| MF16-C | v3 + max fanout 16 | **PROVEN** | 5,832 | 0 | 38 |

**Six of six, 0 unproven, under 45 seconds each.** So every physical result
this project reports is now formally proven equivalent to the netlist it was
given, not just the one pair checked first.

The compare-point count is identical across all six, which is the expected
consistency signal rather than a coincidence: compare points are flops and
ports, all six arms come from the same RTL, and `repair_design` changes
neither. An arm that came back with a different count would mean the flow had
altered the sequential boundary, which is exactly the precondition this check
requires.
