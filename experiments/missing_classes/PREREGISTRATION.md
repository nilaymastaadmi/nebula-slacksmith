# Pre-registration: the two optimization classes the engine never proposed

Registered 2026-09-11, **before** `tools/gate_proposal.py` is modified and
before any variant RTL for this experiment exists. Ordering is provable:

    git log --diff-filter=A -- experiments/missing_classes/PREREGISTRATION.md
    git log -- tools/gate_proposal.py

## Why this experiment exists

An external organiser-persona review of the submission (`REVIEW_RESULT_2026-09-11.md`,
run against `REVIEW_PROMPT.md`) scored objective O3c **MISSING** and O3d
**PARTIAL**:

> **Retiming.** Not recommended by the engine at any point. Present only as an
> ABC mapping pass. The k=0 mapped-state branch could carry a register-move
> obligation and does not.
>
> **FSM optimization.** Not recommended by the engine. The one-hot re-encoding
> exists to exercise obligation branch 4 and was written by the authors.

The problem statement names four optimization classes: pipelining, logic
restructuring, retiming, FSM optimization. Two of four have never been
proposed by the proposer.

The prior explanation on the record was that they had not been written. That
explanation is not tested. This experiment tests a different one.

## Hypothesis

**H.** The two missing classes are missing for the same structural reason:
`gate_proposal.py`'s G3 check requires

    k == 0  =>  dff_delta == 0
    k >  0  =>  dff_delta >  0

and **both** missing classes are `k == 0` with `dff_delta != 0`.

- **Retiming** moves a register across combinational logic. Latency is
  unchanged (k=0) and the flop count changes by design.
- **FSM re-encoding** binary to one-hot changes `state_r` from `[3:0]` to
  `[9:0]`, so `dff_delta = +6` at `k = 0`.

If H holds, no proposal in either class can pass G3, whatever its content, so
the proposer was never able to express one and the absence is a property of
the obligation router rather than of the proposals. The project's existing
one-hot result (`experiments/fsm_reencode/`) would then be hand-built
**because** it could not go through the gate, which matches the fact that that
directory carries its own `miter_mapped.sv` and `miter.sby` and never invokes
`gate_proposal.py`.

## Predictions

Scored on outcome, including the ones expected to miss.

| # | prediction | prior |
|---|---|---|
| **R1** | The unmodified gate rejects a *correct* retiming of `domain_b` at G3 with `FAIL(declared k=0 but flop count changed by ...)`, never reaching G4. | high, read from source; low information, registered so the claim is demonstrated rather than asserted |
| **R2** | The unmodified gate rejects the project's existing one-hot `domain_b` for the **same** G3 reason, `dff_delta = +6`. | high; this is the load-bearing half of H, because it makes the defect account for both classes and not just one |
| **R3** | With a `retime` obligation branch added (k=0, flop delta unconstrained, discharged by the **sequential** miter rather than EQY), a correct retiming of `domain_b` reaches **PROVEN** within the existing 240 s timeout. | genuinely uncertain; `domain_b` carries a 16-bit LFSR and a 16-bit accumulator and the miter is unbounded in state |
| **R4** | An **incorrect** retiming, a register moved across a fork without replicating it, is **REFUTED with a counterexample** by the new branch, not UNRESOLVED. | this is the falsification test. If R4 misses, the new branch is a rubber stamp and R3 means nothing |
| **R5** | The retimed variant does **not** improve its own path group's WNS. | expected to be scored a miss for the transform and a hit for the prediction. `clk_b`'s critical path is fanout-dominated (58.9% to 98.95% attributable, `experiments/classify/`), and moving one 4-bit register will not touch that |
| **R6** | Routing on the declared transform class rather than on `k` alone changes **no** previously recorded verdict for any of the 14 existing proposals, because all 14 declare a class that still routes where it routed before. | must hold or the fix has rewritten history |

## What counts as a result

- H is **supported** only if both R1 and R2 land. R1 alone shows a hole for
  retiming; R1 and R2 together show one rule accounts for both named classes.
- The new branch is **sound** only if R4 lands. A branch that proves everything
  proves nothing, and this project has already shipped one gate that
  manufactured a refutation (`REPORT.md` §9).
- A refuted or timing-negative proposal is a **reported outcome**, not a reason
  to re-propose. If a proposal is refuted it stays refuted in the record.

## Proposer boundary

Both proposals are generated through `tools/proposer.py --proposer handoff`
against live loop state. The request file and the response JSON are committed.
As in `experiments/online_proposer/`, the proposer is shown the timing report
and the RTL and is **not** shown counterexamples, G4 verdicts, or the contents
of this registration's predictions.

## Standing conflict

The variant RTL, the gate change and this registration are written by the same
session, as in every registration in this repository.

---

## Amendment 1, 2026-09-11, after R2 and before any gate change

Two facts found while running R2 that this registration did not anticipate.
Recorded here rather than folded silently into the hypothesis.

