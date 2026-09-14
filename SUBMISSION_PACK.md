# SlackSmith: submission pack, state as of 2026-09-14

Nebula (Astera Labs @ BITS Pilani Goa), Track A: *Constraint Optimization
through RTL Enhancement Using Generative AI*.
Nilay Toshniwal and Shivani Chaudhary.

Repository `github.com/nilaymastaadmi/nebula-slacksmith`, branch `main`.
This file is a factual inventory for the judges. **Every claim below names the file
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
| Demo video | **done: 298.500 s, narrated**, measured by `ffprobe` on 2026-09-14 (H.264 video and AAC audio, both 298.500 s). A synthetic Sarvam voice (`bulbul:v3`, 12 calls) under the locked picture, whose video stream is byte-identical to the signed-off silent cut (`demo/PHASE2_VOICE.md`). The file is committed at the repository root as `slacksmith_demo.mp4`, byte-identical to the assembled cut (SHA-256 checked). `DEMO.md` is the 9-beat shot list and `demo/SCRIPT.md` the verbatim narration; `tools/demo_check.sh` runs every command in `DEMO.md` and reports **23 pass, 0 fail**, measured 2026-09-14. It held 15 and skipped beat 5 until 13 Sept; the 23rd, added on 14 Sept, checks the parameter guard on an included header |
| Repository | runs from a clean clone at any path, verified three times (`experiments/reproducibility/`) |
| Interactive demo | `demo/explorer.html`, generated from committed logs, published |
| `claude` CLI auth | **working.** Token minted 2026-09-11 and held outside the repository in `~/.slacksmith_token`; `tools/preflight.sh` fails if a credential-shaped string ever reaches a tracked file |
| Repository | **pushed**, `origin/main`. **Commit history was rewritten on 2026-09-14** to normalise the author identity and commit-message wording and to remove internal working notes: every commit hash changed, and every commit date, order and file change outside those notes did not. Hashes cited in this repository were remapped in the same pass. **The demo video predates the rewrite**: beat 4's screen shows `4ee45c22` for the pre-registration and `7e3ab9b4` for the proposals, which are now `04fa59c4` and `115fc03f`, with the same dates and the same order. This row deliberately names **no commit hash**: a commit cannot contain its own hash, so any hash typed here is stale the moment it is committed, and a stale hash is the exact failure this project argues against. Verify instead with `git fetch && git rev-list --count origin/main..HEAD` (expect **0**) and `git log --oneline -1`. Until 2026-09-12 the remote was 109 commits behind, which is why this row points at a command rather than at the tree. **Verified on 2026-09-12 by cloning the remote URL to a second path** and running `tools/preflight.sh` and `tools/demo_check.sh` from that clone: all dependencies present, no credential-shaped string tracked, **15 pass, 0 fail**, concurrently with the same check in the working tree. **Verified again on 2026-09-13**, from a fresh clone of the remote: preflight clean, **22 pass, 0 fail**, 259 numbers with 0 unsupported, tally self-test 13 of 13. The first clone run that day **failed 21 of 22**: nine committed proposal files pointed into the author's scratch directory, so the new parameter-guard fixture could not be re-gated from a clone. The gate now falls back to the committed copy beside each proposal; re-cloned and re-run. **Verified a third time on 2026-09-14**, from a fresh clone of the commit that carries the narrated video's handoff and `experiments/open_weight_3/`: preflight clean, **23 pass, 0 fail**, 273 numbers with 0 unsupported, tally self-test 18 of 18. The only later commit is this sentence |

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
  with no human in the loop** (`experiments/cli_backend/`). **17 total in three provenance tiers**: **12 frozen** (written against a timing report, committed before any check
  ran), **4 handoff** (written by a model *through the session driving this project*, so carrying its context:
  `online_proposer` O1 and O2 and `missing_classes` O1 and O2), and **1 unattended** (`claude -p`, no human, no
  context beyond the prompt). A blind proposer has never produced a retiming or an FSM re-encoding, because until
  2026-09-11 the gate rejected both by construction.
