# SlackSmith
### Latency-changing RTL optimization with automatically generated proof obligations

**Nebula @ BITS Goa 2026, Track A (Digital): Constraint Optimization through RTL Enhancement Using Generative AI**

**Team SlackSmith.** Nilay Toshniwal, B.E. Electronics and Communication (senior), BITS Pilani K. K. Birla Goa Campus. Shivani Chaudhary, B.E. Electronics and Communication (2027), BITS Pilani K. K. Birla Goa Campus.

Repository: `github.com/nilaymastaadmi/nebula-slacksmith` (branch `sandbox`). Every number in this report was produced by running the flow; the command that produced each one is in the cited experiment directory.

---

## 1. Summary

An LLM proposes RTL transforms. A formal gate decides whether they are correct. We built both halves, and then we measured the half that everyone assumes works.

The result we would lead with: **we asked an LLM for six transforms against a real timing report, froze them before running any check, and two of six were formally refuted.** One of those two parses, elaborates, passes every precondition, reduces cell count by 208, and is wrong. A testbench running the design's own shipped firmware misses it. Twenty thousand random instruction vectors miss it. The formal gate caught it in 46 seconds.

That is the entire argument of this project in one measurement: **the gates that agentic RTL tools actually ship with would have accepted a broken rewrite.**

---

## 2. The problem, and what is actually new here

Timing closure is manual because static timing analysis speaks in cells and nets while RTL speaks in `always` blocks. An LLM bridges those two representations well. The difficulty is not proposing a rewrite; it is knowing whether the rewrite is correct.

Every published agentic RTL optimizer that holds a formal gate refuses to change latency. Dr. RTL (ICCAD 2026) states it explicitly: it preserves micro-architecture "including pipeline latency", permitting only "latency-preserving sequential restructuring". RTLScout runs on the open Yosys/OpenROAD flow but verifies with `abc cec`, which is combinational and structurally cannot see an added register.

The reason is real. Insert a pipeline stage and the optimized design is no longer equivalent to the original under any conventional miter; it is equivalent only under a latency offset the checker must be told about. So the tools that could check the safe transforms are used, and the profitable ones are forbidden.

**What we built.** Transforms are *typed*. The model does not emit free-text Verilog and hope; it emits a declared transform type, and that declaration mechanically determines which proof obligation is generated. A transform whose obligation cannot be discharged is never reported as a result.

```
   RTL  ──►  Yosys ──► OpenSTA ──►  critical path report
                                          │
                                          ▼
                         ┌────────────────────────────────┐
                         │  LLM: emits a TYPED transform  │
                         │  {def_id, target, k, source}   │
                         └────────────────┬───────────────┘
                                          ▼
              G1 parse ─► G2 elaborate ─► G3 precondition
                                          │
                    the DECLARED type selects the obligation
                                          ▼
        ┌──────────────┬──────────────┬──────────────┬──────────────┐
        │ k=0          │ k>0 rigid    │ k>0 elastic  │ re-encoded   │
        │ equivalence  │ k-padded     │ stream       │ mapped-state │
        │ EQY / dsec   │ miter        │ equivalence  │ + bijection  │
        └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘
               └──────────────┴──── PDR / BMC / k-induction ─┘
                                          │
                        PROVEN ───────────┴─────────── REFUTED
                           │                              │
                    G5 remeasure timing          counterexample, discarded
```

The interface classifier (§6.1) decides rigid versus elastic; the declared latency delta decides padded versus plain. Nothing about that routing is left to the model.

| declared | obligation branch | discharged by |
|---|---|---|
| k = 0, state-preserving | combinational / sequential equivalence | EQY, `yosys-abc dsec` |
| k > 0, rigid interface | k-padded miter | SymbiYosys, BMC + PDR |
| k > 0, elastic interface | stream equivalence | SymbiYosys + `cover` |
| k = 0, re-encoded state | mapped-state equivalence | SymbiYosys with supplied bijection |

All four branches are proven on real RTL, not toys (§6).

---

## 3. Deliverable coverage

