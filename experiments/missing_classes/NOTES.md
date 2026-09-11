# The two optimization classes the engine never proposed

Registered in `PREREGISTRATION.md` (`a66225a`) before `tools/gate_proposal.py`
was touched, with four dated amendments. Started from an external
organiser-persona review (`REVIEW_RESULT_2026-09-11.md`) that scored objective
O3c **MISSING** and O3d **PARTIAL**.

## The finding

The problem statement names four optimization classes. The engine had proposed
two. The reason was **not** that nobody had written them.

`tools/gate_proposal.py`'s G3 check required

    k == 0  =>  dff_delta == 0

with no exception, and **both** missing classes are `k = 0` with the flop count
changed. Retiming moves a register across combinational logic. Re-encoding a
state register widens it. Neither could pass G3 whatever its content, so the
proposer could not express one.

Worse, `tools/proposer_prompt.md` **advertised branch 4 to the proposer**,
described as "you re-encoded state, e.g. binary to one-hot", and every `k = 0`
proposal was routed to EQY before its declared branch was consulted. A proposer
that followed the template was guaranteed a rejection.

| class | cause |
|---|---|
| FSM optimization | **offered and unimplemented** |
| retiming | **never offered**; no row in the template |

Measured, on the project's own published one-hot `domain_b`, RTL unchanged:

| gate | result |
|---|---|
| before | `G3: FAIL(declared k=0 but flop count changed by +12)` |
| after | `G3: PASS(state-remap)`, `G4_bmc PASS 18s`, `G4_pdr PROVEN 64s` |

That is why `experiments/fsm_reencode/` carries a hand-written `miter_mapped.sv`
and never invokes the gate.

## What changed in the tool

1. **Branch 4 (mapped-state) and branch 5 (retiming)** are implemented. Both
   are `k = 0` with the flop count unconstrained, and both are discharged by
   the **sequential miter**, not EQY: neither leaves a flop correspondence for
   EQY to pair internal nets across, which `experiments/g7_in_loop/` already
   measured the hard way.
2. `tools/proposer_prompt_v2.md` adds the retiming row. **v1 is not edited**;
   `experiments/online_proposer/`'s registration lists that as a void
   condition, and `SLACKSMITH_PROMPT` selects the template.
3. **A null control before any refutation is reported** (below).

## The null control, and the two bugs it took to get right

O1, the retiming the proposer wrote against live state, came back `REFUTED`.
Reading the counterexample rather than reporting it showed the two instances
starting from **different arbitrary `key_mem` contents**. Yosys does not apply
a module's async reset to a memory, so `round_key = key_mem[round]` differs at
once.

| miter | result |
|---|---|
| gold vs **gold**, all three outputs | **FAIL `eq_round_key`, 1 s** |
| gold vs gold, `eq_round_key` removed | **PDR PROVEN, 12 s** |

**The miter refutes the design against itself.** This is the third refutation
this project's own harness has manufactured, so the fix is structural rather
than local: before any `REFUTED` is reported, run the same miter with the gate
replaced by the gold, and report `CANNOT` if that also fails. `CANNOT` is
already a first-class outcome in `experiments/slackbench/`, and REPORT §5
already establishes the zero-noise-floor null control on the timing side. The
verification side did not have one.

**The first version of that fix was itself wrong**, and a registered prediction
caught it. R10 predicted the control would change no verdict on `rv32i_core`,
which has no unreset memory. P5 came back `CANNOT` anyway, because the control
was built at the proposal's own `k` and so compared gold-delayed against
gold-undelayed, which fails for any design whose outputs change. The control is
now always built at `k = 0`: it asks whether the harness can tell the module
from itself, which is a question about state initialisation and not about
latency.

## Scorecard

See `PREREGISTRATION.md` for the registered text of every prediction.

## A naming collision, flagged not fixed

This directory numbers its proposals **O1** and **O2**, and so does
`experiments/online_proposer/`. They are different proposals:

| id | experiment | transform |
|---|---|---|
| O1 | `online_proposer` | `array_write_decode_split` |
| O2 | `online_proposer` | `array_read_mux_two_level` |
| O1 | `missing_classes` | `retime_write_decode_forward` |
| O2 | `missing_classes` | `fsm_output_coded_state_assignment` |

The collision was noticed after both were registered and gated. Renumbering a
pre-registered artifact once its results exist is worse than living with the
collision, so every reference names the directory.

## Scorecard

Registered text for every prediction is in `PREREGISTRATION.md` with five dated
amendments. **13 predictions, 4 misses, and 3 of the 4 misses found a defect.**

| # | prediction | outcome |
|---|---|---|
| R1 | the gate rejects a correct retiming at G3 | CONFIRMED |
| R2 | it rejects the project's own one-hot for the same reason | CONFIRMED on mechanism, **MISS on the number**: predicted +6 flops, measured +12 |
| R7 | branch 4 lets the one-hot reach a verdict, and it is PROVEN | CONFIRMED, `PROVEN` 64 s |
| R8 | O1 returns `CANNOT`, not `REFUTED` | CONFIRMED |
| **R10** | the null control changes no `rv32i_core` verdict | **WRONG.** Found the control unsound at k>0 |
| R11 | P5 returns REFUTED under a k=0 control | CONFIRMED verdict, **justification not demonstrated**: the control never closed and the code labelled the timeout a pass |
| R12 | O1 still `CANNOT`; its artifact is real | CONFIRMED |
| **R13** | A3 returns its published REFUTED | **WRONG.** Found module-granular `CANNOT` too coarse |
| R14 | A3 REFUTED on `eq_ready` under per-output control | CONFIRMED. **Published verdict holds** |
| R15 | O1 PROVEN over the decidable outputs | CONFIRMED, 2 of 3 |
| R16 | P5 unchanged | CONFIRMED, and uncorroborated |
| R17 | O2 reaches a partial verdict, not `CANNOT` | CONFIRMED, `PROVEN` 2 of 3 |
| R18 | O2 does not materially improve `clk_b` | see `results/` |

## What this experiment cost and what it bought

**Bought.** Two of the four optimization classes the problem statement names
went from structurally unproposable to proposed, routed and discharged. A null
control on the verification side, which this project had on the timing side
from the beginning and had never built for proofs. A published refutation
(A3) re-checked and held. One (P5) demoted to uncorroborated.

**Cost.** Five defects of this session's own, four of them in code written
*today to fix the previous one*:

1. G3 rejecting two named classes, the original defect.
2. The null control built at the proposal's own `k`, so it failed for every
   k>0 proposal. Caught by R10.
3. `CANNOT` at module granularity, discarding decidable outputs. Caught by R13.
4. `None` from the control reported as `PASS (gold vs gold proves)` when both
   engines had timed out. **This one reached the project owner as a stated
   fact** before being caught by reading the call site.
5. `slacksmith.py` testing `v.startswith("PROVEN")`, which would have accepted
   a partial proof as a full pass and confirmed a transform on a proof that
   excludes the module's primary data output. Caught before any run used it.

Three of those five were caught by **registered predictions that missed**.
That is the argument for pre-registration stated as a measurement rather than
as a principle: the predictions that were wrong did more work than the ones
that were right.