**1. R2's mechanism is confirmed, its magnitude was wrong.** Predicted
`dff_delta = +6` from `state_r` widening `[3:0]` to `[9:0]`. Measured **+12**
(gold 84 flops, gate 96) after `synth`, so the re-encoding costs more flops
than the state register alone. The prediction is scored a **hit on the
mechanism and a miss on the number**; only the sign mattered to H, but the
number was stated and was wrong.

**2. The frozen proposer prompt offers a branch the gate does not implement.**
`tools/proposer_prompt.md` presents the proposer with four obligation branches
and tells it to declare the one its transform needs. Branch **4
(mapped-state equivalence)**, described in the template as "you re-encoded
state, e.g. binary to one-hot", is `latency_delta_k = 0`. Every `k = 0`
proposal in `gate_proposal.py` is routed to EQY, and any proposal that
re-encoded state has `dff_delta != 0` and is killed by G3 before its declared
branch is ever consulted.

So the two missing classes have **two different causes, not one**:

| class | cause |
|---|---|
| FSM optimization | **offered and unimplemented.** A proposer that followed the template and declared branch 4 was guaranteed a G3 rejection |
| retiming | **never offered.** The template has no retiming row, so it was not in the proposer's vocabulary at all |

This is a sharper result than H as registered, which supposed one rule. H is
**revised**: one G3 rule makes both classes unreachable, and a second defect,
an unimplemented branch advertised as available, makes the FSM case worse than
unreachable because it was invited.

**3. Consequence for the prompt.** `tools/proposer_prompt.md` is frozen to
`experiments/online_proposer/`, whose registration lists editing it as a void
condition. It is **not edited**. This experiment adds
`tools/proposer_prompt_v2.md` and the O1/O2 results stay attached to v1.

**4. New prediction, registered now, before the gate is changed.**

| # | prediction |
|---|---|
| **R7** | Implementing branch 4 lets the project's existing one-hot `domain_b` (the PROBE above, unchanged RTL) reach a verdict through `gate_proposal.py` for the first time, and that verdict is **PROVEN**, agreeing with the hand-built `miter_mapped.sv` result already in `experiments/fsm_reencode/`. If the two disagree, one of the two miters is wrong and that is the result. |

---

## Amendment 2, 2026-09-11, after the request was written and before its verdict

**1. The loop did not bind `domain_b`.** This registration assumed the `clk_b`
proposal would target the 10-state FSM. Live state disagreed: at iteration 1
the `clk_b` critical path is inside **`aes_key_mem`**, 30.602 ns across 9
cells, fanout share **0.9139**, with a `nor4_1` at **300 loads** carrying
21.029 ns. The loop was not steered to a different module to suit the
registration. R3, R4 and R5 are therefore scored against **`aes_key_mem`**,
which is the harder and more honest test because it is the design's real
binding path rather than a block chosen for being convenient.

Proposal **O1** is a forward retiming of `round_ctr_reg` across the `key_mem`
write decoder, declared branch 5, flop delta declared positive at k = 0.

**2. Proposer contamination, disclosed.** Before this request was written, the
session had already seen `PROBE_fsm` return **PROVEN** through the new branch 4.
That is a G4 verdict on a transform of `domain_b`, so a proposer writing an FSM
proposal for `domain_b` in this session **would not be blind**. Consequences,
adopted now:

- The FSM proposal in this experiment **may not be the binary-to-one-hot
  re-encoding**, whose verdict is known. It must be a different FSM transform.
- `PROBE_fsm` is reported as a **probe of the gate**, not as a proposal, and is
  excluded from any proposal count.
- R7's result stands as evidence about the *gate* (branch 4 reaches a verdict
  at all, and agrees with the hand-built miter), not as evidence about the
  *proposer*.

**3. R5's bar, stated before the number exists.** R5 predicted the retimed
variant does not improve its own group. The classifier puts **91.4%** of this
path's delay in fanout, and this transform does not reduce fanout: it moves the
decoder off the launch-to-capture path while the 300-load net remains. So the
registered prediction is **no material improvement**, and any improvement at
all would be evidence against the project's own fanout thesis and would be
reported as such.

---

## Amendment 3, 2026-09-11: O1's refutation is void, and it is the gate's fault

**What happened.** O1 came back `G4=REFUTED`, `eq_round_key`, BMC 1 s. Per this
project's standing rule that a refutation is read before it is reported, the
counterexample was inspected. The witness assigns **different arbitrary initial
values to the two instances' `key_mem` arrays**.

**Null control, the one this project's own methodology requires.** The miter
was re-run with the gate replaced by the gold module renamed:

| miter | result |
|---|---|
| gold vs **gold**, all three outputs | **FAIL `eq_round_key`, 1 s** |
| gold vs gold, `eq_round_key` removed | **PDR PROVEN, 12 s** |

**The miter refutes a design against itself.** `round_key = key_mem[round]`,
`key_mem` is a memory Yosys does not apply the async reset to, so each instance
starts from its own arbitrary contents and the read ports differ immediately.

