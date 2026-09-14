# Depth-dominated survival: results

Registered in `PREREGISTRATION.md` (commit `86691c1`) before any run; amendment
1 (commit `ea9604e`) registered after run 1 and before any re-gating. This
file is the scorecard. Raw material: `results/runN/` (request, verbatim reply,
variant, gate logs, decision log), `results/runN/replay/` (the replay through
the repaired loop), `results/survival.tsv` (phase 2), and `score.py`, which
computes every phase-2 number quoted below.

## Phase 1: three unattended runs, no `--force-lever`

| run | proposal | branch | model time | in-loop verdict, original harness |
|---|---|---|---|---|
| 1 | `onehot_fsm_case_to_reachable_shift_decode` | 4 | 991 s | **G1 FAIL**: `` undefined macro `I2C_CMD_STOP `` |
| 2 | `parallel_case_attribute_on_fsm_decode` | 1 | 297 s | **G4 PROVEN** (EQY), then `skip: target experiments/depth_i2c/rtl/i2c.v not in the file list` |
| 3 | `parallel_case_attribute_on_fsm_decode` | 1 | 252 s | **G1 FAIL**: the same undefined macro |

`lever_forced: false` and `routed_lever: rtl` in all three decision logs.

**R54. CONFIRMED.** The router selected RTL unforced in 3 of 3.

**R55. CONFIRMED.** Run 2 reached `PROVEN` inside the loop, on branch 1, in
297 s end to end.

**R63. CONFIRMED.** Two of three proposals used a file-scope macro and failed
G1 on the original harness.

### The two harness defects, both predicted in writing before run 2 was read

Amendment 1 was registered from run 1's failure alone. It named two defects
and predicted that a proven proposal would be skipped by the second. Run 2
then did exactly that: `G4=PROVEN`, `skip`, and the loop printed "no proposal
passed the gate" over a proposal that had.

1. **Gate assembly.** `tools/proposer.py` wrote the model's bare module as the
   whole variant file, so the gate copy lacked the five file-scope `` `define ``
   lines the gold copy carries. Runs 1 and 3 returned a bare module and failed;
   run 2 happened to return the whole file and passed. The verdict depended on
   how much text the model chose to echo.
2. **Apply key.** `tools/slacksmith.py` derived the file key by stripping a
   literal `rtl/`. With `--rtl-dir experiments/depth_i2c/rtl` the key never
   matched, so a proven proposal was gated and never applied or timed.

A third site of the same assumption, G7's "module not in the file list", is
noted and left alone: `i2c_master_bit_ctrl` has no clock crossings, so the
verdict (`SKIPPED`) is right for the wrong reason, and repairing it mid-run
was not registered.

**Repair** (after run 3 exited, so the three samples share one harness):
`splice_module()` splices a bare module back into its file whenever the file
declares more than one module or carries file-scope defines, and leaves a
whole-file variant alone; the apply key is derived relative to `--rtl-dir`.
Both reduce to the old behaviour on `bench_top`, which is R62's claim.

### What the model did on a design it had never seen

Run 2 and run 3 converged on the same transform from independent samples: the
RTL carries `// synopsys full_case parallel_case` comments that Yosys ignores,
so the one-hot `case` arms elaborate with an implicit priority order and ABC
builds the serial `or4/nor4/o41ai` chain on the critical path. The proposal
replaces the dead comment with a real `(* parallel_case *)` attribute on both
case statements: two lines, k = 0, combinational equivalence, and EQY proves
it. It is logic restructuring by attribute rather than by rewrite. Run 1's
proposal is the more ambitious one, an FSM re-encoding on branch 4, and its
fate is in the replay below.

## Amendment 1: the replay through the repaired loop

| run | replay verdict | then |
|---|---|---|
| 1 | G1 PASS, G2 PASS, G3 PASS (state-remap), ~~G4 UNRESOLVED at the 420 s budget~~ **never gated**: elaboration error on the RV32I port list, reported as UNRESOLVED (corrected 2026-09-13, `experiments/invariant_obligation/`); re-gated on the right interface it is REFUTED, uncorroborated | refused |
| 2 | **G4 PROVEN**, EQY | **applied**, re-measured **−0.396**, **reverted** on G5 |
| 3 | **G4 PROVEN**, EQY; the spliced variant is byte-identical to run 2's | applied, re-measured −0.396, reverted |

