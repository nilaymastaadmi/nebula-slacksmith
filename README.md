# SlackSmith

**A GenAI RTL optimization loop that proves each RTL change correct, then measures whether it helps.**

Nebula, Astera Labs @ BITS Pilani Goa. Track A (Digital): *Constraint Optimization
through RTL Enhancement Using Generative AI*. Nilay Toshniwal and Shivani Chaudhary.

## The submission

| | file |
|---|---|
| **Report**, 12 pages | [`REPORT.pdf`](REPORT.pdf) (source [`REPORT.md`](REPORT.md)) |
| **Demo video**, 4 min 58 s, narrated | [`slacksmith_demo.mp4`](slacksmith_demo.mp4) |
| **Deliverable inventory**, every claim with its evidence file | [`SUBMISSION_PACK.md`](SUBMISSION_PACK.md) |
| **Interactive demo**, one offline page generated from the logs | [`demo/explorer.html`](demo/explorer.html) |
| Shot list and the command behind every beat of the video | [`DEMO.md`](DEMO.md) |
| Setup, tool versions, and which claims take minutes or an afternoon to re-derive | [`SETUP.md`](SETUP.md) |

## What the loop does

One command runs the steps an engineer otherwise does by hand, and records every
decision with the evidence it used:

![The SlackSmith loop](docs/slacksmith_loop.svg)

1. **G0, constraint integrity.** Fingerprint the SDC and count its timing exceptions,
   so a constraint edit cannot pass as a timing gain.
2. **Synthesize and time** with Yosys and OpenSTA.
3. **Classify the binding path** by fanout-attributable delay, and route the fix:
   physical (buffering, sizing, `repair_design`) or RTL.
4. **Propose.** An LLM emits a *declared transform type* plus replacement RTL.
5. **Generate and discharge the proof obligation from the declared type**:

   | declared | obligation | discharged by |
   |---|---|---|
   | k = 0, state-preserving | combinational / sequential equivalence | EQY, `yosys-abc dsec` |
   | k > 0, rigid interface | k-padded miter | SymbiYosys, BMC + PDR |
   | k > 0, elastic interface | stream equivalence (proven by hand; no gate route yet) | SymbiYosys + `cover` |
   | k = 0, re-encoded state | mapped-state equivalence | SymbiYosys, sequential miter |
   | k = 0, register moved | retiming | SymbiYosys, sequential miter |

6. **Re-time, then accept or revert**, with a null control run before any refutation
   is reported.

## Deliverables

| # | deliverable | status | evidence |
|---|---|---|---|
| 1 | RTL timing analysis framework | full | `tools/slacksmith.py`, `tools/remeasure.py`, three versioned SDCs, G0 |
| 2 | GenAI-based RTL optimization engine | **met on `tv80s`, proposer disclosed** | 27 proposals in three provenance tiers, 11 unattended, all four named classes routed. One unattended run chose RTL unaided and produced a proven transform that survives `repair_design` (+0.846 ns); its proposer was an agent with a shell in this repository (`experiments/survival_tv80/`) |
| 3 | Critical path and timing violation analysis | full | `tools/classify_path.py`, regression-checked against OpenSTA's fanout column |
| 4 | Optimized RTL implementation | **met on `tv80s`** | `experiments/survival_tv80/results/run6/online_variants/`, proven, +0.846 ns after `repair_design`. The benchmark's `experiments/composed_rtl/aes_key_mem_composed.v` is proven too, and its gain does not survive the physical flow |
| 5 | Timing, frequency and PPA comparison | full | report §8, `experiments/ppa/`, `experiments/closure_cost/` |
| 6 | Formal equivalence verification report | full | five obligation branches proven, four routed by the gate; G6 and G7; `experiments/slackbench/` |
| 7 | Interactive demo | full | `demo/explorer.html` and the narrated video |

The benchmark, `bench_top`, is **55,413 standard cells** hierarchical (48,616 once
flattened, the count the video shows) with five independent
asynchronous clock domains, a generated clock per domain including /3 and /5
dividers, gray-code FIFOs on every multi-bit crossing and two-flop synchronizers
on every single-bit one (`rtl/`, report §4).

## What we measured

- **The model proposes transforms that are wrong.** Of 12 proposals frozen before
  any check ran, **3 were formally refuted**. One of them passes every
  precondition, cuts 208 cells, and survives the design's own firmware and 20,000
  random instruction vectors; the formal gate caught it in **46 seconds** with a
  concrete counterexample.