**Consequences, stated before the fix is written.**

1. **O1's REFUTED is void, not a verdict.** It is scored `CANNOT`, and O1 is
   re-gated once the miter is sound. R4 is **not** satisfied by it: R4 asks for
   a counterexample on a transform that is actually wrong, and this
   counterexample was produced against a correct one.
2. **A3 in `experiments/llm_proposer_aes/` is confounded.** A3 targets the same
   module through the same sequential miter and is published as **REFUTED**.
   Its stated mechanism, that it delayed one of three outputs while the
   k-padded miter delays all of them, is plausible and may be the true cause.
   The point is that **the evidence does not distinguish it from the artifact**,
   because this miter refutes `aes_key_mem` against itself. The published
   verdict stands as recorded and is now annotated as confounded. It is not
   quietly re-scored.
3. This is the **second** time this project has published a refutation its own
   miter manufactured, after the EQY depth-versus-counterexample confusion in
   §7.1 and the uninitialised-memory miter in `experiments/g7_in_loop/`. Three
   occurrences of one failure mode is a process defect, not three accidents.

**The fix, and why this one.** Reaching into `u_g.key_mem` from the wrapper does
not work in Yosys, and after synthesis the gate's array may not be a memory at
all, so there is no general way to assume the two states equal. What is general
is the control itself: **before any REFUTED is reported, run the same miter with
the gate replaced by the gold, and if that also fails, report `CANNOT` with the
reason instead of `REFUTED`.** A gate that cannot answer should say so; `CANNOT`
is already a first-class outcome in SlackBench, and §5 already establishes the
zero-noise-floor null control for the timing side. The verification side did not
have one. Now it does.

**New predictions, registered before the change is written.**

| # | prediction |
|---|---|
| **R8** | With the null control in place, O1 returns `CANNOT(null control refutes)` rather than `REFUTED`. |
| **R9** | Re-running A3 unchanged under the null control also returns `CANNOT`, which would mean its published REFUTED was never decidable by this harness. If instead A3's null control **passes** while A3 itself fails, the published verdict was right for the stated reason and only O1 was contaminated. **I do not know which**, and both outcomes are reportable. |
| **R10** | The null control changes no verdict for any proposal whose module has no unreset memory, so batch 1 (`rv32i_core`) is unaffected. |

---

## Amendment 4, 2026-09-11: the null control was unsound for k > 0, and R10 caught it

### Scorecard for R8, R9, R10

| # | registered | outcome |
|---|---|---|
| **R8** | O1 returns `CANNOT` rather than `REFUTED` | **CONFIRMED.** `G4_null_pdr: FAIL eq_round_key, 87s` on gold vs gold |
| **R9** | A3 either `CANNOT` (never decidable) or null-passes (published verdict right) | **VOID.** Neither: the control itself was invalid at k=1, see below |
| **R10** | the null control changes no verdict on `rv32i_core`, which has no unreset memory | **WRONG**, and this is the miss that mattered |

### What R10 found

P5 (`rv32i_core`, k=1) came back `CANNOT` with
`G4_null_bmc: FAIL eq_dmem_addr, 1s`. `rv32i_core` has no unreset memory, so
the artifact R8 diagnosed cannot be the cause.

The cause is **the null control itself**. For `k > 0` the miter delays every
gold output by k and compares `gp_n == t_n`. The null control sets the gate to
an *undelayed* copy of the gold, so it compares gold-delayed against
gold-undelayed. **That must fail for any design whose outputs ever change.**
It is not evidence of anything.

So the fix introduced a new defect of exactly the kind it was written to
prevent: a control that reports failure regardless of the thing it is
controlling for. **A3's `CANNOT` above is void for the same reason** and says
nothing about whether its published REFUTED was sound. R9 is unresolved, not
answered.

### The corrected control

The question a null control asks is "can this harness distinguish the module
from itself?", which is a question about **state initialisation and has nothing
to do with latency**. So the control must always be built as a **k = 0** miter,
whatever the proposal declares. The miter builder is factored out so the gate
and the control share one implementation rather than the control editing the
gate's output.

### Predictions, registered before the corrected control is written

| # | prediction |
|---|---|
| **R11** | Under a k=0 null control, **P5 returns REFUTED again**, its published verdict, because `rv32i_core` has no unreset state to poison the control. |
| **R12** | Under a k=0 null control, **O1 still returns `CANNOT`**, because its artifact is real. |
| **R13** | **A3 returns REFUTED**, its published verdict, because `key_mem` poisons `eq_round_key` and A3 fails on `eq_ready`, which the k=0 control should prove. If instead the k=0 control fails on `eq_ready` too, A3 was never decidable and the published number in `experiments/llm_proposer_aes/` changes. I do not know which. |

---

## Amendment 5, 2026-09-11: R11 to R13 scored, and module-granular CANNOT is too coarse

