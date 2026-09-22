# Pre-registration: the six classical arms

Written 2026-09-21. **Committed before any arm code exists.** Provable:

    git log --diff-filter=A --format='%ad %h %s' --date=iso -- \
      closureduel/PREREGISTRATION.md closureduel/arms/

## What this is, and what it is not blind to

The question: on an open stack, with the container pinned in `SPEC.md` 2.4,
what does each classical arm do to register-to-register timing on the 10
development designs? This is the classical half of the head-to-head in
`SPEC.md` 2.0. No LLM arm runs in this registration.

**These predictions are not blind, and are not presented as blind.** The
transfer study (`experiments/drrtl_transfer/`) already measured the buffering
and sizing levers on these designs, on a 2022 OpenROAD and a dirty Yosys 0.67
build, and its per-tier medians are quoted in `VISION.md`. What is new here is
the container toolchain, `repair_design` as an arm, the classifier routing as
one arm, the random arm, and the legality gate. Predictions about C2 and C3 are
therefore consistency predictions across a toolchain change, and are scored as
such. The holdout designs have never been run through any of these arms and are
not run now.

## Designs

The 10 development designs from `SPEC.md` 2.3, by tier (corrected classifier):

| Tier | Designs |
|---|---|
| FANOUT | cpu_fsm, aes, communication |
| MIXED | tv80, router |
| DEPTH | ticket_machine, DSP, i2c, vending_machine, cpu_pipe |

The 5 sealed designs (arm_cpu2, datapath, arm_cpu1, simple_spi, controller)
are refused by the harness and are not run.

## Measurement, fixed before any arm runs

- **Flow.** Everything runs inside `closureduel:dev`. Synthesis is the
  committed run-1 flow (`experiments/drrtl_transfer/run_classify.sh`, as
  mirrored in `docker/smoke.sh`): `synth`, `dfflibmap`, `abc -liberty` with the
  `dont_use` exclusion, `opt_clean -purge`, `write_verilog -noattr`.
- **Clock period per design.** `round(0.9 x required, 3)`, where `required` is
  measured on the C0 netlist at a 1000 ns clock, exactly as the committed flow
  defines it. Fixed once from C0 and used for every arm on that design. By
  construction C0 misses timing on every design.
- **WNS.** Worst register-to-register slack at that period, measured by the
  same Tcl as `docker/smoke.sh` (`report_checks -from [all_registers
  -clock_pins] -to [all_registers -data_pins]`). I/O paths are excluded, as in
  the committed flow, because the SDC constrains none.
- **TNS.** OpenSTA `report_tns` at the same period.
- **Area.** Yosys `stat -liberty` "Chip area" on the final netlist, the same
  command for every arm, including C1's OpenROAD-written netlist.
- **Flops.** Count of sky130 sequential cells in the final netlist.
- **Wall clock** per arm per design, measured, not estimated.
- **Closure** means WNS >= 0 **and** the submission is legal.

## Legality, the `SPEC.md` 2.1 bar applied to classical arms

A candidate netlist is legal only if all four hold:

1. It synthesises (or, for C1, OpenROAD writes it) without error.
2. **CEC against the C0 netlist is PROVEN**, using the committed G6 recipe
   (`experiments/openroad_repair/lec_openlane.ys`, 5,832 points proven in
   38.10 s): liberty functional models, `flatten`, `equiv_make`,
   `async2sync`, `equiv_struct`, `equiv_simple -seq 10`,
   `equiv_induct -seq 4`, `equiv_status -assert`. Timeout 300 s. Outcomes are
   PROVEN, FAILED or UNRESOLVED; **UNRESOLVED is not legal** and is reported as
   its own class, never folded into PROVEN.
3. The top module's port list (names, directions, widths) is identical to C0's.
4. Area <= 1.20 x C0 area.

**The CEC gate must be shown failing before any verdict it gives is used**
(`research-integrity` section 9): one planted functional defect in a copy of a
C2 netlist must come back FAILED, and the unmodified copy PROVEN. If it cannot
be made to fail, every legality verdict in this study is VOID.

## The arms

Each definition cites code committed before today. None was chosen after
seeing a result of this study.

