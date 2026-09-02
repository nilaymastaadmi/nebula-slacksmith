# SlackSmith
### Latency-changing RTL optimization with automatically generated proof obligations

**Nebula @ BITS Goa 2026, Track A (Digital): Constraint Optimization through RTL Enhancement Using Generative AI**

**Team SlackSmith.** Nilay Toshniwal, B.E. Electronics and Communication (senior), BITS Pilani K. K. Birla Goa Campus. Shivani Chaudhary, B.E. Electronics and Communication (2027), BITS Pilani K. K. Birla Goa Campus.

Repository: `github.com/nilaymastaadmi/nebula-slacksmith` (branch `sandbox`). Every number in this report was produced by running the flow; the command that produced each one is in the cited experiment directory.

---

## 1. Summary

An LLM proposes RTL transforms. A formal gate decides whether they are correct. We built both halves, and then we measured the half that everyone assumes works.

An LLM pointed at a timing report can fail in two different ways, and we measured both. It can propose a transform that is **wrong**, or one that is **correct and aimed at the wrong variable**.

**Failure one, correctness.** We asked an LLM for transforms against real timing reports, froze every proposal before running any check, and ran two pre-registered batches. **3 of 12 were formally refuted, 1 more was rejected at precondition, and 1 is unresolved.** One of the three parses, elaborates, passes every precondition, reduces cell count by 208, and is wrong. A testbench running the design's own shipped firmware misses it. Twenty thousand random instruction vectors miss it. The formal gate caught it in 46 seconds with a concrete counterexample. **The gates that agentic RTL tools actually ship with would have accepted a broken rewrite.**

That count started at 4 refuted. It is 3 because batch 2 caught **our own gate manufacturing a refutation**: EQY prints the same "Failed to prove equivalence" line whether it found a counterexample or merely ran out of depth, and we matched on the string. §7.1 has the correction and the check that it does not cascade.

**Failure two, relevance.** Then we asked whether the transforms that *are* correct actually help. On our benchmark they mostly did not, and the reason is measurable: the binding paths were **59% to 91% fanout-attributable delay**, and no RTL rewrite shortens a net's load delay. Our best formally-proven RTL transform bought **+4.925 ns**. **OpenROAD `repair_design`, changing zero lines of RTL, bought +55.805 ns on the same clock group and closed all three**, at a measured cost of 20.2% area.

So SlackSmith routes twice. It routes the **proof obligation** by declared transform type, which is the original contribution, and it now routes the **fix** by measured path pathology, which the measurement forced on us. The two levers turn out to be sequential rather than alternative: after buffering, the remaining violations are measurably depth-dominated, which is exactly where an RTL transform has something to bite on.

---

## 2. The problem, and what is actually new here

Timing closure is manual because static timing analysis speaks in cells and nets while RTL speaks in `always` blocks. An LLM bridges those two representations well. The difficulty is not proposing a rewrite; it is knowing whether the rewrite is correct.

**Scoped precisely, because the loose version is false.** Generation-mode agents write any latency they like. The accurate claim is that we found no published system that both *changes* latency and *discharges a formal obligation for it*. Dr. RTL (ICCAD 2026) says so explicitly: it preserves micro-architecture "including pipeline latency", permitting only "latency-preserving sequential restructuring". RTLScout runs on the open Yosys/OpenROAD flow; its primary gate is a Verilator testbench, with `abc cec` secondary and skipped entirely on most of its sequential benchmarks, and CEC is combinational so it structurally cannot see an added register.

Two closer neighbours deserve naming rather than omitting. **ASPEN** (MLCAD 2025) and **ROVER** (TCAD 2024) both pair rewriting with formal justification, and both use obligations that are equational and combinational. Neither can express "agree modulo k cycles, under back-pressure". Ours is temporal, which is the actual difference and a narrower claim than novelty.

**And measuring how often the model is wrong is not new either.** Dr. RTL already reports an 86% SEC pass rate. What we did not find measured anywhere is the rate at which a *weaker* checker would have wrongly **accepted** an invalid rewrite, which is the four-checker matrix in §6.2 and §7, and the question that matters if your tool ships with a testbench gate.

The reason latency is off-limits is real. Insert a pipeline stage and the design is no longer equivalent under any conventional miter; it is equivalent only under a latency offset the checker must be told about. So the profitable transforms are forbidden because the available checkers cannot express them.

**What we built.** Transforms are *typed*. The model does not emit free-text Verilog and hope; it emits a declared transform type, and that declaration mechanically determines which proof obligation is generated. A transform whose obligation cannot be discharged is never reported as a result.

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
| n/a | Benchmark: 5 async domains, generated clocks, CDC, dividers, ~50K cells | §4, `rtl/bench_top.v` |

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