| # | registered | outcome |
|---|---|---|
| **R11** | P5 returns REFUTED again under a k=0 control | **CONFIRMED.** `G4_null_control: PASS (gold vs gold proves)`, `G4: REFUTED`. The corrected control no longer corrupts a clean module |
| **R12** | O1 still `CANNOT` | **CONFIRMED.** `G4_null_pdr: FAIL eq_round_key, 95s`. Its artifact is real |
| **R13** | A3 returns its published REFUTED | **WRONG.** Still `CANNOT`, `G4_null_pdr: FAIL eq_round_key, 9s` |

### Why R13's miss is a design flaw and not just a wrong guess

A3's own miter fails on **`eq_ready`**. Its null control fails on
**`eq_round_key`**. Those are different outputs. A blanket `CANNOT` at module
granularity throws away a question the harness *can* answer because an
unrelated output is poisoned by state the reset does not reach.

`round_key` is a combinational read of `key_mem`, which Yosys does not apply
the async reset to, so it is undecidable by this harness. `ready` and `sboxw`
are functions of reset-reachable state and the control **proves** them (PDR
12 s, measured with `eq_round_key` removed).

### The refinement, registered before it is written

When the control refutes, drop the output it names and retry, until the control
passes or nothing is left. Then re-run the real miter over the surviving
outputs and report, for example, `PROVEN (partial: 2 of 3 outputs; round_key
undecidable)`. **A proof restricted to a subset is a real proof of equivalence
on that subset and must never be reported as full equivalence**, which is why
the partial verdict carries the excluded outputs in its own string rather than
in a footnote.

| # | prediction |
|---|---|
| **R14** | A3 returns **REFUTED (partial)** on `eq_ready`, confirming its published verdict for its published reason. This decides whether `experiments/llm_proposer_aes/`'s "1 of 6 formally REFUTED" survives |
| **R15** | O1 returns **PROVEN (partial)** over `ready` and `sboxw`. Genuinely uncertain: the retiming is correct as far as I can reason, and I have reasoned wrongly about a transform in this project before |
| **R16** | P5 is **unchanged**, REFUTED with nothing dropped, because its control already passes |
| **R17** | O2, the FSM output-coded state assignment, reaches a **partial verdict** rather than `CANNOT` |
| **R18** | O2 does **not** materially improve `clk_b`. Same reasoning as R5: 91.4% of that path is fanout and this removes a decode, not a load |

---

## R15, recorded as it landed, 2026-09-11

    "G4_null_control": "REFUTES on round_key; PASSES on ready,sboxw",
    "G4": "PROVEN (partial: 2 of 3 outputs; round_key undecidable,
            driven by state the reset does not reach)"

**R15 CONFIRMED.** The engine's retiming is formally equivalent on `ready` and
`sboxw`, and the per-output control did what it was registered to do: it
localised the undecidable output instead of abandoning the module.

**The caveat, stated before anyone else has to point it out.** `round_key` is
this module's **primary data output**. The two outputs that were proven are a
control flag and an sbox request. So the honest sentence is *"proven on 2 of 3
outputs, and the excluded one is the one that carries the key material"*, not
*"proven"*. This is better than `CANNOT` because it says exactly what is and is
not established, and it is a long way from full equivalence. Any report text
that drops the parenthetical is wrong.

**Why `round_key` is undecidable here, corrected.** The first version of this
note said an assertion armed after an `init` sequence would decide it. **That
is wrong and is corrected here rather than left standing.**

`round_key = key_mem[round]`, `key_mem` holds 15 rows, `round` is a free 4-bit
input, and an AES-128 key schedule writes rows 0 to 10. Rows 11 to 14 are never
written and are never reset, so `key_mem[12]` is arbitrary and independent in
the two instances **no matter how long the designs run**. Arming after init
does not help; the address has to be constrained too.

So this is **not a harness weakness**. Equivalence of `round_key` is not a
property of this module at all without an assumption about which `round` values
are reachable, which belongs to the enclosing `aes_core` and not to
`aes_key_mem`. A gate that reported `round_key` PROVEN here would be reporting
something false. Reporting it undecidable and naming why is the correct answer,
and the fix is an assumption the *proposal* would have to declare, not
machinery the gate can supply.

## R14, recorded as it landed, 2026-09-11

    "G4_null_control": "REFUTES on round_key; PASSES on ready,sboxw",
    "G4": "REFUTED (partial: 2 of 3 outputs; round_key undecidable,
            driven by state the reset does not reach)"

**R14 CONFIRMED, and amendment 3's warning is now resolved rather than
standing.** A3's own miter fails on `eq_ready`. The null control **proves**
`ready` and `sboxw`. So the output A3 fails on is one the harness can decide,
and its refutation is not the `key_mem` artifact.

**`experiments/llm_proposer_aes/`'s published "1 of 6 formally REFUTED" stands,
for exactly the reason it published**: A3 declared k=1 and delayed one of three
outputs while the k-padded obligation delays all of them.