| # | Organizer deliverable | Where it is evidenced |
|---|---|---|
| 1 | RTL timing analysis framework | §5, `sdc/bench_top.sdc`, `tools/remeasure.py` |
| 2 | GenAI-based RTL optimization engine | §7, `experiments/llm_proposer/`, `tools/gate_proposal.py` |
| 3 | Critical path and timing violation analysis | §5, `docs/measurement-methodology.md` |
| 4 | Optimized RTL implementation | §8, `rtl/rv32i_core_P{1,2,3,6}.v` |
| 5 | Timing, frequency and PPA comparison | §8, `experiments/ppa/` |
| 6 | Formal equivalence verification report | §6, `experiments/*/NOTES.md` + logs |
| 7 | Interactive demo | demo video, §10 |
| — | Benchmark: 5 async domains, generated clocks, CDC, dividers, ~50K cells | §4, `rtl/bench_top.v` |

---

## 4. The benchmark

`bench_top` is **55,413 standard cells**, five independent asynchronous clock domains, each with its own active-low async reset and each driving at least one in-RTL generated clock.

| domain | clock | divider | contents |
|---|---|---|---|
| A | `clk_a` | /2 | 8-bit MAC datapath + **RV32I core** running a real instruction loop |
| B | `clk_b` | /3 | 10-state control FSM + LFSR + **AES-128** |
| C | `clk_c` | /4 | UART-style shift block |
| D | `clk_d` | /5 | reloading timer, two compares |
| E | `clk_e` | /2 | 16 x 32-bit config file + **AES-128** |

Crossings form a ring A→B→C→D→E→A. Every multi-bit crossing is a gray-pointer async FIFO; every single-bit control crossing is a two-flop synchronizer:

| # | src → dst | signal | structure | launch | capture |
|---|---|---|---|---|---|
| 1 | A → B | `a2b_wdata[15:0]` | `async_fifo` DW=16, 8 deep | `clk_a/2` | `clk_b/3` |
| 2 | B → C | `b2c_ctrl` (toggle) | `sync2ff` | `clk_b/3` | `clk_c/4` |
| 3 | C → D | `c2d_wdata[7:0]` | `async_fifo` DW=8, 8 deep | `clk_c/4` | `clk_d/5` |
| 4 | D → E | `d2e_ctrl` (toggle) | `sync2ff` | `clk_d/5` | `clk_e/2` |
| 5 | E → A | `e2a_wdata[31:0]` | `async_fifo` DW=32, 4 deep | `clk_e/2` | `clk_a` |

Four of the five crossings both launch *and* capture on generated clocks, which is the constraint case that makes this benchmark harder than a single-clock design. Single-bit crossings carry a toggle rather than a pulse, so a slow destination cannot miss a narrow source pulse. Inside the FIFOs the crossing pointer is gray-coded (`bin ^ (bin >> 1)`, exactly one bit changing per increment) and `full`/`empty` are registered from the *next* pointer value, so they never combinationally depend on the increment inputs and a consumer driving `rinc = ~rempty` cannot form a loop.

**The /3 and /5 dividers are the deliberate difficulty.** An odd ratio cannot be split evenly by posedge logic alone, so `clkdiv.v` runs two counters, one on each edge, and ANDs their phase flags. We verified the result rather than asserting it: simulated over 2,000 ns with an off-grid reset release, every high and low segment measures **exactly 15.000 ns (/3) and 25.000 ns (/5)**, 65 and 39 segments respectively, minimum segment equal to the mean, so no glitch. The SDC must then describe generated clocks whose edges derive from *both* edges of the source, which is the constraint case this benchmark exists to exercise.

Third-party content: the AES-128 core is `secworks/aes`, BSD-2-Clause, vendored unmodified under `rtl/aes/` with its license and a `THIRD_PARTY.md`. The RV32I core is our own, from `rv32-dsp-soc`, where it is verified against a golden C++ instruction-set simulator over a 400-seed, 132,400-instruction differential regression.

---

