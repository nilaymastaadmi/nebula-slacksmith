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