Amendment 3 said the evidence "does not distinguish it from the artifact". That
was true of the harness as it stood. It is no longer true, and the distinction
was made by measurement rather than by argument. The amendment stays on the
record as written; this is its resolution, not its deletion.

**What this cost to establish.** The confound was real, the first fix for it was
wrong in the same shape as the bug, and the second fix was too coarse to answer
the question. Three iterations, two of them caught by registered predictions
(R10, R13), to arrive at a verdict that turned out to match the published one.
That is the expensive-looking outcome that matters: a number nobody had reason
to doubt was checked, and it held.

---

## Correction, 2026-09-11: R11 was scored on a label the code got wrong

**What was reported.** R11 was scored CONFIRMED and stated to the project owner
as "P5 is REFUTED again with the null control passing", quoting
`"G4_null_control": "PASS (gold vs gold proves)"`.

**What the run actually contained.**

    "G4_null_bmc": "TIMEOUT -- stopped by wrapper timeout, not a tool verdict"
    "G4_null_pdr": "TIMEOUT -- stopped by wrapper timeout, not a tool verdict"
    "G4_null_control": "PASS (gold vs gold proves)"

**Both engines timed out and the gate printed PASS.** `null_control()` returns
`True` on a proof, `False` on a failure and `None` when neither closes, and the
call site tested `if nl is not False`, which treats `None` as a pass. The
docstring directly above it said `None` "is reported as inconclusive rather
than silently treated as a pass". The docstring was right and the code did the
opposite.

Re-run with the corrected branch, same inputs:

    "G4_null_control": "INCONCLUSIVE (gold vs gold neither proved nor failed)"
    "G4": "REFUTED (null control inconclusive: the control did not close,
            so this refutation is not corroborated)"

**Re-scoring R11.** The registered prediction was "P5 returns REFUTED again",
and it does, in both runs. The prediction is **CONFIRMED**. The *reason* given
for it, that `rv32i_core` has no unreset state to poison the control, is
**NOT demonstrated**: the control never closed, so nothing was shown either
way. A confirmed prediction with an unverified justification is not the same as
a confirmed mechanism, and the difference is recorded rather than blurred.

**P5's standing.** Its own miter refutes in 2 to 5 s on `eq_dmem_addr`. Its
control does not close in 300 s against 2,048 flops. So P5 is **REFUTED,
uncorroborated**. That is weaker than what `experiments/llm_proposer/` publishes
and the weaker statement is the true one until the control closes.

**This is the fifth verification defect of my own found today**, and the first
that reached the project owner as a stated fact before being caught. Caught by
reading the call site while writing an unrelated change, not by any test. The
tally belongs in REPORT §9 as a statement about the process rather than as five
separate confessions.

**R19, registered now.** With the null-control timeout raised to 1800 s, P5's
control **closes**, either PROVEN (corroborating the refutation) or FAIL
(voiding it). If it still does not close, the honest conclusion is that this
harness cannot corroborate any refutation on a 2,048-flop design and every
`rv32i_core` refutation in the project inherits "uncorroborated".

## R17, recorded as it landed, 2026-09-11

    "G3": "PASS(state-remap: k=0, flop delta unconstrained)",
    "dff_delta": -2,
    "G4_null_control": "REFUTES on round_key; PASSES on ready,sboxw",
    "G4_partial_pdr": "PROVEN -- 16s",
    "G4": "PROVEN (partial: 2 of 3 outputs; round_key undecidable,
            driven by state the reset does not reach)"

**R17 CONFIRMED.** The FSM output-coded state assignment reaches a real verdict
rather than `CANNOT`.

**Both classes the problem statement names and this engine could not express
are now proposed, routed and discharged.** Retiming through branch 5, FSM
optimization through branch 4, each on the module the loop actually binds.

**One number was not predicted: `dff_delta` is −2, not 0.** The re-encoding was
designed to keep `key_mem_ctrl_reg` at three bits, so the flop count should not
have moved. Synthesis removed two flops elsewhere, presumably because four
control outputs became direct register bits and something feeding them became
dead. Unexplained, recorded, and it does not affect the verdict: branch 4 leaves
the flop delta unconstrained by design, which is the whole point of it.

**Under the old G3 rule this proposal would have been rejected** with
`FAIL(declared k=0 but flop count changed by -2)`, on a transform that is
correct. That is the hypothesis of this experiment landing a second time,
on a transform nobody wrote to demonstrate it.

---

## R5, R18 and C3 scored across all groups, 2026-09-11

One baseline, `sdc/bench_top_v3.sdc`, all three reported groups, zero-parasitic.
`aes_key_mem` is instantiated in both AES cores, so `clk_b` and `clk_e` are both
target groups and `clk_a` is the non-local column REPORT §5 requires separately.

