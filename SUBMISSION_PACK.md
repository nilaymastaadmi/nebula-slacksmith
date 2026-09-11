# SlackSmith: submission pack, state as of 2026-09-11

Nebula (Astera Labs @ BITS Pilani Goa), Track A: *Constraint Optimization
through RTL Enhancement Using Generative AI*.
Nilay Toshniwal and Shivani Chaudhary.

Repository `github.com/nilaymastaadmi/nebula-slacksmith`, branch `sandbox`.
This file is a factual inventory for review. **Every claim below names the file
that carries its evidence**, and nothing here is a summary of something that
does not exist in the repository.

**Submission format required:** 10 to 12 page report covering all deliverables,
plus a demo video.
**Stated judging criteria:** coverage of all deliverables, innovation, thought
process.

---

## 0. Hard status, stated first

| item | state |
|---|---|
| `REPORT.md` | **A4, 15 mm margins, 9.5 pt body at 1.22 leading, 8 pt tables. Measured in a browser, never estimated.** Re-measure after every edit and quote no number from any document, this one included: the figure moved 12.34 -> 15.60 -> under-cap across one day. Compression did 15.6 -> ~12.7 with **no measured result dropped**, removing duplication rather than evidence; margins and leading did the rest, and every setting is disclosed in a footer on the report itself|
| Demo video | **does not exist.** `DEMO.md` is the 9-beat shot list and `demo/SCRIPT.md` the verbatim narration; `tools/demo_check.sh` runs every command in both and reports **15 pass, 0 fail**, measured 2026-09-11 |
| Repository | runs from a clean clone at any path, verified three times (`experiments/reproducibility/`) |
| Interactive demo | `demo/explorer.html`, generated from committed logs, published |
| `claude` CLI auth | **working.** Token minted 2026-09-11 and held outside the repository in `~/.slacksmith_token`; `tools/preflight.sh` fails if a credential-shaped string ever reaches a tracked file |
| Last push | branch `sandbox`, working tree clean |

---

## 1. Deliverable coverage

### D1. RTL timing analysis framework
- `tools/remeasure.py` (synthesis + OpenSTA), `tools/slacksmith.py` (the loop),
  `sdc/bench_top_v3.sdc` (frozen constraints).
- Reports worst slack per clock group, per-group path reports, cell-level
  incremental delay and fanout.
- **G0, constraint integrity:** the SDC is SHA-256 fingerprinted and its timing
  exceptions are counted before any number is trusted (`sdc_fingerprint()`).
  Motivated by a measured result: one `set_multicycle_path` line moves `clk_e`
  from −0.319 VIOLATED to +4.860 MET on a **byte-identical 26,958-cell
  netlist** (`experiments/sdc_integrity/`, +5.179 ns).

### D2. GenAI-based RTL optimization engine
- `tools/proposer.py`, three backends: `frozen` (committed proposals),
  `handoff` (generates against live state, loop halts for the model),
  `cli` (automated via `claude -p`, **exercised 2026-09-11, N = 1**, run preserved at `experiments/cli_backend/results/run1/`).
- `tools/gate_proposal.py` routes the proof obligation from the declared
  transform type.
- Proposals: 12 frozen across two pre-registered batches
  (`experiments/llm_proposer/`, `experiments/llm_proposer_aes/`), 2 generated
  online by handoff (`experiments/online_proposer/`), 2 generated to close the
  missing transform classes (`experiments/missing_classes/`), and **1 generated
  with no human in the loop** (`experiments/cli_backend/`). **17 total, of which 15 are model-written**: the remaining 2, the retiming and the FSM re-encoding in `experiments/missing_classes/`, were written through the `handoff` backend by the session driving this project and are marked as such in REPORT §3. A blind proposer has never produced a retiming or an FSM re-encoding, because until 2026-09-11 the gate rejected both by construction.
- Handoff result: O1 PROVEN and kept (`clk_e` −25.957 → −24.079), O2 **PROVEN
  and 11.434 ns worse**, reverted at G5.