## 5. Timing analysis framework, and three findings about measurement

The SDC is **written once and frozen** before any optimization runs. The agent never edits constraints, and timing exceptions including multi-cycle paths are excluded from the transform set entirely, so no reported improvement can come from relaxing the measurement.

Generated-clock `-edges` for the odd dividers were derived by hand from the divider's edge arithmetic and then cross-checked three independent ways: the hand trace, an Icarus simulation, and OpenSTA's own `report_clock_properties` reading the finished SDC. All three agree to the decimal (`clk_b_div3` 16.5/16.5 of 33 ns; `clk_d_div5` 32.5/32.5 of 65 ns).

The derivation, since this is the part a reviewer should be able to check. For odd `DIV` the output rises when the later of the two phase flags rises and falls when the earlier falls, giving master-edge indices

    rise @ 2*DIV      fall @ 2*(DIV + (DIV+1)/2) - 1      next rise @ 4*DIV

so `DIV=3` → `{6 9 12}` and `DIV=5` → `{10 15 20}`:

```tcl
create_generated_clock -name clk_b_div3 -source [get_ports clk_b] \
    -edges {6 9 12} [get_nets clk_b_div3]
create_generated_clock -name clk_d_div5 -source [get_ports clk_d] \
    -edges {10 15 20} [get_nets clk_d_div5]

set_clock_groups -name async_domains -asynchronous \
    -group {clk_a clk_a_div2} -group {clk_b clk_b_div3} \
    -group {clk_c clk_c_div4} -group {clk_d clk_d_div5} \
    -group {clk_e clk_e_div2}
```

That single `set_clock_groups` is also what correctly exempts every synchronizer path from ordinary setup/hold analysis: those paths are built to tolerate metastability, not to meet a same-domain check. No per-path exception is used anywhere, and **no `set_multicycle_path` appears in the file at all**, because a multicycle exception can manufacture slack without changing the design.

Three findings changed how we report every number (`docs/measurement-methodology.md`):

**A single library cell was worth 4.83 ns of pure artifact.** The first critical path showed 19.5 ns of a 33.0 ns path sitting in *two cells*. That is drive, not logic depth, so we investigated before reporting it. `abc -D 8000` produced a byte-identical netlist, ruling out mapping effort. The culprit was `sky130_fd_sc_hd__lpflow_isobufsrc_1`, a low-power isolation cell ABC selected on area cost. Excluding the `lpflow` and `probe` families, as standard sky130 flows do, moved WNS from **−27.37 to −22.54 with zero RTL change**.

**The measurement tool has a zero noise floor.** Swapping a module for *itself* returns 0.000 delta on every path group. Synthesis and STA are deterministic here, so every nonzero delta is real and reproducible.

**Local RTL changes have non-local timing effects.** Given the null control above, the +1.398 ns that a `domain_b`-only change produces on `clk_a` is not noise: it is ABC's global technology mapping moving an unrelated path group. **Reporting rule adopted:** a transform's effect is the delta in the group it touches; movement elsewhere is reported separately and never folded into the claimed benefit.

Disclosed limitation: after the `lpflow` fix a 5.66 ns single-cell delay remains, which is high fanout with no buffer-insertion pass. This flow stops at technology mapping; a repair or P&R step (OpenROAD `repair_design`) would address it. Our reported violations are therefore an upper bound.

---

## 6. Formal equivalence: four branches, all on real RTL

| transform | branch | verdict | engine |
|---|---|---|---|
| `fsm_reencode(domain_b)` | 4, mapped-state | **PROVEN unbounded** | PDR |
| `mux_priority_to_parallel(domain_b_onehot)` | 1, scoped | **PROVEN unbounded** | PDR |
| `pipeline_cut_rigid(domain_a)` | 2, k-padded | **PROVEN unbounded** | PDR |
| `pipeline_cut_elastic(sync_fifo)` | 3, stream equivalence | **PROVEN unbounded** | PDR + `cover` |
| one-hot state invariant | supporting lemma | **PROVEN unbounded** | k-induction |