| Arm | Definition | Source |
|---|---|---|
| **C0 null** | The synthesis flow above with the default `abc -liberty`. No transform. | `run_classify.sh` run-1 flow |
| **C1 repair_design** | C0's netlist into OpenROAD; tech and cell LEF; liberty; `create_clock` at the design's period; stock `repair_design -pre_placement`, no other options. **No placement and no parasitics.** If OpenROAD requires a floorplan to insert buffers, `initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2.0 -site unithd` (the committed values) is allowed and recorded; placement is not. | `experiments/openroad_repair/run.sh` (commit 567cb4e era), minus placement |
| **C2 buffer-only** | `abc -script` with `HEAD;buffer,-N,16` | `experiments/drrtl_transfer/phase3/run.sh` line 15, ab8762e |
| **C3 sizing-only** | `abc -script` with `HEAD;upsize;dnsize` | same file, line 16 |
| **C4 classifier-routed** | Classify C0's critical path with `tools/classify_path.py`. FANOUT or MIXED: apply buffering; keep it only if WNS improves, else revert; then apply sizing on top of whatever was kept; keep only if WNS improves. DEPTH: apply sizing; keep only if WNS improves. Kept buffering plus sizing is `HEAD;buffer,-N,16;upsize;dnsize`. | `tools/slacksmith.py` `choose_physical` and `abc_script_for`, 2094112 |
| **C5 random** | Action space: the committed levers' own tokens, `{buffer -N 16, upsize, dnsize}`. A candidate is `HEAD` plus a sequence of length L, L uniform on {1,2,3}, tokens uniform with replacement: 39 possible sequences. Budget: 8 candidates per seed, the agent iteration cap in `SPEC.md` 2.1. The seed's result is its best **legal** candidate by WNS, or C0 if none is legal. Seeds 1 to 10, drawn with `random.Random(f"{design}:{seed}")`. | new; action space from the committed tokens |

`HEAD` is `+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put`,
verbatim from `phase3/run.sh` line 14.

**C1's missing placement is a stated limit, not a choice made after seeing
data.** The committed `repair_design` runs followed global placement and
placement parasitics. That is out of scope for this project (`VISION.md`
question 5, item 2), and its slack numbers would carry wire delay the other
arms do not, so the two could not share one table. A placed `repair_design`
arm is a v2 item.

**C5 is implemented by evaluating all 39 sequences once per design** and
answering each seed's 8 draws by lookup. This is equivalent to running each
draw only if evaluation is deterministic, which prediction P10 tests on every
sequence; if P10 fails, C5 is re-run draw by draw. The best of all 39 is
reported as the lever-space ceiling **C\***, which is a bound on any policy
over this action space and is **not an arm**.

## Determinism, and why the classical arms get one trial

Every deterministic arm (C0 to C4, and every C5 sequence) is run twice per
design. Two runs must give byte-identical netlists and identical WNS, TNS,
area and flop count. An arm that fails this is reclassified as stochastic and
reported with 10 trials, and the power analysis in `SPEC.md` 2.5 is recomputed
with its spread.

## The trivial baselines

- **For every arm: C0.** An arm that does not beat C0 has no effect.
- **For C4's routing, which is the contribution:** C5 at 8x the evaluations,
  and the per-design oracle `max(C2, C3)`. C4's routing is a contribution only
  if it closes at least as many designs as C5's median seed **and** matches the
  oracle's choice on a majority of designs. If it loses to C5, the finding is
  reported as "the classifier's routing adds nothing over random selection from
  the same levers at 8x the budget", prominently.

## Predictions