- **Unforced routing:** on `i2c_master_top` (Dr. RTL set, 560 cells,
  depth-dominated) the classifier selects the **RTL lever with no override**,
  and the `cli` backend returns usable proposals on a design it has never seen.
  Run twice it returned *different* transforms; the second is **PROVEN by EQY**.
- **Unattended result (N = 1):** `fanout_replication_round_key_update`, PROVEN
  by EQY over all outputs, **+1.414 ns `clk_b`, +1.414 `clk_e`, +1.967 `clk_a`**,
  no group paying for it. 456 s end to end. It is the only batch-3 transform
  that improved every group.

### D3. Critical path and timing violation analysis
- `tools/classify_path.py` scores what share of a path's delay comes from cells
  driving ≥32 loads, and routes the fix accordingly.
- Binding paths measured 58.9% to 98.95% fanout-attributable. Worst single
  cell: a `nor4_1` at **300 loads** carrying 21.029 of a 30.602 ns path.
- Regression-checked against OpenSTA's own fanout column on 5 fixtures
  (`tools/classify_regression.py`).

### D4. Optimized RTL implementation
- `rtl/rv32i_core_P{1,2,3,6}.v`, plus AES key-memory variants and the online
  variants under `experiments/online_proposer/results/variants/`.
- 7 of 12 frozen proposals reached PROVEN; **3 of those made their own path
  group worse**.

### D5. Timing, frequency and PPA comparison
- `experiments/ppa/`, REPORT §8.
- Physical results with placement parasitics: all three groups close,
  `clk_a` −36.723 → **+17.593**, `clk_b` −43.438 → **+12.367**,
  `clk_e` −47.683 → **+19.529**, at **+20.2% area**.
- Closure survives CTS and global routing (`experiments/openroad_cts/`),
  7,833 µm² (+1.45%), 1,547 clock buffers.

### D6. Formal equivalence verification report
- **Five** obligation branches, all exercised on benchmark RTL: combinational
  (EQY), k-padded miter (SymbiYosys BMC+PDR), stream equivalence, mapped-state,
  and **retiming** (sequential miter, no flop correspondence). Branches 4 and 5
  were added 2026-09-11 after `experiments/missing_classes/` measured that the
  router could not express either, which is why the engine had never proposed an
  FSM re-encoding or a retiming.
- **G6**, physical equivalence: `repair_design`'s output proven equivalent to
  its input, 5,832 compare points, 38 s, on all six arms.
- **G7**, CDC: synchronizer depth (structural) and Hamming safety (temporal,
  SymbiYosys). `experiments/cdc_gate/`, `experiments/g7_in_loop/`.
- **SlackBench** (`experiments/slackbench/`): 8 sealed cases that grade the
  *checker*, ground truth committed before any checker ran. Confusion matrix,
  never one number. The authors' own checker is scored and is wrong twice under
  one discharge strategy.

### D7. Interactive demo showcasing the RTL optimization workflow
- `demo/explorer.html`, generated by `demo/build.py` from the committed logs so
  it cannot drift. Four tabs: the loop (five runs, steppable, each decision with
  the evidence it used), the gate (six proposals, counterexamples), the exam
  (SlackBench matrix), the cheat (the SDC result).
- `demo_check.sh` fails if the committed page differs from a rebuild.

---

## 2. Objectives coverage

