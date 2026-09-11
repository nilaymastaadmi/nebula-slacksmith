# Prompt template for the online proposer, v2

Frozen before the `experiments/missing_classes/` run, 2026-09-11. v1
(`tools/proposer_prompt.md`) is unchanged and stays attached to
`experiments/online_proposer/`, whose registration lists editing it as a void
condition.

**What changed from v1, and why.** v1 offered the proposer four obligation
branches including branch 4, mapped-state. `tools/gate_proposal.py` could not
execute it: every `k = 0` proposal was routed to EQY, and any proposal that
re-encoded state changed the flop count and was killed by G3 first. So v1
invited a class of proposal that was guaranteed to be rejected, and offered no
retiming row at all. Measured in `experiments/missing_classes/`. Both branches
are now implemented and branch 5 is added here.

Per `experiments/online_proposer/PREREGISTRATION.md` §3.
Editing this after seeing a gate result and reporting the re-run as that
experiment is a listed void condition.

Placeholders in `{braces}` are filled by `tools/proposer.py` from the live loop
state. Nothing else is substituted, and no counterexample or gate verdict is
ever placed into this template: that exclusion is the batch-3 boundary.

---

You are proposing ONE typed RTL transform to reduce the critical path delay of a
module in a synthesized design. Your proposal will be checked by a formal
equivalence gate that you cannot influence, and then re-measured by static
timing analysis. A transform that is wrong will be refuted with a
counterexample. A transform that is correct but does not improve timing will be
reverted.

## The state right now

Iteration {iteration} of the closed loop.

Worst path group: **{clock}**, slack **{slack} ns**.

Slack history so far, by iteration: {history}

The classifier routed this path to the RTL lever with verdict **{verdict}**,
fanout delay share {fanout_share}, path delay {path_delay} ns across
{cells_on_path} cells. Its evidence:

{evidence}

Binding module: **{module}**

## The critical path report

```
{timing_report}
```

## The current source of {module}

This is the CURRENT source. It may already contain a transform accepted in an
earlier iteration of this run.

```verilog
{module_source}
```

## What you must return

A single JSON object, and nothing else. No prose before or after it.

```json
{{
  "id": "{proposal_id}",
  "def_id": "<short_snake_case_name_for_the_transform_class>",
  "target_module": "{module}",
  "target_file": "rtl/{module}.v",
  "latency_delta_k": 0,
  "obligation_branch": "<one of the four below>",
  "rationale": "<why this shortens the critical path, in two or three sentences>",
  "variant_source": "<the COMPLETE rewritten source of the module>"
}}
```

### The four proof-obligation branches

Declare the one your transform actually needs. The declaration selects the
proof, so declaring the wrong branch means being checked against the wrong
question.

| `latency_delta_k` | `obligation_branch` | when |
|---|---|---|
| 0 | `1 (combinational equivalence, EQY)` | state-preserving: same flops, same cycle behaviour |
| >0 | `2 (k-padded miter)` | you added k pipeline stages and the interface is rigid |
| >0 | `3 (stream equivalence)` | you added stages and the interface is elastic (valid/ready) |
| 0 | `4 (mapped-state equivalence)` | you re-encoded state, e.g. binary to one-hot |
| 0 | `5 (retiming, sequential miter)` | you moved a register across combinational logic without changing latency |

Branches **4 and 5 may change the flop count**; branches 1, 2 and 3 may not at
`k = 0`. Both 4 and 5 are discharged by a sequential miter over the module
interface rather than by EQY, because neither leaves a flop correspondence for
EQY to pair internal nets across.

A **retiming** here means exactly what it means in the literature: registers
moved across combinational logic so that the cycle-by-cycle behaviour visible
at the module's ports is unchanged. Moving a register forward across a join
removes flops; moving one forward across a fork replicates it. If your
transform changes what the ports do on any cycle it is not a retiming and
declaring branch 5 will get it refuted.

### Rules that will be checked mechanically

- `variant_source` must be the complete module, parseable by Yosys, and must
  synthesize with **zero inferred latches**.
- The module name, its port list and port widths must be unchanged.
- Do not change any interface timing unless you declare `latency_delta_k > 0`
  and the matching branch.
- Do not add `set_multicycle_path`, `set_false_path` or any other constraint.
  The SDC is fingerprinted and constraint changes are rejected before timing is
  believed.
- Prefer a transform that shortens the **specific** path in the report above.
  A correct transform that does not touch the binding path will be reverted.

Return the JSON object only.
