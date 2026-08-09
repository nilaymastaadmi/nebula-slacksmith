# SlackSmith — submitted abstract

**Latency-changing RTL optimization with automatically generated proof obligations**
Track: Digital — Constraint Optimization through RTL Enhancement Using Generative AI
Status: **SUBMITTED 9 Aug 2026**, as written below.

> See the "Known corrections" section of the root README — four claims below need
> scoping in the final report. Citations were verified *after* submission and the
> two named papers both check out; the framing around them does not.

---

Every agentic RTL optimiser published in 2026 leaves latency alone. Dr. RTL, the
strongest of them at 21.3% WNS improvement, preserves the micro-architecture
"including pipeline latency". RTLScout runs on Yosys and OpenROAD but verifies
with `abc cec`, which cannot see an added register. Proving equivalence across
differing latencies is itself old work, formalised by Burch and Dill in 1994 and
sold today in JasperGold, but it is always set up by hand, in commercial tools,
on single-clock designs.

SlackSmith proposes transforms that change latency and writes their proof
obligation itself. For a transform adding k cycles it builds a miter against a
golden design padded with k matched output registers, discharges it in
SymbiYosys, and emits assertions that the pipeline is stall-free and flushes
correctly, since a pipeline can match on quiet traces and still corrupt data
under back-pressure. Latency-preserving rewrites route to EQY and `yosys-abc
dsec` instead. Nothing is reported unless it is discharged, and bounded proofs
are labelled bounded. Because every transform carries a proof, we can also
measure how often the model is wrong, and report the rate at which formally
invalid rewrites would have been accepted without verification, with a
counterexample for each.

The benchmark grows from RTL we already own and have verified against a golden
C++ instruction-set simulator: an RV32I core, an AXI clock-domain-crossing
bridge, AES-128 and peripherals, reaching five asynchronous clock domains and
roughly 50K cells. Its SDC is frozen and published before any optimisation runs,
timing exceptions are excluded from the transform set, and results are reported
in absolute nanoseconds against three baselines: Yosys at maximum effort, Yosys
with `abc -dff` retiming enabled, and RTLScout. We promise no percentage, only
the measured deltas and the proof artifacts behind them.

---

## Verification status of claims in this abstract

| Claim | Verdict |
|---|---|
| Dr. RTL exists (arXiv 2604.14989, ICCAD'26, HKUST) | ✅ verified |
| "21.3% WNS improvement" | ✅ verified, correctly attributed |
| Dr. RTL "preserves… including pipeline latency" | ✅ verified — and its repo's own agent config lists `Add/remove pipeline stages` under **Forbidden** and `Never change latency` in its behavioral contract |
| RTLScout exists (arXiv 2606.06530, Huawei Zürich) | ✅ verified |
| RTLScout verifies with `abc cec` | ✅ verbatim correct — but it is the *secondary* gate, and skipped on most sequential benchmarks |
| Burch & Dill 1994 (CAV, LNCS 818, pp.68–80) | ✅ exists, but formalises **processor-vs-ISA** verification via flushing, not general latency-differing equivalence |
| "always set up by hand" | ⚠️ partially contradicted by Baumgartner et al., ICCD 2006 — automated transformation-tolerant SEC covering retiming and re-pipelining |
| "Every agentic RTL optimiser… leaves latency alone" | ❌ false as literally stated — needs rescoping |
| EQY cannot express a latency difference | ✅ confirmed architecturally — its model is register *correspondence*; an added register has no counterpart to match. **The routing decision in this abstract is correct.** |