**R61. CONFIRMED.** Run 1's proposal passes G1 and G2 under the repair, and
its own fate is the model's: an FSM re-encoding the sequential miter cannot
decide inside the budget, so the loop refused it.

**R62. CONFIRMED.** `verdict_regression.sh`: P4 REFUTED, A2 UNRESOLVED.
`classify_regression.py`: 5 of 5. The spliced variant for `cli_backend`'s O1
is byte-identical to the committed file (`splice_module` returns None on
every `bench_top` source).

**For the first time the loop ran end to end on a design it never saw, with no
flag and no human**: measure, classify, route to RTL, propose, prove, apply,
re-measure, revert. Every decision in that chain was correct. The number it
reverted on is 0.000.

## Phase 2: the survival table (`results/survival.tsv`, `score.py`)

| variant | A unbuffered | B after ABC lever | C before repair | C after repair | cells A | area after |
|---|---|---|---|---|---|---|
| gold | −0.396 | +0.581 | −1.092 | +0.041 | 560 | 6,648 |
| control, two always blocks exchanged | **−0.820** | +0.492 | −2.140 | **−0.187** | **587** | 6,437 |
| run 2 proposal | −0.396 | +0.581 | −1.092 | +0.041 | 560 | 6,648 |
| run 3 proposal (same file) | −0.396 | +0.581 | −1.092 | +0.041 | 560 | 6,648 |
| gold, second OpenROAD run | | | −1.092 | +0.041 | | 6,648 |

**The proven transform is a synthesis no-op.** The mapped netlists of gold
and the proposal are **byte-identical** at A and at B (`cmp`). Yosys already
elaborates a `case` over distinct one-hot constants as parallel; the
`(* parallel_case *)` attribute the model added, twice, from two independent
samples, changes nothing the mapper sees. It is provably equivalent, plausibly
motivated, and worth exactly 0.000 ns at every level.

**R56. WRONG.** +0.000, not more than +0.050.
**R57. VOID.** There is no unbuffered gain for the lever to take away.
**R58. WRONG.** +0.000 after repair.
**R59. WRONG, and this is the instrument finding.** The do-nothing control
moves post-repair slack by **−0.228** and unbuffered slack by **−0.424**, 12%
of the 3.560 ns period, and changes the mapped cell count from 560 to 587.
Exchanging two `always` blocks in source order is enough to re-map a 560-cell
design. The registration assumed a small design has a small floor; in
relative terms it is the reverse. Any RTL gain on `i2c` would have to clear
0.4 ns unbuffered to be visible at all.
**R60. CONFIRMED.** Gold through the OpenROAD flow twice: identical.

## What this establishes, and what it does not

**Established.** The two-router loop works unforced on external IP, and its
gate and its acceptance bar are both load-bearing: one proposal refused as
undecidable, one proven and reverted for buying nothing. The three harness
defects that stood between "PROVEN" and "applied" were named in writing from
run 1's failure and confirmed by run 2 before they were touched (amendment 1).

**Not established.** The depth-dominated cell of the survival table is
**empty**. The engine produced no gain on this design, so whether an RTL gain
survives the physical lever where the classifier says RTL is the lever remains
unmeasured. The fanout cell is filled (0% survival, N = 5 netlists,
`composed_rtl/`); with one cell the classifier is a cost-saver, not a
demonstrated decision procedure, and REPORT §1 says so.

**The registration's own gap.** The fallback declared a handoff-tier proposal
only if *no* unattended proposal reached PROVEN. One did, and it was worth
zero; no fallback was registered for "proven and zero", so none was run.
Recorded as a gap in the registration rather than patched after seeing the
result. The transform that would test the depth cell is run 1's: a per-bit
one-hot decode, correct only under the reachable-state invariant, which needs
the invariant injected into the miter (`experiments/onehot_invariant/` has the
lemma) and is not built.

**The instrument.** `i2c` at 560 cells is too small for this measurement: a
null edit moves it by more than any plausible transform. The next design for
this cell needs a perturbation floor measured *before* it is chosen, on the
order of a few thousand cells, with the control run first.

Scorecard for this directory: R54, R55, R60, R61, R62, R63 CONFIRMED; R56,
R58, R59 WRONG; R57 VOID. Counts by `tools/tally_predictions.py`.
