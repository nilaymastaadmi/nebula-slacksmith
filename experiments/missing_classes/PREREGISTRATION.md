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
