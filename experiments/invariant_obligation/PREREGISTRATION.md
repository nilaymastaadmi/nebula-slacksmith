# Pre-registration: two gate defects, the two proposals they dropped, and the invariant-carrying obligation those proposals need

Registered 2026-09-13, **before any file under `tools/` is edited** and before
either proposal is re-gated. Scored in `NOTES.md` here. Predictions **R86 to
R93**.

This merges the plan's Block 7 with a defect found while deciding whether Block
7 was worth running. The defect changes what Block 7 is for, so the two are
registered together rather than one being bolted onto the other afterwards.

## What was found, with the evidence

Deciding whether Block 7 adds anything meaningful required reading the gate log
of the proposal it was meant to rescue. **Neither run-1 proposal was ever gated.**

`experiments/depth_tv80/results/run1/gates/O1/miter_prop_bmc.raw.log`:

    ERROR: Module tv80_mcode_gate referenced in module miter_prop in cell u_t
           does not have a port named halted.

`experiments/depth_i2c/results/run1/replay/gates/O1/g4.log`:

    bmc: ERROR -- Module i2c_master_bit_ctrl_gate referenced in module miter_prop
         in cell u_t does not have a po...

Both miters were instantiated with **`imem_addr`, `dmem_wdata`, `retire_insn`,
`halted`**: the ports of this project's own RV32I core, which neither `tv80_mcode`
nor `i2c_master_bit_ctrl` has.

### Defect 1: the sequential gate assumes the RV32I interface

`tools/slacksmith.py` carries per-module gate wiring as a hard-coded table with
**one entry, `aes_key_mem`**. Any other module passes no `--inputs`/`--outputs`,
and `tools/gate_proposal.py` then defaults to `CORE_OUTPUTS`, the RV32I port list,
and to `--rst rst_n`. It was invisible on every earlier design: `rv32i_core` *is*
that interface, and every `aes_key_mem` run is in the table. **Branch 1 (EQY) is
unaffected**, because EQY reads both netlists and needs no port list; branches 2,
4 and 5, the sequential miters, are affected on any module outside the table.

### Defect 2: an engine ERROR is reported as UNRESOLVED

`gate_proposal.py` sets `G4 = "UNRESOLVED"` whenever neither engine returns
PROVEN or FAIL. An engine that **errors in elaboration, before any solving**,
falls through to the same verdict as one that **ran out of budget**. That is the
failure REPORT §9 already names, where the gate printed the same line for a
solver timeout and a refutation. It has recurred one branch over.

### What they cost

| experiment | run 1 proposal | reported as | actually |
|---|---|---|---|
| `depth_i2c` | FSM re-encoding of `i2c_master_bit_ctrl` | UNRESOLVED, refused | **never gated**, interface error |
| `depth_tv80` | `onehot_mcycle_tail_case_merge` on `tv80_mcode` | UNRESOLVED, 898 s | **never gated**, interface error |

**These are the only two proposals, across both depth-dominated designs, that
actually attack path depth.** Runs 2 and 3 on both designs proposed a
`parallel_case`-style hint that synthesis already infers, or a restructuring that
made timing worse. The two proposals aimed at the structure the classifier
reported are exactly the two the gate dropped. REPORT §7.8, the pack, and both
experiments' NOTES describe them as UNRESOLVED; that is corrected in the commit
that scores this file, so the correction cites a measurement.

**Verified unaffected:** all four runs 2 and 3 were gated by EQY
(`Successfully proved designs equivalent`, `DONE (PASS)`). Their PROVEN verdicts,
their reverts and the survival tables built on them stand.

## Why the invariant obligation is now the point

The tv80 proposal's own rationale states its correctness condition:

> MCycle is a one-hot register in tv80_core (reset to 7'b0000001, thereafter only
> ever left-rotated ... both of which preserve one-hot-ness), so MCycle[5] and
> MCycle[6] can never both be set for any reachable state.

In a miter of `tv80_mcode` alone, `MCycle` is a **free primary input**. The solver
may drive `MCycle[5]` and `MCycle[6]` high together, the transform differs on
exactly that input, and a correct miter **should refute it**. The transform is
correct only under a reachable-state invariant that lives in the *parent*. That
is the obligation class this project cannot currently discharge, and it is the
one the depth-reducing proposals need.

## Protocol, in order

1. **Repair defect 1.** Derive the gated module's port list and widths from its
   own source declaration rather than from a table. Keep the `aes_key_mem` table
   entry, and assert the derived list equals it, so the derivation is checked
   against the one module whose wiring is already trusted.
2. **Repair defect 2.** An engine ERROR returns `G4 = CANNOT (engine error: ...)`,
   never UNRESOLVED.
3. **Replay the regression surface first.** `tools/verdict_regression.sh` and
   `tools/demo_check.sh` must still pass, and one `aes_key_mem` gate must return
   its previously committed verdict. **If any of those changes, stop.**
4. **Re-gate both run-1 proposals plainly**, corrected interface, no invariant.
5. **Invariant path.** Prove the declared invariant on the **parent** by
   k-induction, then assume it at the child's interface in the miter. The null
   control is not optional: **a transform known to be wrong must still fail under
   the same assumption**, or the assumption is too strong and every verdict under
   it is void.
6. **If PROVEN under the invariant**, time it through `experiments/depth_tv80/`'s
   survival harness against its already-measured 0.152 ns floor.

