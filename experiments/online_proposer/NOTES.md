# The online proposer: results and scoring

Registered in `PREREGISTRATION.md` before `tools/proposer.py` existed, with one
amendment dated before the run. Run 1 is `results/run1_decisions.jsonl`; every
request and every response is in `results/handoff/`, including `REQUEST_O3.md`,
which produced nothing.

## The headline

**The loop generated a transform against live timing state, proved it, applied
it and kept it.** That is the generative half of "closed loop" working end to
end for the first time in this project.

| | O1 | O2 |
|---|---|---|
| class | `array_write_decode_split` | `array_read_mux_two_level` |
| declared | k = 0, branch 1 (EQY) | k = 0, branch 1 (EQY) |
| G3 | PASS | PASS |
| G4 | **PROVEN** | **PROVEN** |
| `clk_e` | −25.957 → **−24.079** (+1.878) | −24.079 → **−35.513** (−11.434) |
| G5 total | −58.081 → −53.963, improved | −53.963 → −77.787, not improved |
| outcome | **CONFIRMED** | **REVERTED** |

**O2 is the more useful of the two.** It is formally proven equivalent and it
made the design 11.434 ns worse on the binding group and the same on `clk_b`.
Proof and profit are independent questions, and here the gate proved a
transform correct while the measurement rejected it, in one run, on a proposal
generated minutes earlier.

## Scorecard

| # | registered | outcome |
|---|---|---|
| **O1** | at least one online proposal passes G1 to G4 | **CONFIRMED**, both did |
| **O2** | at least one is formally REFUTED at G4 | **WRONG so far.** Both proven. N = 2 |
| **O3** | the loop does not close the benchmark | **CONFIRMED**, all three groups still violating |
| **O4** | online no better than frozen at G5 | **inconclusive at N = 2.** 1 of 2 online proven-and-improving (50%) against 4 of 12 frozen (33%). Not a rate |
| **O5** | a different transform class from the frozen batches | **CONFIRMED**. Frozen batches were operator sharing on `rv32i_core`; both online proposals are memory-structure transforms on `aes_key_mem`, because that is where the live path bound |
| **O6** | at least one rejected before G4 | **WRONG so far.** Both cleared G1 to G3. N = 2 |

O2 and O6 are recorded as wrong rather than as pending. The run reached its
N and stopped; a later run that refutes something does not retroactively make
these hits.

## The mechanism I claimed was wrong, and the number was still real

O1's stated rationale was that splitting the write-address decode would remove
the shared term driving 300 loads. **It did not.** After O1 the binding path
carries a `nor4_1` at **293** loads worth 21.585 ns, against 300 loads worth
21.029 ns before. Yosys re-shares common subexpressions, so removing the
sharing in RTL does not remove it from the netlist.

The +1.878 ns is real, formally proven and confirmed by re-measurement. The
explanation attached to it was wrong. Those are two separate claims and only
the first one was measured, so only the first one is asserted.

## A loop defect this run exposed: revert discards confirmed work

Iteration 4 measures `clk_a −13.167, clk_b −18.957, clk_e −25.957`, which is
**byte-identical to the iteration 1 baseline**. O1 had been CONFIRMED two
iterations earlier and worth +1.878 ns. Reverting O2 threw it away.

The cause is one line:

```python
if not improved:
    file_subs.pop(pending["key"], None)     # restores the PRISTINE source
```

`file_subs` maps a source file to the variant currently substituted for it.
Both proposals target `aes/aes_key_mem.v`, so applying O2 overwrote O1's entry,
and reverting O2 popped the key entirely rather than restoring O1's variant.
**The loop silently lost a confirmed gain.**

This was invisible to every earlier run because frozen proposals were reverted
before any other transform on the same file had been confirmed. It takes two
accepted transforms on one file to see it, and only an online run got there.

The verdicts above are unaffected: O1 and O2 were each gated and measured
against the state that actually preceded them. What the defect corrupted is
everything after the revert, which is why iteration 4 restarts from baseline
and why this run's N stops at 2.

## What this run does not show

- **The `cli` backend was not exercised.** The OAuth session on this machine is
  expired. `handoff` proves the loop can consume a freshly generated transform;
  it does not prove the loop can run unattended.
- **The router did not choose RTL.** It chose `physical` at every iteration,
  with the path 91.4% and then 98.95% fanout-attributable. `--force-lever rtl`
  overrode it, logged as `lever_forced`, per amendment 1. Nothing here says an
  RTL transform was the right tool for this path; the measured evidence says it
  was not.
- **N = 2**, one design, one SDC, one model, one sample of a nondeterministic
  proposer. Outcomes, not rates.
- **`REQUEST_O3.md` timed out with no response** because the operator was away,
  not because the proposer declined. It is committed anyway, since the
  registration says every request is, including the ones that produce nothing.
