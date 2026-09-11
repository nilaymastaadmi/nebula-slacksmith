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