- Handoff result: O1 PROVEN and kept (`clk_e` −25.957 → −24.079), O2 **PROVEN
  and 11.434 ns worse**, reverted at G5.
- **Unforced routing:** on `i2c_master_top` (Dr. RTL set, 560 cells,
  depth-dominated) the classifier selects the **RTL lever with no override**,
  and the `cli` backend returns usable proposals on a design it has never seen.
  Run twice it returned *different* transforms. (A "PROVEN by EQY, by hand"
  verdict on the second was withdrawn 2026-09-12: no artifact survives.
  `experiments/depth_i2c/` replaces it with three kept unattended runs.)
- **Unforced, end to end, on external IP** (`experiments/depth_i2c/`, 2026-09-12,
  registered first): 3 of 3 unattended runs on `i2c_master_top` routed RTL with
  no flag; run 2 **proposed, proved (EQY), applied, re-measured and reverted** a
  `(* parallel_case *)` transform that synthesizes to a **byte-identical**
  netlist, 0.000 ns at every level; run 3 drew the same transform; run 1's FSM
  re-encoding was reported UNRESOLVED and refused; **corrected 2026-09-13**, it was never gated (a gate defect built the miter on the RV32I interface), and re-gated correctly it is REFUTED, uncorroborated (`experiments/invariant_obligation/`). Two harness defects that
  stood between PROVEN and applied were predicted in writing from run 1 and
  confirmed by run 2 before being repaired. A do-nothing control on this
  560-cell design moves unbuffered slack by 0.424 ns, so the depth-side
  survival cell stays **empty**, and the pack says so.
- **Unattended result (N = 1):** `fanout_replication_round_key_update`, PROVEN
  by EQY over all outputs, **+1.414 ns `clk_b`, +1.414 `clk_e`, +1.967 `clk_a`**,
  no group paying for it. 456 s end to end. It is the only batch-3 transform
  that improved every group.

### D3. Critical path and timing violation analysis
- `tools/classify_path.py` scores what share of a path's delay comes from cells
  driving ≥32 loads, and routes the fix accordingly.
- Binding paths measured **58.9%** (batch 1's target) and **91.4%** (the
  design-level AES path), the range REPORT §1 quotes; after the online
  proposer's O1 the same path scored 98.95% (`experiments/online_proposer/NOTES.md`). Worst single
  cell: a `nor4_1` at **300 loads** carrying 21.029 of a 30.602 ns path.
- Regression-checked against OpenSTA's own fanout column on 5 fixtures
  (`tools/classify_regression.py`).

### D4. Optimized RTL implementation
- **One composed optimized RTL:** `experiments/composed_rtl/aes_key_mem_composed.v`,
  A4 + O2 + O1 merged three-way against the gold file by `compose.sh`
  (rebuild-checked), **PROVEN** on branch 4 by PDR under the zero-init assumption.
  `clk_b`: **+5.165 ns** zero-parasitic (54.2% of the sum of its parts),
  **0.000** after the ABC buffering lever, **−0.237 against a 0.24 ns perturbation
  floor** after `repair_design` (N = 5 netlists, gold deterministic to every
  digit). No timing benefit survives the physical lever on the paths the
  classifier had already routed to it. REPORT §7.8, `experiments/composed_rtl/NOTES.md`.
- Single variants: `rtl/rv32i_core_P{1,2,3,6}.v`, the AES key-memory variants and
  the online variants under `experiments/online_proposer/results/variants/`.
  7 of 12 frozen proposals reached PROVEN; **3 of those made their own path
  group worse**.

### D5. Timing, frequency and PPA comparison
- **One label to expect a question about.** `experiments/ppa/fmax/results/table.md`
  prints the after-repair `clk_b` row's capture clock as `clk_b`; its **79.500 ns**
  period is `clk_b_div3`'s, the clock REPORT §8 names. The number is right and
  the label is the group name. The file is generated and is not hand-edited;
  it is on screen in the video's beat 5.
- `experiments/ppa/`, REPORT §8.
- Physical results with placement parasitics: all three groups close,
  `clk_a` −36.723 → **+17.593**, `clk_b` −43.438 → **+12.367**,
  `clk_e` −47.683 → **+19.529**, at **+20.2% area**.