| # | Prediction | Confidence |
|---|---|---|
| P1 | C0 closes 0 of 10. This is a wiring check on the period construction. | near-certain |
| P2 | The container's C0 `required` equals the committed transfer-study value within 0.001 ns on at least 9 of 10 designs. | medium |
| P3 | C1 changes WNS by less than 0.05 ns on at least 8 of 10 designs: with no parasitics and a create_clock-only SDC there is little for `repair_design` to repair. | medium |
| P4 | C2 closes at least 2 of the 3 FANOUT designs. | medium-high |
| P5 | C2's median WNS gain over C0 on the 5 DEPTH designs lies within +/-0.05 ns of zero. | medium-high |
| P6 | C3 improves WNS over C0 on at least 4 of the 5 DEPTH designs. | medium |
| P7 | C4 closes at least as many designs as the better of C2 and C3 applied uniformly. | medium |
| P8 | **C5's median seed closes at least as many designs as C4.** A prediction against the contribution: 8 draws from 39 sequences will usually include the full `buffer;upsize;dnsize` chain. | medium |
| P9 | Every C2 to C5 candidate that synthesises is CEC PROVEN: Yosys hands ABC only combinational logic, so `scorr` and `dretime` inside the script cannot move a flop. | high |
| P10 | Every deterministic arm and every C5 sequence is byte-identical across two runs on all 10 designs. | high |
| P11 | The container's classifier verdict equals the committed corrected verdict (`results_reclassified/summary.tsv`) on 10 of 10 designs. | medium |

## Pass, fail and void

This registration characterises arms; it does not test a single hypothesis, so
"pass" and "fail" apply per prediction and are tallied. The study as a whole is
**VOID**, and no arm result is reported as a finding, if any of these holds:

- P1 fails: some C0 closes, so the period construction is broken.
- The CEC gate cannot be shown failing on the planted defect.
- An arm is non-deterministic and was not reclassified and re-run.
- Any holdout design reaches any arm.

If the container's C0 disagrees with the committed transfer study on a design
(P2), the container's number is the benchmark number; the disagreement is
reported as a toolchain effect, not resolved in either direction.

## Multiple comparisons

Six arms on 10 designs, one trial per deterministic cell. **No significance
claim is made in this registration.** C4 against C5 is reported as a
distribution over 10 seeds, with no p-value. Significance testing belongs to
the head-to-head with the agent arms, at the trial count `SPEC.md` 2.5 derives.

## What would make this void, restated for the diff

- Editing any arm definition, the period rule, the legality bar or a
  prediction after any arm has run.
- Adding or dropping a design after any arm has run. A design that fails to
  synthesise or time is reported as failed, not replaced.
- Reporting C\* as an arm.

## Amendment 1, 2026-09-21: a counterexample search beside the CEC gate

Written after 136 of 400 equivalence checks had returned and **before any arm
was scored**. What had been seen, disclosed in full: on `aes`, all 25
sequences containing `buffer` returned NOT_PROVEN with exactly 1 unproven
point, and all 15 others (the 14 sizing-only sequences and C1) PROVEN; on
`cpu_fsm`, the same 25 timed out at 300 s and the other 15 PROVEN;
`communication` proved all 40; `router` was partial, with C1 NOT_PROVEN at 29
points. The pattern tracks structure: sizing changes cell drive strengths and
leaves the netlist's structure intact, so the checker's structural pass proves
it; buffering changes structure and forces SAT through large cones. That
suggests a limit of the checker rather than real inequivalence, **and it is not
shown**.

**The registered verdict is unchanged.** A candidate that is not PROVEN is not
legal, and the primary results score it as CEC_FAIL (NOT_PROVEN) or
CEC_UNRESOLVED (TIMEOUT). Nothing here relaxes the gate.

**Added, and reported separately:** for every candidate whose check is not
PROVEN, a bounded counterexample search on a miter of the C0 netlist and the
candidate (liberty functional models, `flatten`, `miter -equiv
-make_assert`, `async2sync`, `sat -verify -prove-asserts -set-init-zero
-seq 10`, timeout 600 s). Outcomes: COUNTEREXAMPLE (a real input sequence on
which the two differ within 10 cycles of a common zero state), NONE_WITHIN_10
(no difference found; not a proof), or INCONCLUSIVE (timeout or error).

- **The search must be shown finding a counterexample first**, on the planted
  defect in `results/cec_gate_test.json`'s design. If it cannot find that one,
  every NONE_WITHIN_10 it reports is uninformative and is labelled so.
- **A sensitivity table** re-scores the arms treating NONE_WITHIN_10 as legal,
  printed under a heading that says it is not the registered result. The
  registered table stays the headline.

