# Prompt template for the online proposer

Frozen before the run, per `experiments/online_proposer/PREREGISTRATION.md` §3.
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