- Closure survives CTS and global routing (`experiments/openroad_cts/`),
  7,833 µm² (+1.45%), 1,547 clock buffers.
- **Total power 94.5 mW → 139.0 mW, +47.1%** (`experiments/ppa/power/`),
  vector-free at default activity, one model for both netlists, not a signoff
  number.
- **That +20.2% is one point on a curve, measured 2026-09-12**
  (`experiments/closure_cost/`, registered before running, SDC v3 on the same
  placed netlist, so its slacks are not the v2 numbers above). Three repair
  arms: `repair_timing -setup` alone reaches a **worst group of −0.947 ns at
  +6.90% area and 0.313 W** but meets no group outright; `repair_design`
  (the published flow) **−1.471 at +20.17% and 0.408 W**, meeting two;
  the two in sequence **−0.777 at +21.26% and 0.414 W**, also meeting two.
  **No arm meets all three**, and on worst-group slack the published flow is
  last of the three.
- **Zero-parasitic, the loop's own ABC lever is not its best half**:
  `buffer -N 16` alone meets **2 of 3** groups where `buffer; upsize; dnsize`
  (the default `--lever-policy blunt`) meets **1 of 3**, the sizing pass
  trading a met `clk_a` for 3.6% area. `upsize; dnsize` alone meets `clk_b`
  for **+1.39% area and +1.4% power** with no cell added. Registered
  predictions R64 to R69 and R83: four confirmed, three missed.

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
   +5.179 ns on a byte-identical netlist. Written up in REPORT §5.2.
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
   condition registered before the assumption was written. Three of our own
   written explanations preceded the fix and all three blamed the design rather
   than the tool.
6. **A null control on the verification side.** Before any refutation is
   reported the gate re-runs the same miter with the gate replaced by the gold;
   if that also fails it reports `CANNOT` rather than `REFUTED`, and where only
   some outputs are undecidable it names them and decides the rest. Built
   because the miter was found **refuting `aes_key_mem` against itself**. REPORT
   §5 has had the equivalent control on the timing side since the start; the
   proof side had none.
7. **Published negative results as primary output.** Registered predictions are
   scored including the misses, and the misses are in the report. On 2026-09-11
   alone, registered predictions missed repeatedly and several of the misses
   found a defect. **Counts are generated by `tools/tally_predictions.py`**,
   never written by hand: the figure that used to sit here was correct when
   written and stale six hours later.

---

## 4. Thought process: what is on the record

- **29 registration files** across 24 experiment directories (`find experiments -name 'PREREGISTRATION*.md'`), each committed
  before the code or the results they govern, with git as the ordering proof.
- **Dated amendments**, never silent edits. Where ground truth was wrong on
  publication (SlackBench CDC-1) it is disclosed as an amendment rather than
  corrected quietly.
- **Scored predictions including failures.** Examples: the max-fanout
  constraint was predicted to close the last group and made it worse; G7's C4
  predicted zero depth violations and got six; the online proposer's O2 and O6
  both missed.
- **§9 of the report is a list of the project's own errors**, including a
  classifier that undercounted fanout and invalidated every DEPTH verdict (its
  giveaway, a 6.762 ns cell at fanout 1, sat in the logs for **two days**: 51.5 h
  from its first commit, `ed0d912` at 2026-08-31 23:26, to the fix, `dbb3240`
  at 2026-09-03 02:56), and
  a gate that manufactured a refutation.
- **Reproducibility verified by running**, not asserted: clean clone at a
  different path, 15 of 15 (`experiments/reproducibility/`); `demo_check.sh`
  re-run 2026-09-12 from WSL, **15 pass, 0 fail**; **22 pass, 0
  fail** on 2026-09-13 after beat 5 and the parameter guard were added; **23 pass, 0 fail** on 2026-09-14 with the included-header guard fixture.