| objective | where | note |
|---|---|---|
| Analyze RTL against specified timing constraints | D1 | SDC frozen and fingerprinted |
| Identify critical paths and timing violations | D3 | with fanout attribution |
| GenAI recommends optimizations: **pipelining** | `pipeline_cut_rigid` (P5), k>0 rigid branch | refuted at G4, reported |
| ... **logic restructuring** | operator sharing (P1,P2,P3,P6), `mux_priority_to_parallel` (P4), `array_write_decode_split` (O1), `array_read_mux_two_level` (O2) | the bulk of the proposals |
| ... **retiming** | `retime_write_decode_forward` (O1), obligation branch 5 | **The gate could not express a retiming until 2026-09-11.** G3 required `k=0 -> flop delta 0`, and a retiming is k=0 with the flop count changed. Root-caused and fixed in `experiments/missing_classes/`; O1 is **PROVEN** (unbounded, PDR) and **costs 4.616 ns** on its own group, a registered prediction that held. `dretime` also exists as an ABC mapping pass, which is not the same thing |
| ... **FSM optimization** | `experiments/fsm_reencode/` (hand-built), and `fsm_output_coded_state_assignment` (O2) through the gate | Branch 4 was **advertised to the proposer and not implemented**: any re-encoding changes the flop count, so G3 rejected it before the declared branch was read. The project's own one-hot returns `FAIL(declared k=0 but flop count changed by +12)` through the unmodified gate and `PROVEN` through the fixed one. O2 is **PROVEN** (unbounded, PDR) and buys **+3.185 ns**, the largest RTL gain on this group in the project |
| Evaluate timing, area, performance | D5 | area measured, +20.2% and +1.45% |
| Formally verify equivalence | D6 | five branches plus G6 and G7 |

### Benchmark specification

| required | built | evidence |
|---|---|---|
| 5 independent master async clock domains | **5** (`clk_a`..`clk_e`) | `sdc/bench_top_v3.sdc`, 5 `create_clock` |
| ≥1 generated clock per master | **5**, one each | 5 `create_generated_clock` |
| Clock Domain Crossings | gray-pointer async FIFOs on every multi-bit crossing, two-flop synchronizers on every single-bit one | `rtl/async_fifo.v`, `rtl/sync2ff.v`; G7 finds 8 real crossings in `bench_top` |
| Clock divider logic, multiple ratios | **/2, /3, /4, /5** | `rtl/clkdiv.v`, `rtl/bench_top.v` |
| ~50K standard cells | **55,413** as REPORT §4 reports it; **48,616** on the fixture this row measures | see the note below |

**Why two cell counts, and which is which.** `REPORT.md` §4, `README.md` and
`docs/measurement-methodology.md` all say **55,413**: that is the v2 benchmark,
hierarchical, before the physical lever runs. `tools/bench_size.py` and
`DEMO.md` say **48,616**: that is `v3_bufsize_it3`, the *flattened*
buffered-and-sized netlist the later experiments use. A buffered netlist being
smaller than the unbuffered one looks like an error and is not: flattening
collapses redundant decode logic across the hierarchy boundary (REPORT §7.3),
and that saves more cells than the buffering adds. Both are ~50K and both are
correct for the fixture named beside them. The count is cross-checked against a
fresh Yosys `flatten` on each.

### Tools

Verilog ✓ · OpenSTA ✓ · Yosys ✓ · OpenROAD ✓ (floorplan, placement,
parasitics, `repair_design`, CTS, global route) · SymbiYosys ✓ · EQY ✓ ·
Python ✓ · LLM/GenAI ✓ (Claude Opus 5, disclosed in every registration).

---

## 3. What is claimed as innovative

Each with its nearest prior art, conceded where it narrows the claim.

1. **Two routers, not one.** The proof obligation is routed from the *declared
   transform type*; the fix is routed from *measured path pathology*. Nearest
   prior art: ROVER (TCAD 2024) is structurally the same propose-then-gate
   shape with search in place of a model; EquivFusion already derives the
   obligation from a declared scope, two types against our five. **Conceded:
   the taxonomy is finer, and that is the whole difference.**
2. **SlackBench: a benchmark that grades the checker, not the design.** A
   literature search found nothing equivalent. Ground truth sealed before any
   checker ran, scored as a confusion matrix, `CANNOT` first-class, and the
   authors' own checker included and failing twice.
3. **G0, constraint integrity as a gate.** No equivalence checker can catch a
   constraint edit, because the two designs are the same file. Measured at
   +5.179 ns on a byte-identical netlist. Written up in REPORT §5.3.
   **`experiments/sdc_integrity/` is exploratory and not pre-registered**, and
   says so in its own notes. It demonstrates a mechanism; it does not carry the
   pre-registration evidence §4 below describes, and should not be counted
   among the 17.