**Prediction P12** (registered now, after seeing the pattern, so weaker than
P1 to P11): no buffer-containing candidate yields a COUNTEREXAMPLE. High.

### Amendment 1, outcome of its control (2026-09-22, still before any arm is scored)

- **The search finds real defects.** On the planted DSP defect it returned
  COUNTEREXAMPLE in 110 s (`results/cex_control.json`, and the log line
  "Called with -verify and proof did fail!").
- **It cannot clear a correct netlist at this size.** On the unmodified DSP
  netlist (2.9k cells, proven equivalent by the CEC gate in 4 s) it hit the
  600 s cap without finishing 10 cycles. So on the larger designs, where the
  unproven candidates are, a NONE_WITHIN_10 is unreachable in budget, and the
  `--all` sweep (about 100 candidates, up to 4 hours) would return mostly
  INCONCLUSIVE. **It is not run.** The sensitivity table in amendment 1 is
  therefore not produced; this is recorded, not quietly dropped.
- **Direct diagnosis instead, on one case.** For `aes` with `buffer` alone, the
  CEC gate compares 1,409 points and proves **1,408** (every `o_expanded_key`
  bit). The single unproven point is `o_done`, and it fails in the induction
  step ("Proof for induction step failed"), not in the base case: the checker
  cannot pair the renamed counter state behind it, and induction then ranges
  over counter states that are never reached. That is the false-alarm mode
  the existing SlackBench exam already documented for induction, and it is
  **evidence, not proof**, that this candidate is equivalent.
- **A PDR proof was attempted and is not used.** Three versions of a
  hand-built miter failed their controls (unreadable AIGER; a multi-output
  property that flagged the known-equivalent pair; a miter that collapsed to
  zero logic). None produced a verdict that counts. The next attempt should
  reuse the PDR miter recipe already validated in `experiments/slackbench/`,
  not a new one.

**The registered verdict is unaffected by any of this**: a candidate that is
not PROVEN is not legal, and the primary table scores it so.

## Amendment 2, 2026-09-22: a second equivalence checker, PDR on a miter

Written after all 400 registered checks and the scoring, **before this checker
has run on any study candidate.** Seen when writing it: the registered results
(`results/RESULTS_classical.md`), the aes diagnosis in amendment 1's outcome,
and the counterexample-search control. Nothing from PDR on a study candidate.

**The registered result is unchanged and stays the headline.** This adds a
second opinion on the 195 candidates the registered gate did not prove (189
lever sequences and 6 C1 netlists), reported in a separate table labelled as
not the registered result.

**Method:** the PDR checker already validated in `experiments/slackbench/`
(`check_miter_pdr`: SBY `mode prove`, engine `abc pdr`, a Verilog miter module
asserting every output equal), implemented in `arms/pdr_check.py`. Two
adaptations for gate-level netlists: each side is read with liberty functional
models and flattened before renaming; and the start state is all-zero on every
flop in both copies (`setundef -zero -init`) rather than a forced reset,
because reset ports differ in name and polarity across designs and both sides
share one flop set. Timeout 600 s per check. Outcomes PROVEN, COUNTEREXAMPLE,
UNRESOLVED, ERROR; ERROR is never read as a verdict.

**Controls, which must all pass before any study candidate runs** (the script
refuses otherwise): the planted DSP defect gives COUNTEREXAMPLE; the unmodified
DSP pair (registered PROVEN) gives PROVEN; aes sizing-only (registered PROVEN)
gives PROVEN.

**Second table:** a candidate counts as legal there if it is registered PROVEN
or PDR PROVEN, and meets the other three legality conditions. A PDR
COUNTEREXAMPLE is reported prominently, as a real inequivalence in a
candidate the committed levers produced.

**Predictions, registered after seeing the gate's pattern, so weaker than P1
to P11:**

| # | Prediction | Confidence |
|---|---|---|
| P13 | No candidate gets a COUNTEREXAMPLE: ABC's buffering and sizing preserve function, and the registered failures are checker limits | high |
| P14 | PDR settles (PROVEN or COUNTEREXAMPLE) at least half of the 195 within 600 s | medium-low |
| P15 | Under the second table, C2 closes all 3 FANOUT designs, as its timing already shows | medium |