Crossings form a ring A→B→C→D→E→A. Every multi-bit crossing is a gray-pointer async FIFO (`a2b_wdata[15:0]` 8 deep, `c2d_wdata[7:0]` 8 deep, `e2a_wdata[31:0]` 4 deep); every single-bit control crossing is a two-flop synchronizer (`b2c_ctrl`, `d2e_ctrl`).

Four of the five crossings both launch *and* capture on generated clocks, which is what makes this harder than a single-clock design. Single-bit crossings carry a toggle rather than a pulse, so a slow destination cannot miss a narrow source pulse. FIFO pointers are gray-coded and `full`/`empty` are registered from the *next* pointer value, so a consumer driving `rinc = ~rempty` cannot form a loop.

**The /3 and /5 dividers are the deliberate difficulty.** An odd ratio cannot be split evenly by posedge logic alone, so `clkdiv.v` runs two counters, one per edge, and ANDs their phase flags. Simulated over 2,000 ns with an off-grid reset release, every segment measures **exactly 15.000 ns (/3) and 25.000 ns (/5)**, no glitch. The SDC must then describe generated clocks whose edges derive from *both* source edges, which is the constraint case this benchmark exists to exercise.

Third-party content: the AES-128 core is `secworks/aes`, BSD-2-Clause, vendored unmodified under `rtl/aes/` with its license and a `THIRD_PARTY.md`. The RV32I core is ours, from `rv32-dsp-soc`, verified against a golden C++ instruction-set simulator over a 400-seed, 132,400-instruction differential regression.

---

## 5. Timing analysis framework, and three findings about measurement

The SDC is **written once and frozen** before any optimization runs. The agent never edits constraints, and timing exceptions including multi-cycle paths are excluded from the transform set entirely, so no reported improvement can come from relaxing the measurement.

Generated-clock `-edges` for the odd dividers were derived from the divider's edge arithmetic (`rise @ 2*DIV`, `fall @ 2*(DIV + (DIV+1)/2) - 1`, `next rise @ 4*DIV`, so `DIV=3` gives `{6 9 12}`) and cross-checked three independent ways: the hand trace, an Icarus simulation, and OpenSTA's `report_clock_properties`. All three agree to the decimal.

One `set_clock_groups -asynchronous` over the five domains is also what exempts every synchronizer path from ordinary setup/hold analysis. No per-path exception is used anywhere, and **no `set_multicycle_path` appears in the file at all**, because a multicycle exception manufactures slack without changing the design.

Three findings changed how we report every number (`docs/measurement-methodology.md`):

**A single library cell was worth 4.83 ns of pure artifact.** The first critical path put 19.5 ns of 33.0 ns in *two cells*, which is drive, not logic depth. The culprit was `sky130_fd_sc_hd__lpflow_isobufsrc_1`, a low-power isolation cell ABC selected on area cost. Excluding the `lpflow` and `probe` families, as standard sky130 flows do, moved WNS from **−27.37 to −22.54 with zero RTL change**.

**The measurement tool has a zero noise floor**: swapping a module for *itself* returns 0.000 delta on every path group. **But local RTL changes have non-local effects.** Given that null control, the +1.398 ns a `domain_b`-only change produces on `clk_a` is not noise, it is ABC's global mapping moving an unrelated group. **Reporting rule adopted:** a transform's effect is the delta in the group it touches, and movement elsewhere is reported separately, never folded into the claimed benefit.

### 5.1 Setting a closure target that means something

The v1 periods were chosen as illustrative when the benchmark was 3,584 cells. At 55,413 cells an 8 ns `clk_a` target demands roughly four times what a single-cycle RV32I with async-read memory can reach in sky130, and against a target like that moving WNS from −25 ns to −24 ns is not progress toward anything.

So we measured what each domain requires and set `sdc/bench_top_v2.sdc` about 10% tighter: `clk_a` 33.29 measured to 30.0 target, `clk_b` and `clk_e` 29.49 to 26.5, with `clk_c` and `clk_d` already met and tightened to 3.0 and 8.0. Generated-clock `-edges` are relative to master edges, so they scale automatically and no edge list changed. v1 is retained unchanged as the frozen record for every earlier measurement: revising a target with disclosure is not the same as editing constraints mid-campaign, which stays forbidden. `sdc/bench_top_v3.sdc` (§7.3) later applies the same method again, to the flow that includes the buffering pass.

Under v2, and after the correction below, the baseline **meets** `clk_a` at +1.333 ns, with `clk_a_div2` at −0.543 and the two AES-bound domains at −4.957 each. **Read those against §7.2**, which shows what they become once wires exist.

### 5.2 The fix that did nothing, for eight commits

Finding 1 above is correct in substance and **was not in effect**. The exclusion list is built by scanning the liberty for cell names; the liberty writes `cell ("name")` with quotes and the regex expected it without, so it matched nothing and returned an empty flag string. Every netlist built between that "fix" and its discovery carries 203 `lpflow` cells and the 12.8 ns artifact the exclusion exists to remove. It was found by reading a critical-path report and seeing the banned cell at 12.824 ns on a path where it was supposedly forbidden. There was no test, which is why nothing else caught it.