| variant | author | proof | clk_b | clk_e | clk_a (non-local) |
|---|---|---|---|---|---|
| `fanout_replication_round_key_update` | **model, unattended** | PROVEN (EQY, all outputs) | **+1.414** | +1.414 | +1.967 |
| `fsm_output_coded_state_assignment` | this session | PROVEN, 2 of 3 outputs | **+3.185** | +3.185 | +0.528 |
| `retime_write_decode_forward` | this session | PROVEN, 2 of 3 outputs | **−4.616** | −4.616 | +0.274 |

| # | registered | outcome |
|---|---|---|
| **R5** | the retiming does not improve its own group | **CONFIRMED in direction, understated in magnitude.** It does not merely fail to help, it costs **4.616 ns** |
| **R18** | the FSM transform does not materially improve `clk_b` | **WRONG. +3.185 ns**, the largest RTL gain on this group in the project |
| **C3** | the unattended proposal does not materially improve `clk_b` | **WRONG. +1.414 ns**, and no group paid for it |

### Correction to a statement already made to the project owner

After the single-group measurement I wrote: *"the unattended model proposed a
better transform for this path than the session driving this project did."*
**That is wrong on the full data.** The model's fanout split beat this session's
**retiming** by 6.03 ns, and lost to this session's **FSM re-encoding** by
1.77 ns on the same group.

The defensible version: **the model's proposal was the only one of the three
that improved every group, and it carries the strongest proof** (EQY over all
outputs, against two partial proofs). The session's retiming was the worst
transform of the three and its stated rationale was aimed at the wrong thing.

### What this does to REPORT §1

The claim *"no RTL rewrite shortens a net's load delay"* is **falsified**, and
by more than one transform: two of three RTL transforms improved a group the
classifier scored 91.4% fanout-attributable, one of them by 3.185 ns.

What survives the measurement:

- Best RTL gain here: **+3.185 ns** on a **−18.957 ns** violation, **16.8%**.
- `repair_design` on the same class of path: **+55.805 ns**.
- So the true claim is **"RTL work on a fanout-dominated path buys a sixth of
  what physical buffering buys on this benchmark, so the router prefers
  physical"** — a ratio, not an impossibility.

The two-lever design survives and is better supported by a ratio than by an
absolute that a single counterexample breaks.

---

## R19, recorded as it landed, 2026-09-11

    "G4_null_control": "INCONCLUSIVE (gold vs gold neither proved nor failed)",
    "G4": "REFUTED (null control inconclusive: the control did not close,
            so this refutation is not corroborated)"

**R19 IS WRONG.** Given 1800 s instead of 300, P5's gold-vs-gold control still
does not close on `rv32i_core`.

**The registered alternative is therefore the finding:** *"if it still does not
close, this harness cannot corroborate any refutation on a 2,048-flop design."*
That is now the stated limit.

### Exactly which verdicts inherit the caveat, and which do not

| refutation | discharged by | corroborated? |
|---|---|---|
| **P5** (`rv32i_core`, k=1) | sequential miter | **NO.** Control does not close at 1800 s |
| **P4** (`rv32i_core`, k=0) | **EQY**, partition-level | **YES, independently.** Concrete counterexample `a=ae19f605, shamt=7`, confirmed by directed simulation |
| **A3** (`aes_key_mem`, k=1) | sequential miter | **YES.** Fails on `eq_ready`, an output the per-output control proves |

So the caveat is narrow and specific: **refutations from the sequential miter on
designs around 2,000 flops**. P5 is the only such verdict in this project. EQY
refutations are unaffected, because they are partition-level and P4's carries
concrete values independently reproduced in simulation.

### What P5 still has, and what it does not

P5's refutation is **not** unsupported. Its own miter fails in 2 to 5 s on
`eq_dmem_addr`, the failure has a stated mechanism (a k-padded obligation
against a feedback machine, §7.3), and the trace is committed. What it lacks is
the one thing the null control exists to supply: **proof that the harness can
tell this design from itself**. Without that, the possibility that the miter
refutes `rv32i_core` against itself for some reason nobody has found is open,
and the honest word for an open possibility is *uncorroborated*.

**Corroborating it independently is possible and is not done**: extract the BMC
trace and replay it in directed simulation, as was done for P4. Registered here
as known-open rather than claimed.

### Why the control cannot close, stated as a limit rather than an excuse

The control is an unbounded sequential equivalence question over 2,048 flops
with free inputs. BMC exhausts its depth budget and PDR does not converge. This
is a property of the method at that size, not a bug: the same control closes in
**10 to 12 s** on `aes_key_mem` and in **64 s** on `domain_b`. The gate is
honest about it, which is the whole point of a verdict string that says
`not corroborated` instead of `REFUTED`.

---

## Amendment 6, 2026-09-11: the second review says the partial proof is a harness gap, and it is probably right

A second organiser review (`REVIEW_RESULT_2026-09-11_r2.md`) rejects this
registration's argument that `round_key` is undecidable *by nature*:

