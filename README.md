# SlackSmith

**Latency-changing RTL optimization with automatically generated proof obligations.**

Entry for *Nebula* — Astera Labs @ BITS Pilani, Goa campus.
Track: Digital — *Constraint Optimization through RTL Enhancement Using Generative AI*.

---

## The thesis in one line

Every published agentic RTL optimiser that holds a formal gate refuses to change
pipeline latency — not because latency changes are unprofitable, but because
equivalence checking across differing latencies is hard. SlackSmith proposes
transforms that change latency **and writes their proof obligation itself.**

## Status

| | |
|---|---|
| Abstract | Submitted 9 Aug 2026 |
| Shortlisting | 12 Aug 2026 |
| Final submission | 15 Sept 2026 |
| Presentations | 25 Sept 2026, 9 AM |
| **Build window** | **34 days from shortlisting** |

**The spine is proven.** A k-padded miter discharges a real pipelining transform
under k-induction — an unbounded proof, not a bounded check — and three mutants
confirm it is not vacuous. See [`experiments/toy_miter/NOTES.md`](experiments/toy_miter/NOTES.md).

| Case | BMC(24) | k-induction | |
|---|---|---|---|
| K=0, claims latency preserved | FAILED | FAILED | ✅ |
| **K=1, correct** | **PASSED** | **PASSED** | ✅ |
| K=2, wrong latency claim | FAILED | FAILED | ✅ |
| K=1, arithmetic mutated | FAILED | FAILED | ✅ |

## The finding that shapes the plan

**PDR hung >440s on an 8-bit multiplier; SMT proved the same property in under a
second.** SMT reasons about multiplication in the bit-vector theory; AIG-based
PDR bit-blasts it and hits a wall. That is the AES-128 hardness problem in
miniature, found on day one on a toy.

Consequences: engine portfolio racing is load-bearing, not optional. AES will be
the case that times out — say so before a judge finds it. And report three
outcomes, always: **proved / refuted-with-counterexample / unresolved.** A
timeout folded into "passed" is the one thing that destroys credibility with this
panel.

## Layout

```
docs/
  brochure-analysis.md    event facts, all three tracks, failure modes, strategy
  research-findings.md    literature verification, prior art, transplants
  abstracts/              the two abstracts as written
experiments/
  toy_miter/              the day-one de-risking experiment (working)
```

## Known corrections to make in the final report

The abstract was submitted before the literature survey completed. Four claims
need scoping in the report — owning them reads better than being caught:

1. *"Every agentic RTL optimiser published in 2026 leaves latency alone"* is
   false as stated. Generation-mode agents write any latency they like. Rescope:
   none both **changes** latency **and** discharges a formal obligation for it.
2. RTLScout's `abc cec` is its **secondary** gate — the primary is a Verilator
   testbench — and CEC is skipped entirely for most of its sequential benchmarks.
3. Dr. RTL **already reports an 86% SEC pass rate**, so "we measure how often the
   model is wrong" is not new. Reframe to the four-checker matrix: the rate at
   which a *weaker* checker would have wrongly accepted an invalid rewrite.
4. **ASPEN** (MLCAD 2025) and **ROVER** (TCAD 2024) are uncited and close.
   Differentiator: their obligations are equational and combinational and cannot
   express "agree modulo k cycles under back-pressure." Ours is temporal.

Also outstanding: the benchmark needs **generated clocks and multi-ratio dividers**
in the frozen SDC — both are explicit organizer requirements currently unmet.

## Next

1. Repeat the miter on a **valid/ready** pair; confirm it gives a false negative
   under back-pressure. That failure motivates the two-branch obligation generator.
2. Deeper pipelines (K=2,3) without a multiplier, to separate latency scaling
   from solver hardness.
3. Confirm **EQY rejects** the K=1 pair — "we ran it, here is the error" beats a
   citation.
4. Build the corpus for the four-checker matrix. **That is the paper**, and it
   stands alone even if the optimizer improves nothing.

## Reproduce

```bash
apt-get install -y yosys z3      # yosys ships yosys-smtbmc and yosys-abc
cd experiments/toy_miter && ./run.sh 24
```