4. **G7, CDC as a formal property rather than a lint.** Hamming safety checks
   that the value crossing a boundary changes at most one bit per cycle, so it
   checks the *property* and not the encoding. Detects both SlackBench CDC
   cases, which every functional checker in the suite gets wrong or cannot
   express.
5. **Equal power-up state, and the check that it is not too strong.** A miter
   that gives two copies of one chip *independent* arbitrary initial state asks
   whether they agree from any **pair** of starting states, which no correct
   transform satisfies. Fixing that turned two partial proofs into unbounded
   ones over the full interface. The result only counts because a transform
   **known to be broken still fails** under the same assumption, a void
   condition registered before the assumption was written. Found by an external
   reviewer, not by us; three of our own written explanations preceded it and
   all three blamed the design rather than the tool.
6. **A null control on the verification side.** Before any refutation is
   reported the gate re-runs the same miter with the gate replaced by the gold;
   if that also fails it reports `CANNOT` rather than `REFUTED`, and where only
   some outputs are undecidable it names them and decides the rest. Built
   because the miter was found **refuting `aes_key_mem` against itself**. REPORT
   §5 has had the equivalent control on the timing side since the start; the
   proof side had none.
7. **Published negative results as primary output.** Registered predictions are
   scored including the misses, and the misses are in the report. On 2026-09-11
   alone, 4 of 13 registered predictions missed and 3 of those 4 found a defect.

---

## 4. Thought process: what is on the record

- **17 pre-registrations** across 15 experiment directories, each committed
  before the code or the results they govern, with git as the ordering proof.
- **Dated amendments**, never silent edits. Where ground truth was wrong on
  publication (SlackBench CDC-1) it is disclosed as an amendment rather than
  corrected quietly.
- **Scored predictions including failures.** Examples: the max-fanout
  constraint was predicted to close the last group and made it worse; G7's C4
  predicted zero depth violations and got six; the online proposer's O2 and O6
  both missed.
- **§9 of the report is a list of the project's own errors**, including a
  classifier that undercounted fanout and invalidated every DEPTH verdict, and
  a gate that manufactured a refutation.
- **Reproducibility verified by running**, not asserted: clean clone at a
  different path, 15 of 15 (`experiments/reproducibility/`).

---

## 5. Known-open items

1. **`REPORT.md` fits at 9.5 pt, not at 10.5 pt.** Measured, not estimated. Compression took it from 15.6 to 14.0 pages with no measured result dropped; type size took it the rest of the way, and the setting is stated in a footer on the report itself. A judge who expects 11 pt will find this the densest entry in the pile.
2. **The demo video does not exist.** Shot list and verification script do.
3. **The unattended backend is N = 1.** One run, one design, one sample
   (`experiments/cli_backend/`). Everything else in this project that says
   "closed loop" means a model in the loop with a human-mediated handoff.
4. **The router never selects the RTL lever on THIS benchmark**, because its
   binding paths are 59 to 91 percent fanout-attributable and the physical
   lever is the correct answer to them. Every in-loop RTL result here used
   `--force-lever rtl`, logged as `lever_forced`. **It does select RTL unforced
   on a depth-dominated external design** (`experiments/unforced/`, `i2c` from
   the Dr. RTL set). That run also exposed **six defects in this project's own
   tooling**, none affecting a published result and none of which this
   benchmark could structurally have shown; two of them were reporting a
   proposal EQY proves as a harness error. Both readings are in REPORT §7.2.
5. **Equivalence is proven for `repair_design`'s pairs but not for the ABC
   buffering lever**, where the method times out.
6. **G7 fires only on modules with clock crossings**, and skips every module
   the current proposals target.
7. **Small N throughout.** 12 frozen proposals, 2 online, 8 benchmark cases,
   20 external designs of which 15 in scope. Outcomes, not rates.

---

## 6. How to verify any of this

    git clone https://github.com/nilaymastaadmi/nebula-slacksmith
    cd nebula-slacksmith
    bash tools/preflight.sh      # names any missing dependency
    bash tools/demo_check.sh     # 15 assertions across the claims above

`SETUP.md` lists the tool versions the results were measured with, and states
which claims re-derive in minutes and which cost an afternoon of synthesis.