> Right: `round_key = key_mem[round]` with a free 4-bit `round` and 11 written
> rows is not a property of `aes_key_mem` in isolation. **Wrong: "this is not a
> harness limit".** The null control fails gold against gold on `round_key`
> precisely because the miter gives the two instances *independent* arbitrary
> initial memory contents [...] the independence is the harness's choice, not
> the design's. Standard sequential equivalence on unreset storage assumes the
> two copies start from the same initial state, because they are the same chip.

**I think that is correct and my earlier note was wrong.** The question a miter
asks is whether two designs behave identically *from the same starting
conditions*. Yosys's `anyinit` seeds each instance separately, which asks a
different and stricter question: whether they agree from **any pair** of
starting states. For unreset storage that is not equivalence, it is something
no correct transform could satisfy.

This is the second time this file has recorded a wrong explanation for the same
verdict. The first claimed an init-armed guard would fix it; it would not,
because unwritten rows stay arbitrary. Both errors pointed away from the
harness and toward the design, which is the direction that flatters the tool.

### Predictions, registered before the assumption is written

| # | prediction |
|---|---|
| **R20** | With the two instances' `key_mem` assumed equal at time 0, the **null control proves all three outputs** on `aes_key_mem`, where today it fails `round_key` in 1 s |
| **R21** | Under that control, **O2 proves 3 of 3**. O2 re-encodes `key_mem_ctrl_reg` and never touches `key_mem`, so if anything can prove outright it is this one |
| **R22** | **O1 also proves 3 of 3.** Less certain: it adds a registered one-hot shadow of `round_ctr_reg`, and while that register *is* reset, the proof now has to carry the invariant `round_ctr_oh_reg == 1 << round_ctr_reg` across the memory write port |
| **R23** | The assumption changes **no verdict on `rv32i_core` or `domain_b`**, neither of which has unreset storage. If it does, the assumption is doing more than it claims |

**Void condition.** If the assumption makes a **known-bad** transform prove,
it is too strong and the result is thrown out, not patched. The existing
refuted variants are the test: A3 must stay REFUTED.

## R20 and R21, recorded as they landed, 2026-09-11

`setundef -init -zero` after `prep`, which gives every undefined initial value a
defined one, **the same one in both instances**, without touching either design
or using a hierarchical reference (Yosys rejects those here with
`AST_AUTOWIRE`).

| miter | before | with the assumption |
|---|---|---|
| null control, gold vs gold, all 3 outputs | **FAIL `eq_round_key`, step 3, 1 s** | **PASS to depth 8** |
| O2, all 3 outputs including `round_key` | not attempted; control refused | **PASS to depth 8** |

**R20 CONFIRMED. R21 CONFIRMED.**

**The partial proof was a harness gap and this registration twice said it was
not.** Amendment 5 called `round_key` "undecidable, driven by state the reset
does not reach". The R15 note went further and called it "not a harness
weakness [...] a gate reporting it PROVEN here would be reporting something
false". Both are **withdrawn**. The gate can report it PROVEN, under a stated
assumption, and the assumption is the one sequential equivalence has always
made: the two designs are the same chip and their unreset storage starts in the
same state.

**What the assumption is, stated exactly.** Not "the same arbitrary value",
which Yosys cannot express here, but **zero**, which is strictly weaker and is
what `reg_update`'s own reset loop intends for `key_mem` and which Yosys cannot
apply because the target is an array. Every verdict obtained this way carries
that assumption in its text. A transform that is equivalent from a zeroed
memory but not from an arbitrary one would pass this and should not; no such
transform is known to be in this project, and that gap is disclosed rather than
closed.

**How this was found.** Not by us. An external reviewer read the argument in
amendment 5 and rejected it, correctly, in one paragraph. Two of the three
wrong explanations this file has recorded for this verdict pointed away from the
harness and toward the design, which is the direction that flatters the tool.

---

## Amendment 7, 2026-09-11: the null control was asking a harder question than the one posed

The same review rejects R19's conclusion as an instrument problem rather than a
result:

> The refutation is a BMC counterexample found in 2 seconds, so it lives at
> depth 1 or 2. Corroboration needs only that gold-vs-gold does not fail at
> that depth [...] The downgrade is over-scrupulous as executed.

**Correct.** A refutation found at step *n* is only as trustworthy as the
harness is at step *n*. The control ran BMC to the proposal's full depth (20)
and PDR to convergence over 2,048 flops, which is a strictly harder question,
and on `rv32i_core` it answers nothing: both engines time out and a real
refutation is downgraded for no reason.

`failing_depth()` now reads the counterexample's step out of the BMC log and
the control runs at `min(depth, step + 2)`. Both numbers are recorded in the
result as `G4_counterexample_step` and `G4_null_depth`, so the verdict carries
the depth its corroboration actually covers.

**This narrows what a passing control means, and the narrower claim is the
honest one.** It no longer says "the harness can distinguish these designs".
It says "the harness does not produce a spurious failure at or below the depth
where this refutation was found", which is exactly what is needed to trust that
refutation and nothing more.

