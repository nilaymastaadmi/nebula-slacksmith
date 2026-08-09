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

## Second result: the obligation must depend on the interface

[`experiments/vr_miter/`](experiments/vr_miter/NOTES.md) points the *same*
k-padded obligation at a valid/ready pair with back-pressure. It is **refuted in
0 seconds** — and the design is correct. Stream equivalence proves the same pair
holds.

| Obligation | BMC(20) | k-induction |
|---|---|---|
| k-padded (wrong for this interface) | **REFUTED** | refuted |
| stream equivalence (right) | **PROVED BOUNDED** | unresolved |

The first assertion to break is *valid alignment*, not data: under back-pressure
the two designs hold different numbers of in-flight transactions, so no fixed
cycle offset exists. **A tool emitting a k-padded obligation for a valid/ready
interface reports a correct transform as broken.**

That gives the two-branch rule its evidence:

```
rigid interface        -> k-padded miter       (proved unbounded)
valid/ready interface  -> stream equivalence   (proved bounded)
```

Automatically choosing between them from the interface is the core technical
idea, and it is now motivated by a measured false negative rather than an
argument.

## Third result: the obligation is now chosen automatically

[`experiments/classify/`](experiments/classify/NOTES.md) picks the obligation
from the interface, in three passes — lexical, structural, formal.

| Module | Lexical | Structural | Formal | Verdict |
|---|---|---|---|---|
| `mac_ref` | no candidate | — | — | **RIGID** |
| `mac_vr_ref` | `out_ready` | reaches `$dff.D` | PASSED | **ELASTIC** |
| `alias_names` (`vld`/`rdy`) | `o_rdy` | reaches `$dff.D` | PASSED | **ELASTIC** |
| `axi_style` (AXI prefixes) | `m_axis_tready` | reaches `$dff.D` | PASSED | **ELASTIC** |
| `costume_ready` | `out_ready` | **REJECTED** | **FAILED** | **RIGID** |

Pass 3 proves **output stability under back-pressure** — valid held with ready
low must leave data and valid unchanged — so the verdict is a discharged
obligation rather than a heuristic.

`costume_ready` is the case that earns the machinery: handshake-shaped ports, not
elastic. Both later passes reject it by *independent* arguments — the signal
never reaches state, and the data changes while stalled.

**Known unsafe direction:** exotic flow control (credit-based) misses the lexical
pass and is classified rigid, which would emit a k-padded miter for an elastic
interface. Unknown should default to elastic. Not yet done.

## Fourth result: the existing checkers, measured

[`experiments/cec_check/`](experiments/cec_check/NOTES.md) runs the real tools at
the correct transform from `toy_miter/`. Every checker got a positive control
first, so a FAIL means it rejected a correct transform.

| Checker | control | ref vs opt (latency +1) |
|---|---|---|
| `yosys-abc cec` | equivalent ✓ | **cannot build the miter** |
| `yosys-abc dsec` | equivalent ✓ | **NOT EQUIVALENT** |
| **EQY** | PASS ✓ | **FAIL**, 1/1 partitions |
| padded miter | — | **PASSED, unbounded** |

They fail for *different* reasons, and that is the point. `cec` does not answer
"no" — it cannot construct the comparison (`Networks have different number of
latches. Miter computation has failed.`). `dsec` and EQY *can* set up the
comparison and correctly answer no, because the designs are genuinely not
cycle-for-cycle equivalent.

None of them can express equivalence modulo k cycles, so a pipeline gated on any
of them can only ever reject a latency change. **That is the routing decision in
the abstract, now measured rather than asserted.**

## Fifth result: simulation accepts what formal refutes

[`experiments/sim_check/`](experiments/sim_check/NOTES.md) is the fourth checker
and the dangerous direction — not rejecting correct transforms, but **accepting
invalid ones.** It is also what agentic RTL tools actually gate on: RTLScout's
primary gate is a Verilator testbench.

| Mutant | SIM lazy | SIM aggr | FORMAL | |
|---|---|---|---|---|
| `mut0_correct` | PASS | PASS | **PASSED** | control ✅ |
| `mut1_stale_c` | **PASS** | FAIL | **FAILED** | escaped the lazy testbench |
| `mut2_rare` | **PASS** | **PASS** | **FAILED** | **escaped both** |
| `mut3_trunc` | FAIL | FAIL | **FAILED** | simulation worked |

`mut1_stale_c` is the classic pipelining bug — stage 2 adding the current `c` to
a product one cycle old. It is invisible to a testbench that holds `c` constant,
which is precisely what a directed MAC test looks like. **The verdict tracks
stimulus quality, not bug severity** — so a simulation-gated error rate measures
the testbench, not the model.

`mut2_rare` survived 20,000 random vectors in both regimes and formal refuted it
instantly.

**Honest limit: n=3, hand-picked. That is a mechanism, not a statistic.** The
real number needs a corpus of model-proposed rewrites, stratified, with
Clopper–Pearson intervals and a power calculation.

## Next

1. Discharge stream equivalence **unbounded** with a strengthening invariant, or
   record it as permanently bounded and say so.
2. Generate the pass-3 wrapper from the port list (currently template-bound), and
   add the input-side no-loss obligation to complete the elastic contract.
3. Confirm **EQY rejects** the rigid K=1 pair — "we ran it, here is the error"
   beats a citation.
4. Build the corpus for the four-checker matrix. **That is the paper**, and it
   stands alone even if the optimizer improves nothing.

## Reproduce

```bash
apt-get install -y yosys z3      # yosys ships yosys-smtbmc and yosys-abc
cd experiments/toy_miter && ./run.sh 24
```