**We measured what the existing checkers do**, rather than asserting it. Given a correct latency-changing transform, with a positive control run first in every case:

| checker | control | correct latency-+1 transform |
|---|---|---|
| `yosys-abc cec` | equivalent | **cannot build the miter** ("different number of latches") |
| `yosys-abc dsec` | equivalent | **NOT EQUIVALENT** |
| EQY | PASS | **FAIL**, 1/1 partitions |
| k-padded miter | — | **PASSED, unbounded** |

They fail for different reasons, and the difference matters: `cec` cannot express the question, while `dsec` and EQY express it and correctly answer no, because the designs genuinely are not cycle-for-cycle equivalent. None can express equivalence *modulo k cycles*, so a pipeline gated on any of them can only ever reject a latency change. That is measured evidence for the routing decision, not an argument.

**We mutation-tested our own checker, and it failed.** The stream-equivalence obligation asserts only once both designs have completed a transaction. We built a mutant reproducing a real documented deadlock bug, confirmed by simulation that it never produces output, and ran the proof: **PDR reported PROVEN in 0 seconds** for a design that deadlocks. The assert was vacuously true because its guard was unreachable. Fixed with a `cover` property, validated to distinguish the real design (REACHED) from the mutant (UNREACHABLE), and now a standing task in the tooling. We found this by testing the verifier, not the design.

### 6.1 Choosing the branch: the interface classifier

A k-padded obligation is *wrong* for an elastic interface. We measured that too: pointed at a valid/ready pair with back-pressure, the k-padded miter is **refuted in 0 seconds on a design that is correct**, because under back-pressure the two designs hold different numbers of in-flight transactions and no fixed cycle offset exists. A tool that emits the wrong obligation reports a correct transform as broken.

So the branch is chosen automatically, in three passes, each able to overrule the last:

1. **Lexical**: candidate handshake ports by name (`ready`, `rdy`, AXI `t*` prefixes).
2. **Structural**: does the candidate actually reach a flop's D or enable cone? A signal that never reaches sequential state cannot stall anything.
3. **Formal**: prove output stability under back-pressure, so the verdict is a discharged obligation rather than a heuristic.

| module | lexical | structural | formal | verdict |
|---|---|---|---|---|
| `mac_ref` (rigid) | no candidate | — | — | RIGID |
| `mac_vr_ref` | `out_ready` | reaches `$dff.D` | PASSED | ELASTIC |
| `alias_names` (`vld`/`rdy`) | `o_rdy` | reaches `$dff.D` | PASSED | ELASTIC |
| `axi_style` (AXI prefixes) | `m_axis_tready` | reaches `$dff.D` | PASSED | ELASTIC |
| `costume_ready` | `out_ready` | **REJECTED** | **FAILED** | **RIGID** |

`costume_ready` is the case that earns the machinery: handshake-shaped port names, not an elastic interface. Both later passes reject it by *independent* arguments, the signal never reaching state and the data changing while stalled.

Two honest limits. Pass 3 is bounded (depth 16), not an unbounded proof, and is reported as such. And credit-based or otherwise exotic flow control will miss the lexical pass and be classified rigid, which is the unsafe direction; the correct default for an unrecognised interface is elastic, and that is not yet implemented.

### 6.2 Why simulation is not a substitute, measured on four mutants

Before the LLM experiment we measured the same question on hand-built mutants of a known-correct transform, with a correct control:

| mutant | lazy testbench | aggressive testbench | formal |
|---|---|---|---|
| `mut0_correct` (control) | PASS | PASS | **PASSED** |
| `mut1_stale_c` | **PASS** | FAIL | **FAILED** |
| `mut2_rare` | **PASS** | **PASS** | **FAILED** |
| `mut3_trunc` | FAIL | FAIL | **FAILED** |

`mut1_stale_c` is the classic pipelining bug, stage 2 adding the current operand to a product one cycle old, and it is invisible to a testbench that holds that operand constant, which is exactly what a directed test looks like. `mut2_rare` survived 20,000 random vectors in both regimes and formal refuted it instantly. §7 reproduces this result on a real LLM proposal rather than a hand-built mutant.

