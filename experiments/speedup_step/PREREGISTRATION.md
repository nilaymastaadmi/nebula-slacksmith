# Pre-registration: how long the obligation takes a person to write

Registered 2026-09-12, before any timing was taken. Scored in `NOTES.md` here.
Predictions **R70 to R72**.

## Why

The organisers asked entrants to show how AI agents speed up a previously
manual optimisation workflow. REPORT §1.1 currently **refuses to give a ratio**,
because no engineer was ever timed doing the work. That refusal is honest and it
is also a non-answer to a question they asked in writing.

A whole-workflow ratio is not available: nobody here is going to hand-close
timing on a 48,616-cell design three times to produce a denominator. **One step
of the workflow is purely mechanical and can be timed honestly**: writing the
proof obligation once the transform and its declared type are known. That is
the step `tools/gate_proposal.py` automates, and it is the step this measures.

## Protocol

Three transforms, one per obligation branch, chosen before timing began:

| branch | transform | gold | variant |
|---|---|---|---|
| 1, combinational (EQY) | **P2** | `rtl/rv32i_core.v` | `experiments/llm_proposer/proposals/` |
| 2, k-padded miter (SymbiYosys) | **`pipeline_cut_rigid(domain_a)`**, k = 1 | `experiments/pipeline_cut_domain_a/domain_a_clamped_comb.v` | `..._pipelined.v` |
| 4, mapped-state (SymbiYosys) | **`fsm_reencode(domain_b)`**, k = 0 | `experiments/fsm_reencode/domain_b.v` | `domain_b_onehot.v` |

**The author writes each obligation from scratch, from the RTL and the declared
transform type, with a stopwatch running, without opening the generated one.**
The files that must stay closed are listed in `HANDOFF.md` beside this file. An
obligation counts as finished when the author believes it is correct and stops
the clock, **not** when it runs, because "does it run first time" is a separate
measurement (R72).

**The author knows this codebase and wrote the transforms.** That makes every
time below a **floor on the human side**, and therefore a **ceiling on the
ratio**. A stranger would be slower. This is stated in the report sentence
itself, not just here.

The generated side comes from the gate logs already committed. Authoring and
solving are separated where the log allows it; where it does not, the whole
gate wall-clock is quoted and labelled as including the solve, which makes the
generated side look **slower** than it is.

## Predictions

**R70.** Branch 1, the EQY config, takes **more than 3 minutes**. *Prior:
moderate. It is the simplest of the three and mostly boilerplate, but the
partition and `dont_use` details are where it goes wrong.*

**R71.** Branches 2 and 4, the SymbiYosys miters, each take **more than 10
minutes**. *Prior: strong. A k-padded miter needs a shift register on the
reference outputs, a reset-alignment assumption, and the right `depth`; a
mapped-state miter needs the state correspondence stated or deliberately
unconstrained.*

**R72.** **At least one** hand-written obligation fails to run first time.
*Prior: strong. Three hand-written formal setups running first time would be
the surprising outcome.*

## What would void this

- Looking at a generated obligation, at `tools/gate_proposal.py`'s templates, or
  at a past miter for the same branch, voids that transform's time. Say so and
  report the other two.
- An interruption longer than a minute voids that time; restart the transform.
- The times are reported as measured. **A time that looks embarrassing for
  either side is still the time.**

## Scope

N = 3, one author, one codebase, all three transforms written by the person
timing them. This is a step ratio, not a workflow ratio, and the report sentence
says so.

---

## Amendment 1, 2026-09-12, before any time was taken

**R70 to R72 are suspended, not scored.** The author states he is not practised
at writing formal obligations, so his time would not stand in for an engineer's.
That matters more than it first looks: the two confounds run in **opposite
directions** and cannot be signed.

- He wrote these transforms and knows this codebase, which makes him **faster**
  than a stranger, so his time is a floor and the ratio a ceiling.
- He is not practised at miter authoring, which makes him **slower** than a
  practised verification engineer, so his time is a ceiling and the ratio a
  floor.

With N = 1 and both confounds present, the bias has no sign, and a ratio whose
direction of error is unknown is worse than no ratio. **If the author runs the
tasks anyway the times are recorded and reported with both confounds stated,
and R70 to R72 are scored then. Until that happens they stay open, not void.**

**A borrowed denominator was considered and rejected.** A web search on
2026-09-12 for published per-obligation authoring times returned none: the
literature covers miter construction and overall verification effort share, not
how long a person takes to write one equivalence obligation. Taking a number
from a verification-effort survey and dividing by it would be a category error
with a citation attached, which is the exact failure mode
`tools/check_report_numbers.py` and `tools/tally_predictions.py` exist to catch
in our own writing.

## What replaces it, and why it is not a prediction

`obligation_cost.py` counts **the numerator instead of guessing the
denominator**: how much machinery each generated obligation is, measured from
the committed artifacts.

**This is a descriptive measurement, not a hypothesis test, and it carries no
prediction id.** It was run before this amendment was written, so registering a
prediction against it now would be scoring a coin after it landed. The project
distinguishes the two deliberately, and this is the second kind.

| branch | artifact | lines | code lines | port connections | properties |
|---|---|---|---|---|---|
| 1 combinational | `ctrl.eqy` | 11 | 9 | 0 | 0 |
| 2 k-padded miter | `miter_pipeline_domain_a.sv` | 138 | 71 | 28 | 4 |
| 2 runner | `miter.sby` | 32 | 23 | 0 | 0 |
| 4 mapped-state miter | `miter_mapped.sv` | 108 | 48 | 18 | 6 |
| 4 runner | `miter.sby` | 37 | 26 | 0 | 0 |
| **total** | 5 artifacts | **326** | **177** | **46** | **10** |

A reader can weigh 177 lines of hand-wired miter across three branches against
their own experience. That is a better answer to "how does this speed up manual
work" than a ratio this project cannot support, and it is checkable by running
the script.