- **The tally is generated**: `tools/tally_predictions.py`, quoted in REPORT
  §9 and re-run after every registration. **It was itself wrong until
  2026-09-13** (every id mention counted); it now self-tests on 16 real lines, including every one that broke it (until 14 Sept it also missed the word CORRECT, which left H1 and H2 unscored), and reads 35 missed of 107 decided, 136 registered, 8 unscored. **It reads lettered ids only**, which appear in 15 of the 24 registered experiments; the other nine, SlackBench, the transfer study and batch 1 among them, are outside those counts. REPORT §9 carried a stale hand-written
  tally until 12 Sept.

---

## 5. Known-open items

1. **`REPORT.md` fits at 9.5 pt, not at 10.5 pt.** Measured, not estimated. Compression took it from 15.6 to 14.0 pages with no measured result dropped; type size took it the rest of the way, and the setting is stated in a footer on the report itself. A judge who expects 11 pt will find this the densest entry in the pile.
2. **The demo video's narration is a synthetic voice**, Sarvam `bulbul:v3`, not a recorded person; three beats were re-synthesised at pace 1.08 to 1.13 to fit their screens (`demo/PHASE2_VOICE.md`). The video is 298.500 s, 1.5 s inside the 5-minute cap.
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
8. **The demo narration was over the 5-minute window until 2026-09-12.**
   `demo/SCRIPT.md` said 690 words and held 983 (6.6 minutes at 150 wpm); the
   count had been written once. It is now measured by `tools/script_words.py`,
   which fails above 750, and the narration was cut to fit with every number
   and every retraction kept.
9. **One prediction registration this project wrote was flawed** (composed_rtl
   amendment 2, R50: the perturbation spread included the netlist under test).
   Scored as written, flaw disclosed beside the score.