---

## 7. The GenAI engine, and the experiment we pre-registered

The model receives the OpenSTA critical-path report, the target RTL and the typed transform schema, and emits a declared transform type plus replacement source. The declaration selects the obligation; `tools/gate_proposal.py` runs five gates in order: **parse, elaborate, precondition, formal, timing.**

To measure this honestly we **pre-registered the experiment before writing any proposer code**, and git proves the ordering (`4ee45c2` precedes `7e3ab9b` precedes the results). The registration fixed N = 6, fixed the gates, and fixed the anti-tuning rule: *all six proposals committed before any gate ran, none editable afterwards, all six reported regardless of outcome.*

| | transform | declared | parse | elab | precond | **formal** | timing (clk_a) |
|---|---|---|---|---|---|---|---|
| P1 | addsub sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | −2.471 |
| P2 | shifter sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | **+0.829** |
| P3 | comparator sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | −2.051 |
| P4 | mux priority→parallel | k=0 | ✓ | ✓ | ✓ | **REFUTED** | — |
| P5 | pipeline cut | k=1 | ✓ | ✓ | ✓ | **REFUTED** | — |
| P6 | branch cmp sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | −3.400 |

**4 proven, 2 refuted, 1 improved timing.** The registered primary bar was met by P2, which is also the only proposal both smaller (−351 cells) and faster.

### P4: the proposal that was wrong in the way that matters

P4 one-hot decoded `funct3` and OR-ed the masked arms. It parses, elaborates, passes preconditions and saves 208 cells. EQY refuted it in 46 seconds, isolating **one failing partition out of 447**: `alu_out`.

It had folded the shift arms into a ternary:

```verilog
wire [31:0] r_shr = alt ? ($signed(a) >>> shamt) : (a >> shamt);
```

A conditional operator's signedness derives from *both* branches. Pairing a signed branch with an unsigned one makes the whole expression unsigned, that context propagates back into the operands, and `>>>` silently degrades to a logical shift. SRA is then wrong for every negative operand.

`rv32i_core.v` carries a six-line comment warning about exactly this, **ten lines above the code being transformed.** The model had that file as input and made the documented mistake anyway.

### The four-checker column on P4

| checker | verdict |
|---|---|
| EQY (formal) | **CAUGHT**, 46 s |
| simulation, the design's own shipped firmware loop, 400 cycles | **MISSED** |
| simulation, 20,000 random instruction words | **MISSED** |
| simulation, directed SRAI on a negative operand | CAUGHT |

We ran the directed probe specifically so the two misses could not be mistaken for a phantom defect: the bug is fully visible to simulation (gold `ffffffff`, gate `0fffffff`). Both misses are stimulus weakness. The shipped firmware loop contains no shift instruction at all, so it can never reach the bug. **The verdict tracks stimulus quality, not bug severity.**

P5 shows the k-padded obligation doing its job in the other direction: refuted in 1 second because `alu_out` feeds the register file and PC, so a declared k = 1 shift is not what the transform actually does.

---

## 8. Optimized RTL and PPA

Core level (`rv32i_core` alone, transform is 100% of the design; reset false-pathed, otherwise the recovery check masks the data path):

| variant | cells | data WNS (ns) | power (mW) |
|---|---|---|---|
| gold | 6,769 | −9.84 | 6.26 |
| P1 | 6,702 | −9.46 | 6.25 |
| P2 | **6,441** | −9.81 | **6.20** |
| P3 | 6,700 | −12.65 | 6.62 |
| P6 | 6,864 | **−7.88** | 6.38 |

Expressed as frequency, which is what deliverable 5 asks for: at core level a 10 ns constraint with −9.84 ns of violation means a required period of 19.84 ns, so **F_max 50.4 MHz for the baseline core and 55.9 MHz with P6**, an 11.0% improvement. At design level the 8 ns `clk_a` constraint with −25.287 ns gives a required period of 33.29 ns, **F_max 30.0 MHz**, which is an upper bound given the missing buffer-insertion pass noted in §5.