All affected numbers were re-measured. The `clk_a` baseline carried **4.62 ns** of artifact (−25.287 → −20.667) and the four proven transforms' deltas moved 40 to 50%, but **the qualitative conclusion did not change**, so no conclusion had to be withdrawn. Note also that the exclusion is **not** uniformly beneficial: `clk_a` gains 4.62 ns while `clk_b` and `clk_e` each lose 1.97 ns, because constraining the mapper also removes options from paths using those cells benignly.

After the fix a 5.66 ns single-cell delay remained, high fanout with no buffer-insertion pass; §7.2 stops flagging that and measures it.

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
| k-padded miter | n/a | **PASSED, unbounded** |

`cec` cannot express the question; `dsec` and EQY express it and correctly answer no, because the designs are not cycle-for-cycle equivalent. None can express equivalence *modulo k cycles*, so a pipeline gated on any of them can only ever reject a latency change. Measured evidence for the routing decision, not an argument.

**We mutation-tested our own checker, and it failed.** The stream-equivalence obligation asserts only once both designs have completed a transaction. We built a mutant reproducing a real documented deadlock bug, confirmed by simulation that it never produces output, and ran the proof: **PDR reported PROVEN in 0 seconds** for a design that deadlocks, because the assert's guard was unreachable and it was vacuously true. Fixed with a `cover` property that distinguishes the real design (REACHED) from the mutant (UNREACHABLE). We found this by testing the verifier, not the design.

### 6.1 Choosing the branch: the interface classifier

A k-padded obligation is *wrong* for an elastic interface. We measured that too: pointed at a valid/ready pair with back-pressure, the k-padded miter is **refuted in 0 seconds on a design that is correct**, because under back-pressure the two designs hold different numbers of in-flight transactions and no fixed cycle offset exists. A tool that emits the wrong obligation reports a correct transform as broken.