- **Correct transforms were aimed at the wrong variable.** The binding paths were
  **59% to 91% fanout-attributable delay**. Like for like on one group, a proven
  FSM re-encoding buys **+3.185 ns** while the physical lever takes the same group
  from **−18.957 to +5.6**: about one eighth.
- **On the benchmark, nothing the RTL half bought survived the physical flow.** Three
  proven transforms composed into one file are worth **+5.165 ns** before wires,
  **0.000** after buffering, and **−0.237 ns** after `repair_design`, inside a 0.24 ns
  floor. On two external designs where the router chose RTL unaided, the first four
  proven transforms bought **0.000, 0.000, −0.268 and −0.421 ns**.
- **Then one survived, and the proposer was an agent.** Six registered runs on `tv80s`:
  a proven transform lands **+0.846 ns** better than gold after `repair_design`, 2.26
  times the design's noise floor and better in all four columns. The unattended
  `claude -p` proposer turned out to be the Claude Code agent with a shell in this
  repository: that session read earlier results and ran synthesis, timing and
  equivalence before replying. The gate verdict and the measurement were redone after
  the runs, outside it. Six blind runs with the tools removed produced no surviving gain; the best proven one,
  +0.444 ns, has the null control's shape (`experiments/survival_tv80_blind/`).
- **Closure has a price, measured.** `repair_design` closes all three violating
  groups with placement parasitics at **+20.2% area**, and **+47.1% power** measured
  zero-parasitic.
- **One constraint line is worth +5.179 ns on a byte-identical netlist**, and every
  equivalence checker we own correctly calls the two designs equivalent. That is what G0
  exists to catch.
- **SlackBench grades the checker, not the design**: 8 sealed transform pairs with
  ground truth committed first, our own gate scored among them.

The negative results are the point. Proof and profit are independent questions,
and the report measures both.

## Run it

```
git clone https://github.com/nilaymastaadmi/nebula-slacksmith
cd nebula-slacksmith
bash tools/preflight.sh      # names any missing dependency and where to get it
bash tools/demo_check.sh     # runs every command in DEMO.md: 24 assertions
```

The loop on its own:

```
python3 tools/slacksmith.py \
  --sdc sdc/bench_top_v2.sdc \
  --clock clk_a --clock clk_b --clock clk_e \
  --workdir ~/run --engine sta
```

It closes SDC v2 in 2 iterations, a median **112.7 s** on one core
(`experiments/loop_runtime/`), and writes every routing decision with its
evidence to `decisions.jsonl`. Clone rather than download a zip: one assertion
checks that each pre-registration was committed before its results, which needs
the git history. The history was rewritten on 2026-09-14 to normalise authorship and
messages, with dates and order unchanged, so the video's beat 4 shows the earlier
hashes `4ee45c22` and `7e3ab9b4`, now `04fa59c4` and `115fc03f`.

## Layout

```
REPORT.md, REPORT.pdf      the report
slacksmith_demo.mp4        the demo video, recorded before the tv80 survival result (report §7.8)
SUBMISSION_PACK.md         deliverables, objectives and known-open items, each with its evidence
DEMO.md                    the video's shot list; tools/demo_check.sh runs every command in it
SETUP.md                   dependencies, versions, cost of re-deriving each claim
rtl/                       bench_top and its five domains; rtl/aes is vendored, BSD-2
sdc/                       v1 frozen, v2 closure targets, v3 generated by make_v3.py
tools/                     the loop, the classifier, the obligation gate, G0, G6, G7, checks
experiments/               every result, each with its registration, sources, logs and NOTES
docs/                      measurement methodology, path classification, the closed loop
demo/                      the interactive explorer and the video's sources
```

## Limits

Stated in full in report §9 and §10 and in `SUBMISSION_PACK.md` §5. In short: 27
proposals from one proposer model (Claude Opus 5), so outcomes, not rates;
13 unattended runs that are not independent, because the agent read earlier results,
and one surviving gain, N = 1; the physical flow reaches CTS and global routing,
not signoff; equivalence is not proven for the ABC buffering lever; modules
instantiated with parameter overrides are refused unless the value is passed with
`--param`; and the
organisers' open-source-model recommendation is not met for the main result.