**The rankings invert between contexts.** By core timing the best transform is P6 (+1.96 ns); at design level P6 is the worst (−3.400 ns), and the only design-level winner is P2, which is nearly neutral at core level. Two real mechanisms: the core's critical path is not the design's (inside `bench_top` the binding path runs through the wrapper's async-read memory and its fanout, not the ALU cone), plus the non-local remapping quantified in §5.

We report both contexts for all four transforms. A report quoting only the core table would name P6 the best transform; one quoting only the design table would name it the worst.

Power is vector-free at default switching activity: a relative comparison between variants, not an absolute silicon figure. At design level power is flat at 223–224 mW across all variants, because a 351-cell change is 0.6% of a 55K design and below the method's resolution. We report that as a null rather than as a 1 mW difference.

---

## 9. What we got wrong

Judged work should show its corrections, so here are ours, all committed with the evidence.

**Two of five registered predictions were wrong.** We predicted at least one proposal would be rejected at the precondition gate; **zero were**. The precondition layer as built is a type check, not a legality check, and the formal gate did all the real filtering. We also predicted latency semantics would dominate the failure modes; it was one of each. Both were registered in advance, one at explicitly low confidence, so the misses are visible rather than forgotten.

**A claim that was false, caught by simulation.** We had described `pipeline_cut_rigid(domain_a)` as boundary-proven *and therefore* module-equivalent. It is not: a testbench shows `mac_result` diverging permanently (`002a` vs `0031`), because the consuming domain samples at half rate and a one-cycle delay selects a different subsequence rather than shifting the stream. The proof stands for the property it states; the sufficiency claim was withdrawn and the refuting testbench committed.

**A number that was nearly published six times too large.** P2's improvement first measured +5.105 ns against a baseline built by a slightly different flow. Rebuilt identically: **+0.829 ns**.

**An interoperability gap that nearly hid our only success.** P2 is the one proposal using a Verilog `function`. Yosys names function temporaries with an embedded absolute path and colon, which OpenSTA's Verilog reader rejects, so a netlist that synthesized cleanly could not be timed at all (1,386 such names). `opt_clean -purge` fixes it. Without that fix the batch's single winner would have been recorded as unmeasurable.

**A tool that a comment could break.** `remeasure.py` matched `//` as a module name, so `bench_top.v`'s own documentation counted as a second instantiation and the tool refused to run.

**An attempted fix that did not work, and is reported as closed rather than pending.** Two proofs needed PDR where single-step k-induction failed. We tried wiring a real divider into the harness to fix it. That surfaces a genuine Yosys limitation (opposite-polarity clocking needs `clk2fflogic`), and `clk2fflogic`'s clock-as-data modelling then makes BMC on this dual-edge divider intractable: step cost climbed past 30 s by depth 28. **PDR is therefore confirmed as the correct tool for these properties, not a workaround** for a proof we never attempted.

---

## 10. Demo, reproduction, limits

The demo video walks the pipeline end to end on the real benchmark: a timing report, a proposed typed transform, the obligation generated from its declared type, the prover portfolio running, and a refutation with its counterexample. The refutation is the part worth watching, because it is the case every simulation-gated tool would have passed.

Everything reproduces from the repository. Each experiment directory holds its sources, its `.sby` or `.eqy` configuration, and its raw logs; proofs re-run with `sby -f <config> pdr` or `python3 tools/run_proof.py`. Cold-clone reproduction was verified by copying each experiment directory alone into a scratch tree and running the committed configuration unchanged.

**Limits we would rather state than be asked.** N = 6 proposals, one batch, one target module, one model: these are outcomes, not rates with confidence intervals. The flow stops at technology mapping, so absolute violation numbers are an upper bound and no place-and-route data is included. The precondition layer did not screen anything in this batch. And the four transforms that are formally proven correct mostly made timing worse, which is the honest result: **proof and profit are independent questions, and we measured both.**