So the branch is chosen automatically, in three passes, each able to overrule the last: **lexical** (candidate handshake ports by name), **structural** (does the candidate reach a flop's D or enable cone, since a signal that never reaches state cannot stall anything), and **formal** (prove output stability under back-pressure, so the verdict is a discharged obligation rather than a heuristic).

| module | lexical | structural | formal | verdict |
|---|---|---|---|---|
| `mac_ref` (rigid) | no candidate | n/a | n/a | RIGID |
| `mac_vr_ref` | `out_ready` | reaches `$dff.D` | PASSED | ELASTIC |
| `alias_names` (`vld`/`rdy`) | `o_rdy` | reaches `$dff.D` | PASSED | ELASTIC |
| `axi_style` (AXI prefixes) | `m_axis_tready` | reaches `$dff.D` | PASSED | ELASTIC |
| `costume_ready` | `out_ready` | **REJECTED** | **FAILED** | **RIGID** |

`costume_ready` is the case that earns the machinery: handshake-shaped port names, not an elastic interface. Both later passes reject it by *independent* arguments, the signal never reaching state and the data changing while stalled.

Two limits: pass 3 is bounded (depth 16), and exotic flow control that misses the lexical pass is classified rigid, the unsafe direction; defaulting unrecognised interfaces to elastic is not yet implemented.

### 6.2 Why simulation is not a substitute, measured on four mutants

Before the LLM experiment we measured the same question on hand-built mutants of a known-correct transform, with a correct control:

| mutant | lazy testbench | aggressive testbench | formal |
|---|---|---|---|
| `mut0_correct` (control) | PASS | PASS | **PASSED** |
| `mut1_stale_c` | **PASS** | FAIL | **FAILED** |
| `mut2_rare` | **PASS** | **PASS** | **FAILED** |
| `mut3_trunc` | FAIL | FAIL | **FAILED** |

`mut1_stale_c` is the classic pipelining bug, stage 2 adding the current operand to a product one cycle old, invisible to any testbench that holds that operand constant. `mut2_rare` survived 20,000 random vectors in both regimes and formal refuted it instantly. §7 reproduces this on a real LLM proposal rather than a hand-built mutant.

---

## 7. The GenAI engine, and the experiment we pre-registered

The model receives the OpenSTA critical-path report, the target RTL and the typed transform schema, and emits a declared transform type plus replacement source. The declaration selects the obligation; `tools/gate_proposal.py` runs five gates in order: **parse, elaborate, precondition, formal, timing.**

To measure this honestly we **pre-registered the experiment before writing any proposer code**, and git proves the ordering (`4ee45c2` precedes `7e3ab9b` precedes the results). The registration fixed N = 6, fixed the gates, and fixed the anti-tuning rule: *all six proposals committed before any gate ran, none editable afterwards, all six reported regardless of outcome.*

| | transform | declared | parse | elab | precond | **formal** | timing (clk_a) |
|---|---|---|---|---|---|---|---|
| P1 | addsub sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | −1.555 |
| P2 | shifter sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | **+0.485** |
| P3 | comparator sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | −2.102 |
| P4 | mux priority→parallel | k=0 | ✓ | ✓ | ✓ | **REFUTED** | n/a |
| P5 | pipeline cut | k=1 | ✓ | ✓ | ✓ | **REFUTED** | n/a |
| P6 | branch cmp sharing | k=0 | ✓ | ✓ | ✓ | PROVEN | −1.615 |

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

### 7.1 Batch 2, registered separately, on the AES key memory

Batch 1's registration required that any second batch be registered separately, its N added to the trial count, and both reported. We did that (`02ead73` precedes `3b17e5d` precedes every result). **Trial count: 16.**

Batch 2 targets `aes_key_mem`, which holds the worst path on `clk_b` and `clk_e` (−4.957 ns each). Because `u_aes_b` and `u_aes_e` are two instances of one module, every edit is measured twice in two clock groups: a built-in replicate.

| | transform | declared | parse | elab | precond | **formal** | clk_b | clk_e |
|---|---|---|---|---|---|---|---|---|
| A1 | mux bank split | k=0 | ✓ | ✓ | ✓ | PROVEN | +2.020 | +2.020 |
| A2 | decode duplication | k=0 | ✓ | ✓ | ✓ | **UNRESOLVED** | n/a | n/a |
| A3 | read port register | k=1 | ✓ | ✓ | ✓ | **REFUTED** | n/a | n/a |
| A4 | one-hot read select | k=0 | ✓ | ✓ | ✓ | PROVEN | **+4.925** | **+4.925** |
| A5 | reset unroll (control) | k=0 | ✓ | ✓ | ✓ | PROVEN | +0.436 | +0.436 |
| A6 | key mem parity split | k=0 | ✓ | ✓ | **REJECTED** | n/a | n/a | n/a |

**A4 takes `clk_b` from −4.957 to −0.032**, a 99.4% reduction, adding no storage. Both instances produce identical deltas, which is the replicate behaving exactly as it should.

**The precondition gate fired for the first time.** Batch 1's most useful miss was that *zero* proposals were rejected at precondition, which we reported as evidence that the layer was a type check rather than a legality check. A6 splits a 15-entry array into two 8-entry arrays, which is 16 words of storage where the design had 15. It declared k = 0, the flop count moved by +256, and G3 rejected it before any solver ran. That is the case the check exists for: a transform that silently changes state would otherwise have had a **combinational** obligation generated for it, which is the wrong obligation.

**A5 is why we registered a control.** It only unrolls a reset loop, is functionally identical, and touches nothing on the read path, yet it moves `clk_b` by +0.436 ns (and `clk_a` by exactly 0.000). So +0.436 is this module's same-module remapping floor, and A4's honest figure is **+4.489 above a change that does nothing**.

**A2 is the batch's real finding, and it is a bug in our gate.** A2 splits `key_mem` into four 32-bit arrays and is equivalent by inspection. The gate said REFUTED, one failing partition out of 573, and it looked like a second P4. Three things did not fit: simulation had gold and gate agreeing on all 16 values of `round`; EQY had proved **128 of 128** `tmp_round_key` partitions while failing the output that is a plain alias of them; and the partition's own log ends `Reached maximum number of time steps -> proof failed`, which is a **bound**, not a counterexample. EQY prints the same summary line for both, and we matched on the string. The gate now reads each failing partition's log and separates `model found` from depth exhaustion.

We checked whether the correction cascades, rather than assuming. It does not. P4's log ends `SAT temporal induction proof finished - model found for base case: FAIL!` with concrete values (`a = ae19f605`, `shamt = 7`, gold `alu_out = ff5c33ec`, the arithmetic shift), and that had already been confirmed independently by directed simulation. P5 and A3 were refuted by BMC, which reports a trace. **P4 stands.**

Two hypotheses about A2 were tested and both were wrong before the log gave the answer, and one is a trap worth passing on: clamping `round` to its reachable range *outside* the designs changed nothing, because **EQY proves each partition with its inputs as free variables**, so an external constraint never reaches the partition's cone.

We would rather report this than the version where A2 is a second headline refutation. Bugs that hide a result behind UNRESOLVED are the safe direction, and our standing rule caught two of those in this batch. A bug that turns a non-result into a confident REFUTED is the dangerous direction, and no rule caught it: what caught it was a partition failing while everything feeding it passed.

### 7.2 The second router: which lever, before which transform

Four of batch 1's six proposals were proven correct and three of those made timing *worse*. The obvious reading is that LLM RTL proposals do not help. The measured reading is more useful.

We built `tools/classify_path.py`, which scores what fraction of a path's delay comes from cells driving 32 or more loads. Batch 1's target path is **58.9% fanout-attributable**. The design-level AES path is **91.4%**, with 21.029 ns sitting in a single `nor4_1` driving **300 loads**: `aes_key_mem` is a 15 × 128-bit register array read through a combinational 15-to-1 mux. Restructuring logic does not shorten a net's load delay. The proposals were aimed at the wrong variable.

The control, registered in advance and committed before its output was read: synthesize `bench_top` twice from identical RTL under identical SDC, differing only by appending `buffer -N 16; upsize; dnsize` to the ABC script. Yosys ships that in its `-liberty -constr` script; our flow was not running it. Both violated groups close, `clk_b` moving **−4.957 to +12.600 MET**, with zero RTL change, 1,419 buffers added and an identical flop count. Equivalence checked rather than trusted: **49,923 of 49,924** obligations discharged, the residual being one top-level XOR whose input net is undriven in *both* designs.

That control has no placement and no parasitics, so we then ran the real thing. **OpenROAD** was the one organizer-named tool this project had never used, and the measurement is what finally asked for it. Full flow on the same unbuffered netlist: tech and cell LEF, floorplan at 40% utilization, `make_tracks`, `place_pins`, the platform's own `setRC.tcl`, global placement, placement-based parasitics, then `repair_design` and detailed placement.

| clock | before `repair_design` | after | delta |
|---|---|---|---|
| clk_a | −36.723 | **+17.593 MET** | **+54.316** |
| clk_b | −43.438 | **+12.367 MET** | **+55.805** |
| clk_e | −47.683 | **+19.529 MET** | **+67.212** |

**All three groups close**, at a measured cost of **+20.2% area** (448,840 to 539,351 µm², 40% to 48% utilization). Flop count is identical at 7,959 flattened on both sides, with 960 buffers added, and both runs of the flow reproduce every number exactly.

**And the closure survives a clock tree.** Those numbers use ideal clocks, which is the standard context for `repair_design` and not a signoff number, so we ran CTS and global routing on the same flow:

| point | clk_a | clk_b | clk_e | clock network |
|---|---|---|---|---|
| post-place | +17.593 | +12.367 | +19.529 | **ideal** |
| post-CTS | **+17.616** | **+8.694** | **+18.428** | **propagated** |
| post-global-route | **+17.117** | **+8.987** | **+18.647** | **propagated** |

Every group meets at every point, for 7,833 µm² (+1.45%) and 1,547 clock buffers. `clk_b` pays 3.673 ns for its tree, and the mechanism is in the same report: its launch path sits **3.514 ns** deeper than its capture path, so the imbalance and the slack loss agree to 0.16 ns. `clk_a`, at 2.463 ns of insertion but only 0.090 ns of imbalance, is essentially free. Propagation was verified rather than assumed: 6 `clock network delay (ideal)` lines before CTS, 12 `(propagated)` after, and insertion delay exactly 0.0 before. `report_clock_skew` printed empty on this build, so the imbalance figures come from the path reports and no skew number is claimed. Details and the unexplained `clk_e` capture reading are in `experiments/openroad_cts/NOTES.md`.

One thing is **not** verified, and we would rather say so than round it up. The ABC control got a 49,923-of-49,924 internal equivalence check. `repair_design` did not: three attempts failed for tooling reasons, twice because `equiv_make` matches by name and `repair_design` splits nets when it buffers them (86 equivalence points in one attempt, 1 in the other), and once because liberty-derived cells stay blackboxes in the bounded miter. **None produced a counterexample; they produced no evidence either way.** What supports the result is the structural check, the exact reproducibility, and the pass's documented contract. Closing this properly needs functional sky130 cell models, and it is listed as open work.

Now look at the *before* column. Under the same SDC, netlist and liberty, `clk_a` reads **+1.333 MET without parasitics and −36.723 with them**. **Every timing number this project published before today was a zero-parasitic number.** That does not invalidate the baseline-versus-variant comparisons, which were all made under one consistent model, but it does mean our absolute closure claims described a model without wires. This is the correction, and it makes the routing argument stronger rather than weaker: wire delay is definitionally not an RTL problem, so putting parasitics in the model *raises* the share of the violation no RTL rewrite can touch.

| lever, same group, same SDC | clk_b gain | changes RTL? | parasitics? |
|---|---|---|---|
| best LLM RTL transform, batch 1 (P2) | +0.485 | yes | no |
| best LLM RTL transform, batch 2 (A4) | +4.925 | yes | no |
| ABC buffering control | +17.557 | no | no |
| **OpenROAD `repair_design`** | **+55.805** | **no** | **yes** |

The mapping-level control pointed the right way and understated the real pass by **3.2x**, which is what a control is for.

Two results keep this from being a simple "buffering wins" story.

First, **A4 gained 4.925 ns while leaving max fanout exactly unchanged** (2193 in gold and in every proven variant), as pre-registered in H2: synthesis re-merges duplicated cones. An RTL transform *can* move a fanout-dominated path, by restructuring what sits in series with the high-fanout net rather than by fixing the net.

Second, **after buffering the remaining violations are mixed, not depth-dominated.** Re-tightening every clock period 6x on the buffered netlist puts `clk_b` at −1.689 ns and `clk_a` at −12.216 ns. We first reported these at 0.0% fanout-attributable delay and DEPTH_DOMINATED; the corrected classifier (§9) puts them at **34.4% and 42.8%**, MIXED, with a 59-load S-box input and a 387-load net respectively. The tool still separates 0.914 and 0.589 from 0.344 and 0.428, which is the weaker claim we can now make.

**The two levers are sequential, not alternative.** Buffer, re-measure, then propose RTL. `docs/path-classification.md` carries the validation table and the correction of 2026-09-03 described in §7.3 and §9: until that day the tool undercounted fanout across module boundaries, and every DEPTH verdict it gave on this benchmark's post-buffering paths was wrong.

**Does any of this transfer off our own benchmark?** We pre-registered a test on the 20 human-written designs published with Dr. RTL (ICCAD 2026), whose analyzer routes "wide fan-out" to logic restructuring by having the model read the report. Same flow, same thresholds, each design at 0.9x its own measured requirement, then the physical lever. 15 of 20 are in scope (FIFO uses async-load flops no sky130 cell implements; SPI, UART and pcie infer latches, which G2 rejects; LSTM has no registers). As first classified: **5 FANOUT_DOMINATED, 2 MIXED, 8 DEPTH_DOMINATED**, byte-identical across two executions; after the classifier correction (§9), 1 verdict changed (tv80, DEPTH to MIXED) and the split is **5 / 3 / 7**. Both groupings are in `experiments/drrtl_transfer/NOTES.md`; the corrected one is below.

| verdict | n | lever closes it alone | lever gain, median | min | max |
|---|---|---|---|---|---|
| FANOUT_DOMINATED | 5 | **5 of 5** | **3.623** | 1.542 | 17.515 |
| DEPTH_DOMINATED | 7 | 4 of 7 | 0.581 | 0.000 | 2.851 |

Three of the five registered predictions were **wrong**, including the primary one, which said the lever would help fewer than half of the DEPTH designs. It helped 6 of 8 as then classified, because `upsize; dnsize` is gate *sizing* and sizing helps any path: the lever we compared the classifier against does two things. What the classifier actually predicts on designs it has never seen is **magnitude** (6.2x median, 7.5x before the correction) and **closure** (5 of 5 against 4 of 7). The fanout finding transfers at a lower rate than on our benchmark (33%, 47% with MIXED), and one external design outdoes ours: `cpu_fsm`'s program counter drives **1,131 loads** and burns 32.954 ns in one cell. The classifier's verdict on one design, `arm_cpu2`, flips with how enable flops are legalized, and it took three dated amendments to get one run right; both are in `experiments/drrtl_transfer/` rather than smoothed away.

So we split the lever, pre-registered, into buffer-only and sizing-only on the same 15 designs. **Buffering alone does nothing for depth-dominated designs** (corrected grouping: median **0.000 ns**, worse on 3 of 7; as first classified it read −0.019, worse on 4 of 8, and the design that moved out of the group is the one buffering hurt most) and closes 4 of 5 fanout-dominated ones (median **+3.282**). That is the claim the classifier makes, measured against the component it models; prediction 4 was right about buffering and wrong about the lever it was tested with. Sizing turned out stronger and broader than registered, helping 6 of 7 depth designs and fanout designs 4x more, so 2 of those 4 predictions were wrong too. On `cpu_fsm`, buffer-only gains +18.974 against the combined lever's +11.754: sizing after buffering gave back 7.2 ns, one design, not claimed as a rule.

We then applied Dr. RTL's **high-confidence skill #7**, "duplicate register copies and split fanout cones", as written to that `cpu_fsm` path. `PC`'s fanout fell from 1,131 to 3 because the copy inherited **1,175**: the fetch mux is one cone, so the load moved and did not split. Slack got **worse** by 0.447 ns, `(* keep *)` changed nothing, and our gate rejected it as not k=0, which is partly on us: register duplication wants the sequential obligation the library has and the flop-count check prevents reaching. The physical lever gains +17.515 ns on the same design.

Their **skill #8**, "replicate a high-fanout condition wire per consumer", went onto three more of their designs. Plain replication was a no-op on 3 of 3 (ABC merged the copies back). With `(* keep *)` it split the fanout on 1 of 3 and that design got **slower** (−0.219), closed 1 of 3 by moving the worst path elsewhere (+0.998), and did nothing on the third; buffering alone beat it on all three. Four of six variants PROVEN, two unresolved at EQY's depth bound. Across both skills, **0 of 4 applications both reduced the worst path's fanout and improved timing**; the phase also found and fixed two harness defects.

### 7.3 The closed loop

`tools/slacksmith.py` runs all of the above as one command: **measure, classify, route, apply, re-measure, repeat**, stopping when every group meets, when no lever remains, or at `--max-iters`, and logging every decision with its evidence to `decisions.jsonl`.

Against SDC v2 it closes in **2 iterations and 46.7 seconds**: it measures −4.957 on `clk_b`, classifies it FANOUT_DOMINATED at 0.914 with a 21.029 ns cell driving **300 loads**, routes to the physical lever, and re-measures at +12.600 MET. It reproduces the standalone experiments' numbers exactly, and the RTL lever never fires because nothing is left for it.

To exercise both branches the target has to be one the flow cannot already clear. `sdc/bench_top_v3.sdc` applies v2's methodology to the corrected flow (~10% tighter than the measured **post-buffering** requirement, generated by `sdc/make_v3.py`), because the buffered netlist clears v2's targets by 12 to 20 ns. Under v3 the loop routes to the physical lever first. The classifier of the day then called the residual `clk_a` violation DEPTH_DOMINATED at fanout share 0.000 and routed it to RTL; that verdict was wrong (the path is **MIXED at 0.428**, a 387-load net carrying 6.762 of its 17.131 ns) and the correction is in §9. The runs below are reported as they happened.

The v3 run: 8 iterations, 449.3 s. The physical lever alone **closes `clk_b` outright** (−18.957 to +5.6); the RTL lever gates P1, P2 and P3, EQY proves all three correct, and **the loop reverts all three on G5**, each revert restoring `clk_a` to exactly −1.716.

**The ranking changes once the physical lever has been applied.** P2, the one proposal batch 1 found to improve `clk_a` (+0.485 ns), was reverted by the loop. We isolated it: one SDC, one transform, and the only difference is whether the buffering pass runs.

| context | baseline clk_a | with P2 | delta |
|---|---|---|---|
| unbuffered | 1.333 | 1.818 | **+0.485** |
| buffered | 12.784 | 12.299 | **−0.485** |

The unbuffered row reproduces batch 1 exactly; the buffered row flips the sign at the same magnitude. **Batch 1's single winner is a loser in the context the design would actually ship in.** One transform, one design, one buffering setting; the equal magnitude is reported, not claimed as a law.

**Three more registered runs, 14 predictions, after the lever split in §7.2.** Under `--lever-policy verdict` the classifier picks the component and every physical step is provisional. Buffer-only alone puts `clk_a` at **+1.75** and `clk_b` at +5.556, where the combined lever left `clk_a` at −1.716. Sizing, applied for `clk_e`, then gains 0.838 ns there and moves `clk_a` back to −1.716; the per-group G5 bar looked only at `clk_e` and **confirmed it** (P3, "at least one physical step is reverted", wrong). A second registration, written at iteration 5 of that run, measures G5 across all groups: keep a step only if the sum of negative worst slacks improves. That run reverts the sizing step and ends in **4 iterations instead of 8 with 1 group violating instead of 2** (total −1.444 against −2.322); 4 of 4 predictions held. A third run, after the classifier correction, ends in the same state for a now-true reason: `clk_e` is MIXED at 0.286, both physical components have been tried, and the loop stops with `physical_exhausted`; 5 of 5 held. **Under SDC v3 with a correct classifier the RTL lever never fires**, so runs 2 and 3 measured three proven transforms on a path the router should not have sent them to.

**Running the loop found two defects in it.** It gated proposals against a module that was not on the binding path: the violation was in the RV32I domain, the loaded proposals targeted `aes_key_mem`, EQY proved one correct, the loop applied it, and `clk_a` went **−1.716 to −2.203**. And it had no G5 bar, so it kept that transform. Both are fixed; the pre-fix log is kept.

A third defect surfaced in the gate, the mirror image of the A2 bug in §7.1: a string-match fix read P4's concrete counterexample as **UNRESOLVED**. Caught by re-running proposals with known verdicts, now the standing regression: **P4 must read REFUTED and A2 must read UNRESOLVED**.

**Honest limit on the phrase.** The proposer is offline: the loop selects from proposals frozen before any gate ran, gates and measures them, and does not generate them, because the anti-tuning rule forbids generating a proposal after seeing a gate result.

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

As frequency, which is what deliverable 5 asks for: at core level a 10 ns constraint with −9.84 ns of violation means a required period of 19.84 ns, so **F_max 50.4 MHz baseline and 55.9 MHz with P6**, an 11.0% improvement.

**The rankings invert between contexts.** By core timing the best transform is P6 (+1.96 ns); at design level P6 is the **worst** (−1.615 ns), and the only design-level winner is P2, which is nearly neutral at core level. Two real mechanisms: the core's critical path is not the design's (inside `bench_top` the binding path runs through the wrapper's async-read memory and its fanout, not the ALU cone), plus the non-local remapping quantified in §5. We report both contexts for all four transforms, because a report quoting only the core table would name P6 the best transform and one quoting only the design table would name it the worst.

Power is vector-free at default switching activity, relative between variants only; at design level it is flat at 223 to 224 mW across all variants (a 351-cell change is 0.6% of a 55K design), reported as a null rather than a 1 mW difference. The area cost that *is* resolvable is `repair_design`'s **+20.2%** (§7.2).

---

## 9. What we got wrong

Judged work should show its corrections, so here are ours, all committed with the evidence.

**Our gate manufactured a refutation.** It reported A2 as REFUTED when EQY had only run out of depth (§7.1). Every other bug below hid a real result behind an inconclusive verdict, which the rule "UNRESOLVED is never a verdict" is built to catch; this one turned a non-result into a confident claim, and no rule caught it. We found it by noticing a partition had failed while all 128 partitions feeding it had passed.

**Three of eleven registered predictions across the two batches were wrong**, 9 of 18 in the transfer study, and 1 and a half of 14 in the closed-loop runs. Batch 1 predicted a precondition rejection and got zero (batch 2 then rejected A6, so the finding is true of batch 1 only); it predicted latency semantics would dominate failures and got one of each; batch 2 predicted at most 2 of 6 improving `clk_b` and **3 did**. Every miss is on the record with its registered confidence.

**We spent most of the project optimizing a design whose violations a stock pass closes, and reporting numbers that had no wires in them.** Yosys ships `buffer; upsize` in its `-liberty -constr` ABC script, not in the plain `-liberty` script we used; it is worth 17.557 ns. And every timing number published before §7.2 was **zero-parasitic**: with placement parasitics the `clk_a` baseline reported as "+1.333 MET" is **−36.723**. Baseline-versus-variant comparisons survive, since both sides used one model; the absolute closure claims did not.

**Two harness bugs, both ours, both surfaced as UNRESOLVED.** A3 reported UNRESOLVED twice before producing a verdict: `sby` was not on PATH, then our generalization patch wrote `{max(k,1)}` into the generated miter as literal Verilog. Fixed and re-run, A3 is REFUTED. UNRESOLVED twice meant "the harness broke", and a report that left A3 there would have hidden two of its own bugs behind something that looks like a result.

**The loop's acceptance bar confirmed a step that traded a met group for 0.838 ns on another** (§7.3). The run that exposed it is kept, the fix was registered mid-run and dated, and the registration it corrects had named the wrong clock in a prediction.

**The path classifier undercounted fanout across module boundaries, and we had written down the tell and shipped it anyway.** Its docstring named "a 6.762 ns delay on a cell at fanout 1" as the signature of this bug, and that number sat in every v3 closed-loop log under a DEPTH_DOMINATED verdict. Read against the OpenSTA report, the cell drives **387** loads, and a 1.952 ns cell recorded at fanout 0 drives **59**: whole-bus and concatenated port connections were charged nothing. Every DEPTH verdict in runs 2 to 4 is MIXED; 1 of 15 external verdicts changed; the fix reads OpenSTA's own fanout column and is regression-checked on 5 fixtures with 0 disagreements at or above fanout 32. The wrong logs are kept. This is the largest correction in the project, and the tool's own output carried it.

**A claim that was false, caught by simulation.** We described `pipeline_cut_rigid(domain_a)` as boundary-proven *and therefore* module-equivalent. It is not: `mac_result` diverges permanently (`002a` vs `0031`) because the consuming domain samples at half rate, so a one-cycle delay selects a different subsequence. The proof stands for the property it states; the sufficiency claim was withdrawn and the refuting testbench committed.

**Two more, briefly.** P2's improvement first measured **+5.105 ns** against a baseline from a slightly different flow; rebuilt identically it is **+0.485 ns**. And the real divider hit a Yosys limitation (`clk2fflogic` makes BMC intractable past depth 28), so **PDR is the correct tool for those properties**, not a workaround.

---

## 10. Demo, reproduction, limits

The demo video walks the pipeline end to end on the real benchmark: a timing report, a typed transform, its generated obligation, the prover portfolio, and a refutation with its counterexample, the case every simulation-gated tool would have passed.

Everything reproduces from the repository: each experiment directory holds its sources, its `.sby` or `.eqy` configuration and its raw logs; proofs re-run with `sby -f <config> pdr` or `python3 tools/run_proof.py`. Cold-clone reproduction was verified by running each experiment directory alone in a scratch tree.

**Limits we would rather state than be asked.** N = 12 proposals across two batches, two target modules, one proposer model: outcomes, not rates. The physical flow reaches CTS and global routing, not signoff, and `repair_design`'s equivalence is unverified after four attempts. The classifier's thresholds were chosen on our benchmark, it has given no DEPTH verdict on it since the correction, and one external verdict is flow-sensitive. The proposer in the closed loop is offline by design, and the best run leaves `clk_e` at −1.444 with no lever left. Of the seven transforms formally proven correct across both batches, three made their own path group worse and all three tried after buffering were reverted: **proof and profit are independent questions, and we measured both.**
