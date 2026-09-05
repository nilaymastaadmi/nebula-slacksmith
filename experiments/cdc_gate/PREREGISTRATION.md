# G7: a clock-domain-crossing gate. Registered before any checker code exists.

**Written 2026-09-05. Committed before `tools/cdc_check.py` exists.** Git is the
evidence for that ordering, the same way `experiments/llm_proposer/` does it.

## Why this gate

`REPORT.md` §10 states a limit in its own words:

> Neither CDC case is detected as a CDC defect by anything here, our own
> checker included. Functional equivalence has no notion of a protocol.

That is true and it is a hole. The benchmark has five asynchronous domains,
gray-pointer FIFOs on every multi-bit crossing and two-flop synchronizers on
every single-bit one, and the project has no check that any of that is right.
G0 to G6 all answer questions about *function*. A CDC defect is not a function
defect, which is exactly why SlackBench's two CDC cases are the two cases every
checker in §7.4 gets for the wrong reason or cannot express at all.

## What the gate checks, defined before it is built

Operating on the **Yosys-elaborated RTL**, not the mapped netlist: clock
domains and register boundaries are unambiguous before technology mapping and
are not after it.

- A **crossing** is a net driven by logic clocked in domain S and sampled by a
  flop clocked in domain D, with S and D different clocks.
- **Synchronizer depth** is the number of back-to-back flops in D from the
  crossing point to the first fanout use, with no combinational logic between
  them.
- A **multi-bit crossing** is a crossing whose source is a vector of width > 1.
- **Hamming safety**, the property that matters for a multi-bit crossing:
  for the source register R in domain S, at every reachable cycle the next
  value differs from the current one in **at most one bit**. Gray coding is one
  way to satisfy it; the gate checks the property, not the encoding, so a
  design that achieves it another way passes and a design that gray-codes on
  the wrong side of the boundary fails.

Discharged with the tools already in the project: structural analysis in Yosys
for depth, and SymbiYosys for Hamming safety, which is a temporal property and
therefore something formal can answer and equivalence cannot.

**Verdicts:** `SAFE`, `DEPTH_n` (n < 2), `MULTIBIT_UNSAFE` (with a
counterexample naming two consecutive values and the bits that differ),
`UNCLASSIFIED`. `UNCLASSIFIED` is first-class and is reported separately from a
violation, on the same principle as `CANNOT` in SlackBench: a crossing the gate
cannot reason about must not be silently called safe.

## Registered predictions

Scored as written, including the misses.

| # | prediction | confidence |
|---|---|---|
| **C1** | The depth check flags `slackbench/cases/CDC-1/gate.v` as `DEPTH_1` and passes its `gold.v`. This is the case the report says nothing here detects. | high |
| **C2** | The Hamming check refutes `CDC-2/gate.v` with a counterexample in which two consecutive values of the crossing register differ in **more than one bit**, and proves `CDC-2/gold.v`. | high |
| **C3** | On `bench_top`, all **6** `async_fifo` gray-pointer crossings (3 instances, 2 pointers each, 4 bits wide) prove Hamming safe. | medium |
| **C4** | On `bench_top`, the depth check reports **zero** `DEPTH_n` violations, because every crossing goes through `sync2ff`, which is two deep. | medium |
| **C5** | The gate does **not** come back clean on `bench_top`. I expect **1 to 5 `UNCLASSIFIED`** crossings, most likely around the `clkdiv`-generated clocks and reset synchronization, which are crossings by the structural definition above but are not data crossings. | medium |
| **C6** | The gate produces **at least one false positive**: a crossing that is safe because of a handshake protocol rather than its encoding, which this gate cannot see and will therefore flag. Structural CDC checking cannot verify a protocol. | medium |

**C5 and C6 are registered because I expect them to be true.** A CDC checker
that reports a clean sheet on a 55K-cell design with five domains is far more
likely to be broken than to be right, and a gate with no false positives on
this class of problem would mean it is not looking hard enough.

## What would make this gate worthless

- **If it flags nothing on the two CDC cases**, C1 and C2 both fail and the
  gate adds nothing over the checkers already in §7.4.
- **If it flags everything**, it is a linter with the threshold set to noise
  and its findings carry no information.
- **If bench_top's own gray pointers fail C3**, either the gate is wrong or the
  benchmark's CDC is wrong. Both are reportable; guessing which without
  checking is not.

## Anti-tuning rule

Thresholds and definitions are fixed above. If a definition has to change after
seeing output, the change is dated, the reason is recorded, and **the run that
prompted it is kept and reported**, exactly as amendment 1 and amendment 2 were
handled in `experiments/slackbench/`. Cases are not added after results are
visible.

## Honest limits, stated before results

- **This is structural and temporal, not physical.** It says nothing about
  actual metastability probability, MTBF, or whether the synchronizer's flops
  are placed close enough to make the depth meaningful.
- **A two-flop synchronizer is a convention, not a proof.** Depth 2 is what
  this gate accepts because it is what the design uses; some domains need three.
- **Protocol correctness is out of scope.** Handshakes, request/acknowledge and
  FIFO full/empty logic are not verified, which is what C6 registers.
- **One design.** bench_top plus two purpose-built cases is not a rate.