## Predictions

**R86.** After repair 1 the derived port list for `aes_key_mem` equals the
hand-written table entry exactly. *Prior: strong. If it misses, the derivation is
wrong and nothing after this step runs.*

**R87.** After both repairs, `verdict_regression.sh` and `demo_check.sh` pass
unchanged and the `aes_key_mem` O2 gate returns its committed verdict.
*Prior: strong.*

**R88.** Re-gated plainly on the correct interface, the tv80 proposal is **not
PROVEN**: REFUTED or CANNOT, because `MCycle` is a free input in isolation.
*Prior: strong. A plain PROVEN here would mean the rationale's invariant is not
actually needed, which is worth knowing.*

**R89.** Re-gated plainly, the `i2c` proposal is also **not PROVEN**. *Prior:
moderate. Its correctness condition has not been read yet; this is written before
reading it.*

**R90.** The invariant "at most one of `MCycle[5]`, `MCycle[6]` is set" proves on
gold `tv80_core` by k-induction within 300 s. *Prior: moderate. The full one-hot
property is stronger and may need more depth than the two-bit exclusion.*

**R91.** Under that invariant the tv80 proposal is **PROVEN**. *Prior: moderate.*

**R92.** Under the same invariant, a deliberately broken variant of the tv80
proposal (one arm's assignment swapped) is **still REFUTED**. *Prior: strong, and
if it misses, R91 is void rather than confirmed.*

**R93.** If R91 holds, the proven transform's unbuffered gain exceeds **0.456 ns**,
3x the measured floor. *Prior: weak. It is the one proposal across two designs
that attacks the path's actual depth, and that is still a weak reason to expect a
number.*

## What would stop this

- R86 or R87 missing: the repair is wrong or has changed a published verdict.
  Stop, record, and do not re-gate anything on a tool that moved.
- R92 missing: the assumption is too strong. Every verdict under it is void and
  the invariant path is reported as not yet sound.
- **Time.** This is 4 to 8 hours two days before submission. If step 5 is not
  working by 14 Sept 18:00 IST, it stops there, and the two defects and their
  corrections are reported on their own. They are worth reporting on their own.

## Scope

Two proposals, two designs, one invariant. A new obligation type demonstrated
once is a demonstration, not a method.

---

## Amendment 1, 2026-09-13: a third defect, found while building the invariant proof

**R86. CONFIRMED** before this amendment was written. The derived port list for
`aes_key_mem` equals the hand-written table exactly: inputs, outputs, clock
`clk`, reset `reset_n`. The derivation also reports `tv80_mcode` as **purely
combinational**, 6 inputs and 46 outputs, no clock, no reset, which is itself a
finding: run 1's model declared a **mapped-state** obligation (branch 4) for a
module that has no state.

### Defect 3: the gate proves a parameterised module at its defaults

Building the child obligation meant reading how `tv80_mcode` is instantiated:

    tv80s       parameter Mode = 1;              // 1 => Fast Z80
    tv80_core   tv80_mcode #(Mode, Flag_C, ...)  // passes Mode = 1 down
    tv80_mcode  parameter Mode = 0;              // its own default

`tv80_mcode` references `Mode` **42 times**. The gate reads the module on its own,
so both EQY and the miter elaborate it at **`Mode = 0`**, a different decoder
from the **`Mode = 1`** one the design contains.

**What this does and does not touch:**

- `depth_tv80` **run 2**: EQY PROVEN at `Mode = 0`. Its whole-design netlist at
  `Mode = 1` is **byte-identical to gold** in `experiments/depth_tv80/`'s
  survival table, so it is equivalent at the instantiated value regardless. The
  verdict's conclusion stands; its stated basis was the wrong elaboration.
- `depth_tv80` **run 3**: EQY PROVEN at `Mode = 0` only. **Its equivalence at
  `Mode = 1` has never been checked.** It was reverted, so no unproven RTL
  shipped, but "2 of 3 PROVEN" is overstated by one until it is.
- `depth_i2c`: **unaffected.** `i2c_master_bit_ctrl`'s `parameter`s are
  state-encoding constants in the body and it is never instantiated with `#(`.
- Every benchmark module this gate has proven (`rv32i_core`, `aes_key_mem`): no
  header parameters overridden at instantiation. **Unaffected**, and checked by
  reading, which is stated as a limit of this amendment rather than a proof.

**Not repaired in `tools/` in this block.** Threading instantiated parameters from
the parent into the gate is a real change to how every obligation is elaborated,
and R87 is mid-run on the current tool. The invariant proof below sets
`Mode = 1` explicitly, experiment-side, and run 3 is re-checked the same way.

### Predictions added

**R94.** Run 3's transform, re-checked by EQY with `chparam -set Mode 1` on both
sides, is **PROVEN**. *Prior: moderate. The transform flattens an override
priority in the tail block; whether that interacts with `Mode`-gated arms has
not been read.*

**R95.** Run 1's transform, re-gated plainly at `Mode = 1` with no invariant, is
**not PROVEN**. This replaces R88's framing: R88 is still scored on the repaired
gate as registered, which elaborates at the default, and R95 asks the same
question of the decoder that is actually in the design.

The invariant obligation (R90 to R92) is built at `Mode = 1` from the start,
because an invariant-carrying proof about the wrong elaboration would be the
same defect with more steps.