10. **Gate defect 3: a parameterised module is proven at its header defaults.**
    Every obligation branch elaborates the module on its own, at its header
    defaults, so a module the design instantiates with a `#(` override was proven
    about a different circuit, the one gate defect whose failure is a false PROVEN.
    **The gate now refuses it**: `CANNOT (parameter override at instantiation)`,
    checked inside `demo_check.sh` by `tools/param_guard_regression.sh`
    (`tv80_mcode` reads CANNOT; `rv32i_core` and `aes_key_mem` declare no
    parameters and are untouched, so no benchmark verdict changes). **The repair,
    threading instantiated parameters into every branch, is not done**: until it
    is, parameterised external IP gets CANNOT rather than a proof. Since 14 Sept a
    parameter that arrives through an `` `include `` inside the module
    body is refused too (`tools/fixtures/param_include/`). **Still missed**, each a
    false-PROVEN path on external IP: an override set by the synthesis script
    (`chparam`, `read_verilog -D`), a parent outside the target's directory and its
    parent, and an instantiation or `defparam` that does not open its line.
11. **The loop's default lever is not its best half.** `--lever-policy blunt`
    applies `buffer; upsize; dnsize` as one step; zero-parasitic, `buffer` alone
    meets 2 of 3 groups where the pair meets 1 of 3 (`experiments/closure_cost/`).
    `--lever-policy verdict` exists and `run_v3_fixed` uses it. **The default is
    unchanged before submission**, and `DEMO.md` beat 2 runs it.
12. **The loop's wall clock is about two minutes, not the 46.7 s first
    published.** Five protocol runs: median 112.7 s, 83.9 to 152.7 s, CPU time equal to wall
    time (`experiments/loop_runtime/`). 46.7 s was one run of a program 29 commits
    older and is below the whole range. Outside the protocol the same command
    measured 93.88, 367.8 and 832.8 s (`demo/PHASE1_CUT.md` finding 1,
    `demo/takes/beat2_timing.txt`), so the report quotes the median, not the
    range, as the loop's cost.
13. **The organisers' open-source-key recommendation is not met for the primary
    result**, which was produced with Claude Opus 5 (§5d). **A hosted open-weight
    run is still to do.** The one attempt, Gemma 4 31B on a free OpenRouter pool on
    2026-09-14, was rate-limited on all three tries and is VOID, with no reply
    (`experiments/open_weight_3/`, arm A). The local replay with the whole request
    in context (arm B) saw all 5,113 tokens and replied in 3,025 s, past the loop's
    fixed 1,800 s wait, so it is VOID too; its reply is committed and was not gated.

---

## 5b. Completed and pending, stated plainly

| deliverable | state |
|---|---|
| D1 timing analysis framework | **complete** |
| D2 GenAI optimization engine | **partial.** All four named classes are proposed and routed; 17 proposals in three provenance tiers, one unattended end-to-end run. **No run has both chosen RTL unforced and produced a proven, timing-positive transform, after 17 proposals and three designs**, and the engine has never proposed a pipeline cut that proved. The router chooses RTL unforced on `i2c`; that run's proposal was reported `UNRESOLVED`, which was almost certainly the same gate defect found on 13 Sept (same module, same branch, same code path; its artifacts were not kept, so this is inferred, not measured). The `i2c` proposal REPORT §7.2 once called "PROVEN by EQY, by hand" has **no artifact** (the run script wiped its scratch) and is withdrawn; `experiments/depth_i2c/` re-runs the design three times unattended with everything kept |
| D3 critical path analysis | **complete** |
| D4 optimized RTL | **partial**: one composed optimized RTL ships (`experiments/composed_rtl/`), proven; measured before wires, after the ABC lever and after `repair_design`. Its timing contribution after the physical flow is inside the flow's perturbation floor, and design-level closure comes from `repair_design`, not from RTL |
| D5 timing, frequency, PPA | **complete.** Before/after for all three, including power at **+47.1%**, measured 2026-09-12 |
| D6 formal equivalence | **complete.** Five branches, null control, void check. Open: the ABC buffering lever is unproven, and P5's control does not close |
| D7 interactive demo | **complete.** `demo/explorer.html`, rebuild-checked |
| **Demo video** | **complete.** 298.500 s with Sarvam narration under the locked picture (`demo/PHASE2_VOICE.md`) |

**Pending, in priority order:** a hosted open-weight run (item 13); one unforced run that proposes, proves *and* **improves**. That is **still open after two designs**: `experiments/depth_i2c/` and `experiments/depth_tv80/` both route RTL unforced 3 of 3, and four proven transforms across them bought 0.000, 0.000, −0.268 and −0.421. The survival table's depth cell was attempted on a design large enough to show a gain (tv80, 3,447 cells, 0.152 ns floor) and **is empty there too**. Composition and the marginal gain after buffering: **done**, `experiments/composed_rtl/`. Closure cost: **done**, `experiments/closure_cost/`.

## 5c. Overfitting, and testing beyond our own design

The classifier's thresholds (`FANOUT_HI = 32`, share 0.50/0.20) were chosen on
**our** benchmark. That is the overfitting risk and it is tested three ways.

1. **20 external designs.** `experiments/drrtl_transfer/`, the designs published
   with Dr. RTL, run through the same flow at 0.9x each design's own measured
   requirement. 15 in scope, split 5 FANOUT / 3 MIXED / 7 DEPTH, byte-identical
   across two executions. The physical lever closes **5 of 5** fanout-dominated
   designs alone and **4 of 7** depth-dominated, which is the direction the
   classifier predicts. The primary registered prediction was **wrong**.
2. **A design the loop had never run on.** `experiments/unforced/` pointed the
   whole loop at `i2c_master_top`. It exposed **six defects in our own tooling**
   that our benchmark structurally could not: our SDC has one path group, our
   benchmark is one module per file. **None affected a published result**, and
   the finding cuts both ways: the router works, and the tooling had one
   design's worth of testing.
3. **A benchmark that grades the checker, not the design.**
   `experiments/slackbench/`, 8 sealed cases with ground truth committed before
   any checker ran, our own gate scored among them.

**What this does not establish:** that the thresholds are right for designs
unlike these. One external verdict is flow-sensitive, and the sample is 20
designs from one paper plus one from another.

## 5d. Models and keys

**Model: Claude Opus 5**, disclosed in every registration, default sampling,
one sample per proposal, no best-of-n. Three runs on one design returned three
different transforms, so the nondeterminism is measured rather than assumed.

**The proposer is not tied to it.** `tools/proposer.py` has three backends and
the prompt is plain text with no provider-specific syntax:
`--proposer handoff` writes the prompt to a file and reads a JSON reply, so any
model reachable by any means can be dropped in with no code change;
`--proposer cli` shells out to whatever `--claude-bin` names. Swapping to an
open-weight model is a flag and a binary, not a port. **Exercised, not asserted**
(`experiments/open_weight/`, registered first): Qwen2.5-7B-Instruct under Ollama,
no key and no vendor, the identical request. Zero changes under `tools/`, and it
**failed**: 1,172 s of CPU inference returned a reply that is not valid JSON,
part VHDL, module interface not preserved; it never reached G1. Scored 2
confirmed, 3 wrong, 1 void. **Run again with a code-specialised model**
(`experiments/open_weight_2/`, Qwen2.5-Coder-7B, registered first): the identical
failure, 1,335 s and invalid JSON. **With Ollama's JSON mode, registered in
advance as the follow-up, it returned valid JSON in 160 s and failed G1**: no
port list, reset on the rising edge of an active-low signal. Across two open-weight models and three runs, no proposal reached the formal gate,
**but all three were cut short**: Ollama's default context evaluated **2,050 of the request's 5,113 tokens**, so each model saw 40% of the task (measured 2026-09-14,
`experiments/open_weight_3/context_check/`). **The earlier reading, "the wall is the
engineering, not the envelope", is withdrawn.** So: portability exercised twice, capability
**not demonstrated at 7B on CPU, on a truncated prompt**, and **the organisers' open-source-key
recommendation is not met for the primary result**, which was produced with
Claude Opus 5. One hosted 31B attempt was rate-limited and void (item 13). Nothing here speaks for 32B or 70B open-weight
models served over an API, and the prompt was tuned against Claude Opus 5. **No API key is committed
anywhere**: the token lives in `~/.slacksmith_token` outside the repository and
`tools/preflight.sh` fails if a credential-shaped string reaches a tracked file.

## 5e. The speed-up the organisers asked for, and what we will say instead

They asked entrants to show how AI agents speed up a previously manual
optimisation workflow. **REPORT §1.1 refuses to state a ratio and quotes the
count below instead**, because no
engineer was ever timed doing the work, and a web search on 2026-09-12 found no
published per-obligation authoring time to borrow. Dividing by a number taken
from a verification-effort survey would be a category error with a citation
attached.

**So the numerator is counted instead of the denominator guessed**
(`experiments/speedup_step/obligation_cost.py`, run it yourself):

| branch | artifact | lines | code lines | port connections | properties |
|---|---|---|---|---|---|
| 1 combinational | `ctrl.eqy` | 11 | 9 | 0 | 0 |
| 2 k-padded miter | `miter_pipeline_domain_a.sv` | 138 | 71 | 28 | 4 |
| 2 runner | `miter.sby` | 32 | 23 | 0 | 0 |
| 4 mapped-state miter | `miter_mapped.sv` | 108 | 48 | 18 | 6 |
| 4 runner | `miter.sby` | 37 | 26 | 0 | 0 |
| **total** | 5 artifacts | **326** | **177** | **46** | **10** |

Every line is generated from the declared transform type in about a second.
Weigh 177 lines of hand-wired miter across three branches against your own
experience; we will not divide by a time we did not measure.

**The human side is registered and open, not abandoned**
(`experiments/speedup_step/PREREGISTRATION.md`, R70 to R72, amendment 1). It is
suspended because the one available author both wrote these transforms, which
makes him faster than a stranger, and is not practised at formal setup, which
makes him slower than a verification engineer. With N = 1 and both confounds
present the bias has no sign, and a ratio whose direction of error is unknown is
worse than no ratio.

## 6. How to verify any of this

    git clone https://github.com/nilaymastaadmi/nebula-slacksmith
    cd nebula-slacksmith
    bash tools/preflight.sh      # names any missing dependency
    bash tools/demo_check.sh     # 23 assertions across the claims above

`SETUP.md` lists the tool versions the results were measured with, and states
which claims re-derive in minutes and which cost an afternoon of synthesis.