| # | prediction |
|---|---|
| **R24** | P5's control **closes** at the bounded depth and P5 returns plain `REFUTED`, recovering the verdict R19 downgraded |
| **R25** | The bound changes **no verdict** already obtained on `aes_key_mem`, whose control closed in 10 to 12 s at full depth anyway |

If R24 misses, the downgrade in R19 stands on its own merits and the extra
machinery bought nothing, which is also a reportable outcome.

## R21, R22 and the void check, recorded as they landed, 2026-09-11

All three at `--depth 8 --zero-init`, against `aes_key_mem`, all three outputs
including `round_key`:

| proposal | before | with the assumption |
|---|---|---|
| **O2** `fsm_output_coded_state_assignment` | PROVEN, 2 of 3 | **PROVEN.** `bmc PASS 19s`, `pdr PROVEN 124s` |
| **O1** `retime_write_decode_forward` | PROVEN, 2 of 3 | **PROVEN.** `bmc PASS 58s`, `pdr PROVEN 222s` |
| **A3** known-bad, the void check | REFUTED | **REFUTED.** Fails `eq_ready` at 1 s |

**R21 CONFIRMED. R22 CONFIRMED. The void condition does NOT fire.**

Both are **PDR**, which is unbounded, not the depth-8 bound: these are full
sequential equivalence proofs over the whole interface, conditional on the
stated initial-state assumption and nothing else.

**The void check is the one that makes the other two mean anything.** An
assumption that made a known-bad transform prove would be an assumption that
proves whatever you point it at. A3 declares k = 1 and delays one of three
outputs while the k-padded obligation delays all of them; that defect has
nothing to do with memory initialisation, and the assumption correctly leaves
it visible.

### The bounded control, first measurement

A3's result also carries amendment 7's change, and it behaves as registered:

    "G4_counterexample_step": 3,
    "G4_null_depth": 5,
    "G4_null_bmc": "PASS -- 1s",
    "G4_null_control": "PASS (gold vs gold proves)"

The refutation sits at step 3, so the control ran to depth 5 and closed in
**1 second**. At full depth the same control cost 10 to 12 s here and did not
close at all on `rv32i_core`.

### What this retracts, for the third time on one verdict

Amendment 5 and the R15 note both argued `round_key` was undecidable as a
property of the design. Amendment 6 withdrew that. This measurement closes it:
the output is decidable, the proof is unbounded, and the only thing that ever
stood in the way was the harness giving two copies of one chip independent
power-up state.

**A reader should count three wrong explanations before the right one**, all
three of them pointing at the design rather than at the tool.

## R24 and R25, recorded as they landed, 2026-09-11

| # | registered | outcome |
|---|---|---|
| **R24** | P5's control closes at the bounded depth and P5 returns plain REFUTED | **WRONG.** `G4_null_depth: 5`, `G4_null_bmc: TIMEOUT`, still uncorroborated |
| **R25** | the bound changes no verdict already obtained on `aes_key_mem` | **CONFIRMED.** A3 unchanged, control now closes in **1 s** instead of 10 to 12 |

### Why R24 missed, measured

The review's estimate was *"a BMC to depth 2, seconds"*. That underestimates an
asymmetry: the real miter **found** P5's counterexample at step 3 in 3 s, which
is a SAT question; the control has to **prove no counterexample exists** to
depth 5, which is UNSAT over two copies of 2,048 flops and did not finish in
300 s. Presence is cheap, absence is not.

### And the bound exposed a logic error of ours, which is the more useful finding

`null_control()` returns `True` only when **PDR** reports PROVEN. PDR is
unbounded. So a control deliberately bounded at the counterexample's depth is
still judged by an unbounded criterion, and **a BMC PASS at the bounded depth
is discarded**. That defeats the entire point of amendment 7: the bound makes
the question cheaper and the acceptance test never got the message.

Corrected: when the control is bounded (a counterexample depth was found), a
**BMC PASS at that depth is sufficient corroboration**, because it is exactly
the claim being made, that the harness produces no spurious failure at or below
the depth where this refutation was found. PDR PROVEN remains sufficient and is
still preferred when it closes.

**This is the fourth iteration on one control**: built at the wrong k (R10),
too coarse at module granularity (R13), reporting a timeout as a pass, and now
judging a bounded run by an unbounded criterion. Three of the four were caught
by registered predictions that missed.

| # | prediction |
|---|---|
| **R26** | With BMC-at-bounded-depth accepted, P5's control **still does not close**, because the BMC itself timed out rather than passing. The fix is correct and insufficient, and P5 stays uncorroborated by this route |
| **R27** | Given 1800 s at depth 5, the control **does** close and P5 returns plain REFUTED |

If R27 also misses, the honest conclusion is the one R19 reached: this harness
cannot corroborate a sequential-miter refutation at this design size, and the
remaining route is the reviewer's other suggestion, replaying the witness trace
in simulation, which is not built.
