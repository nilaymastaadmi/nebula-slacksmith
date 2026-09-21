# ClosureDuel specification v0.4

Phase 2. Written 2026-09-21. **Frozen before any result is generated.**

Version history lives at the bottom. Any change after the first result run is
an amendment with a date and a reason, never a silent edit.

---

## 2.0 Scope, v0.3: a head-to-head, not a benchmark

Amended 2026-09-21 before any arm has run; the reasoning is in `VISION.md`,
"Decision, 2026-09-21".

**The primary comparison** is closure rate (2.2) between the best LLM agent
configuration and the classifier-routed classical arm, at matched budget, on
the development designs, reported with each arm's run-to-run spread. Every
other arm is reported in the same table and is secondary.

**Arms.** Six classical arms, defined and pre-registered in
`PREREGISTRATION.md` before any of their code exists:

| # | Arm | What it is |
|---|---|---|
| C0 | null | no transform; the floor |
| C1 | `repair_design` | OpenROAD's stock repair, stock settings |
| C2 | buffer-only | the measured buffering lever alone |
| C3 | sizing-only | the measured sizing lever alone |
| C4 | classifier-routed | the FANOUT/DEPTH/MIXED classifier picks C2 or C3 per design; this arm carries the contribution |
| C5 | random | transforms drawn at random from the same action space, at matched budget |

The LLM agent arms A, B and C (2.1) come after the classical arms are complete,
and not in the session that builds the classical arms.

**Designs.** The 10 development designs only. The 5 sealed holdout designs
(2.3) are touched once, in the final run, and the harness refuses them before
then.

**Trials per cell.** A classical cell gets exactly one trial, **after**
determinism has been shown for that arm by running it twice on every design and
getting byte-identical output; an arm that is not deterministic is treated as
stochastic and is repeated like the agents. The random arm and the agent arms
are stochastic. Their trial count comes from the power analysis in 2.5, which
cannot use the classical arms' spread, because that spread is zero.

---

## 2.1 Task definition

### Input the agent receives

Per design, per run:

| Item | Form |
|---|---|
| RTL source | the original `*.v0.v` / `*.v0.sv` file, unmodified |
| SDC constraints | a frozen `.sdc`, SHA256 recorded in the run row |
| Target clock period | stated in ns in the task prompt and in the SDC |
| Liberty | `sky130_fd_sc_hd__tt_025C_1v80`, SHA256 recorded |
| Current STA report | OpenSTA output for the unmodified design at the target period |

### Tool access - stated explicitly, and enforced

Three arms. The distinction is the whole point of the arm split, so the
harness **enforces and verifies** it rather than trusting the prompt.

- **Arm A, single-shot, no tools.** One prompt, one response, one transform
  list. The agent process runs with no network egress except the model API and
  no executable EDA tool on its PATH.
- **Arm B, tool-using loop.** The agent may invoke exactly: `yosys`,
  `sta` (OpenSTA), and a read-only `report_checks` wrapper. The tool list is
  reproduced in the results table, not just here.
- **Arm C, tool-using plus the skill library.** Arm B's tools, plus Dr. RTL's
  published 47-skill library supplied in the context. This is the registered
  arm C from the deferred batch 3.

**Why enforcement and not assertion.** In our own prior work `claude -p` was
tool-using in 12 of 13 runs that were recorded as blind. An arm labelled
"no tools" that silently had them invalidates the comparison the arms exist to
make. Arm A therefore asserts, per run, that the tool-invocation count is zero
and **fails the run as `TOOL_ERROR` if it is not**, rather than recording it as
a result.

### Action space

The agent emits an ordered list of transforms. Legal members, and nothing else:

1. **RTL edit** - a unified diff against the input source.
2. **Synthesis directive** - a Yosys/ABC command from a published allowlist.
3. **Constraint change** - an SDC edit. Permitted, and audited: see the
   constraint-integrity rule below.

Anything outside this list is `ILLEGAL_EDIT`.

### Termination

All three bounds apply; whichever binds first ends the run:

- **Wall clock:** 30 minutes per design per run.
- **Tokens:** 200,000 total (prompt + completion), counted by the harness.
- **Iterations:** 8 propose-evaluate cycles.

### What counts as a legal submission

1. Synthesises under the pinned Yosys without error.
2. Passes **combinational equivalence checking** against the original.
3. Does **not** change the module interface: port names, widths and directions
   identical.
4. Cell area increase <= 20%.
5. **Constraint integrity.** The SDC's statement count and hash are recorded on
   every row. A submission whose timing improvement comes from adding a timing
   exception is reported in a separate column and **never counted toward the
   closure rate**. This exists because one `set_multicycle_path` line was worth
   +5.179 ns on a byte-identical netlist in our own prior work, which no
   equivalence checker can catch, because the two designs are the same file.

CEC and not SEC is a deliberate v1.0 limit. SEC is strictly stronger and is
what Dr. RTL uses; CEC cannot verify a transform that changes state encoding
or latency. Any transform requiring SEC is rejected as `ILLEGAL_EDIT` in v1.0
rather than silently accepted.

---

## 2.2 The metric

### Primary

> **Closure rate at fixed budget**: the fraction of designs whose worst
> negative slack reaches >= 0 within the budget, subject to passing CEC, an
> unchanged interface, <= 20% area increase, and constraint integrity.

Argued in `VISION.md` section 2. One number, binary per design, so it has a
well-defined variance across seeds.

### Secondary - all reported, none headline

- Median and IQR of WNS improvement (ns).
- **Total negative slack improvement, reported alongside per-group WNS.**
  These two disagreed in our own prior runs: sizing gained 0.838 on one clock
  group while moving another from +1.75 to -1.716, which the per-group bar
  confirmed and the total bar reverted. Reporting only one hides that.
- Area delta, flop-count delta.
- USD and tokens per design, captured per run, not estimated afterwards.
- Wall clock per design.
- **Run-to-run standard deviation across seeds.** This is the reliability half
  and the claim in `VISION.md` section 3 is about it.

### Reporting rule

The headline chart is closure rate **with error bars across seeds**. A bar
chart of best runs is a misuse of this benchmark, for the same reason a single
score per checker is a misuse of the existing SlackBench.

---

## 2.3 Design set, tiers, and the sealed holdout

### In scope: 15 of Dr. RTL's 20

Source: `github.com/hkust-zhiyao/Dr_RTL`, `rtl_dataset/`.

### Excluded: 5, each with its reason

| Design | Reason |
|---|---|
| `FIFO` | asynchronous-load flops; the flow cannot map them to a timed path |
| `SPI` | latch-based; no register boundary to close against |
| `UART` | latch-based |
| `pcie` | latch-based |
| `LSTM` | contains no registers at all, so there is no timing path to close |

These are flow properties, not tuning decisions, and they were established
before this specification existed.

### Difficulty tiers

From the corrected path classifier. The stratification is a real contribution,
not decoration: the combined lever's measured median gain was 3.623 ns on
FANOUT against 0.581 ns on DEPTH, a 6.2x split, after the classifier
correction. (v0.1 of this file said 0.481 ns and 7.5x, the pre-correction
grouping; corrected in v0.3. Source: `experiments/drrtl_transfer/NOTES.md`,
re-scored table.)

| Tier | n | Designs |
|---|---|---|
| FANOUT | 5 | cpu_fsm, datapath, aes, communication, arm_cpu2 |
| MIXED | 3 | router, tv80, arm_cpu1 |
| DEPTH | 7 | vending_machine, ticket_machine, DSP, simple_spi, controller, cpu_pipe, i2c |

Tiers come from the **corrected** classifier. The pre-correction classifier
undercounted fanout across module boundaries; `tv80` moved DEPTH to MIXED as a
result. Never quote a pre-correction verdict.

### The sealed holdout

**Selection rule, published so the pick is mechanical rather than chosen.**
Stratified 2 FANOUT / 1 MIXED / 2 DEPTH. Within each tier, designs are ranked
by `SHA256("c2f4186:" + design_name)` and the lowest are held out. The salt
`c2f4186` is the commit that added `VISION.md` and `PRIOR_ART.md`, which
existed before this selection did and could not be chosen to produce a
favourable split. Regenerate with `tools/select_holdout.py`.

| Tier | Design | File | Bytes | SHA256 |
|---|---|---|---|---|
| FANOUT | arm_cpu2 | `arm_cpu2.v0.v` | 35281 | `9089774688d22ad7d371324ebe1595963e1ba85b7ac1c76b1b68acac550fd061` |
| FANOUT | datapath | `datapath.v0.v` | 28751 | `7647ab3f5bd554c5f0c6060712a63ed59a6a83805cfbd5b76bdd3f9d8ed35594` |
| MIXED | arm_cpu1 | `arm_cpu1.v0.v` | 57630 | `bb2020ea808fcf7125064fddfaf5214b858cebcfafca59cd5962af8a391dddcf` |
| DEPTH | simple_spi | `simple_spi.v0.v` | 15348 | `5d31bfd3742a88c95177281b525ebd5f2f03b3d727814e1bc5d2bde590035d2c` |
| DEPTH | controller | `controller.v0.v` | 14327 | `5f46393afd33b60b6e2ad31e0d012e9a9792972aab1258ce9b52f430d3b1e106` |

Development set, the remaining 10: cpu_fsm, aes, communication, router, tv80,
vending_machine, ticket_machine, DSP, cpu_pipe, i2c.

### What this seal does NOT protect against - stated, not hidden

**The transfer-study results for all 15 designs are already committed and
visible** in `experiments/drrtl_transfer/`. We know which designs the physical
lever closed and which it did not. So this holdout is weaker than a true sealed
holdout: it prevents tuning from **here forward**, and it does not and cannot
undo what has already been seen.

This is the same honesty split the existing SlackBench uses for Tier A against
Tier B. Presenting these five as blind would be the fraud the split exists to
prevent. The claim that *is* supportable: no agent prompt, scoring rule or
threshold is tuned against these five after this commit, and the mechanical
selection rule means the five were not chosen to flatter a result.

### Independence

5 to 10 designs from outside Dr. RTL are desirable for independence and are a
v1.1 item, not v1.0. Licences get checked before anything is added.

---

## 2.4 Reproducibility contract - hard requirements

1. **Pinned tool versions, recorded by exact build.** The container is the
   only supported way to reproduce, and it is pinned by tag and digest:
   `openroad/orfs:26Q3-600-g3a964e13f@sha256:7fbb16f7aaf3caa170ea308c1bd833defc7fdf1f5316303dce6a0e6eeb6deee9`,
   which names OpenROAD-flow-scripts commit `3a964e1` (master, 2026-09-19).
   `docker/stamp.sh` records every tool version into `TOOLCHAIN.txt` at build
   time and fails the build if a tool or the liberty is missing.

   **The prior host toolchain is archival, not the benchmark toolchain.** Every
   number in `experiments/` was measured on Yosys 0.67+94 (`7defa5186-dirty`)
   and OpenROAD `f12e2f4`, which is **2022-03-26**, four and a half years old.
   A 2026 benchmark cannot rest its classical `repair_design` baseline on a
   2022 build: the baseline is re-measured in the container, and the host
   numbers are reported as a flow-sensitivity column, never as benchmark
   results. (The prior finding that `repair_design` takes no `-max_fanout`
   flag is **not** a 2022 artifact: the current signature has no such flag
   either, and fanout is repaired from the SDC's `set_max_fanout`.)
2. **Pinned liberty and PDK, recorded by SHA256** in every run row. Host
   reference: `sky130hd_tt.lib` sha256
   `70a45bf9b5ea8f6a701dc34744b5c767b38e1af31b1d1f97309a97ec64603ecf`. The
   container's copy is recorded at build time; whether the two are the same
   file is a measured fact, not an assumption.
3. **Pinned design source, and never redistributed.** Designs come from
   `github.com/hkust-zhiyao/Dr_RTL` at commit
   `8d86c0e3d0a6260a3b20caa98412e81f496ad19a`, the commit the holdout was
   sealed against. Upstream has since moved to `62b95a5`, and the two commits
   between touch only `CLAUDE.md` and `README.md`: `rtl_dataset/` and
   `syn_flow/design_all.json` are identical, so the seal holds against current
   upstream too. **Dr_RTL carries no licence** (no LICENSE file, GitHub reports
   none, and 19 of 20 design files carry no licence text; `simple_spi` alone
   keeps an OpenCores header). Unlicensed code is all-rights-reserved by
   default, so designs are mounted at runtime and are never copied into the
   repo or the image. **This is a release blocker for v1.0**: see the note at
   the end of this section.
4. **Pinned model IDs and API versions** for every agent baseline.
5. **Fixed seeds; temperature recorded per run.**
6. **Every result row carries the harness commit hash** that produced it.
7. **No absolute paths in any script.** Every path comes from an environment
   variable with a default, following `tools/env.sh`. This repo shipped with
   `cd /mnt/c/Users/toshn/...` at the top of 30 shell scripts until
   2026-09-05; that is the failure being designed out.
8. **Determinism test.** The same design, same seed, a non-LLM baseline: the
   outputs must be byte-identical. This is achievable - it was demonstrated at
   commit `694375d`. It is an automated test, not a claim.
9. **Every instrument is guarded.** Any command returning a count or a list is
   paired with an independent existence check, and an empty result over
   known-present data halts as a broken instrument rather than reporting zero.

---

### Release blocker: the design set has no licence

v1.0 as specified ships a public repo, a public container and a leaderboard
built on Dr. RTL's designs. None of those needs the designs to be
redistributed, because they are fetched at runtime, so the harness itself is
unaffected. But a benchmark whose entire design set is all-rights-reserved is
fragile: a takedown request removes the benchmark. Resolve before v1.0, in
this order of preference: ask the Dr. RTL authors (HKUST) to add a licence;
otherwise re-source designs that carry a licence of their own (OpenCores
originals such as `tv80` and `simple_spi` do, upstream); otherwise ship with
the runtime-fetch design documented as the reason nothing is redistributed.

---

## 2.5 Power: how many agent trials per design

Added in v0.4, before any agent arm exists. Computed by `power/power.py`;
the numbers live in the generated `results/POWER.md` and `results/power.json`,
and are not copied here, so they cannot drift.

**Why the classical arms cannot size this.** They are deterministic (checked
per candidate, `results/RESULTS_classical.md`, P10), so their run-to-run
spread is zero. The trial count depends only on the agent's spread, which no
paper in `PRIOR_ART.md` publishes.

**The effect to detect** is SynAct's own, in SynAct's own metric: the WNS
violation ratio `max(0, -WNS) / max(0, -WNS of the baseline)`, closure
counting as zero; per design, CBTune's ratio minus SynAct's, from SynAct
Table III (`power/synact_table.csv`, transcription checked against the paper's
printed averages).

**The method.** Exact two-sided one-sample noncentral-t power against a
deterministic classical value, at 80% power, tabulated over the agent's
unknown SD, at alpha 0.05 for one design and 0.005 (Bonferroni over 10
designs). The code must reproduce published reference sample sizes before it
emits anything. The table is anchored on C5 random's measured across-seed SD,
which is a random policy's spread, not an agent's.

**The rule it sets for the agent arms.** Run an agent's first 5 trials on
every development design, measure its SD, read the trial count off the table
at that SD for the median-sized effect, Bonferroni row, and run to that count.
The count is fixed before the remaining trials run, and is not revised after.

**What trials cannot buy.** The headline is a closure comparison across
designs. Whatever the trial count, a two-sided exact sign test needs the agent
to win on the number of designs `results/POWER.md` states (of 10 development
designs, or of 15 with the holdout), ties removed. Trials make each per-design
verdict trustworthy; only more designs make the headline stronger.

## Version history

- **v0.1, 2026-09-21.** First draft. Frozen before any result exists.
  Holdout sealed at commit `c2f4186`.
- **v0.2, 2026-09-21.** Amendment, made before any benchmark result exists.
  Reason: the toolchain pins in 2.4 were placeholders naming the host build;
  they now name the container image by tag and digest. Adds: the finding that
  the host OpenROAD is from 2022 and is therefore archival; the host liberty
  hash; the pinned Dr_RTL commit; the no-licence finding and the release
  blocker it creates. Section 2.1 to 2.3, the metric, and the holdout are
  unchanged.
- **v0.3, 2026-09-21.** Amendment, made before any arm has run. Reason: the
  project narrows from a benchmark platform to a head-to-head (`VISION.md`,
  "Decision, 2026-09-21"). Adds 2.0 (primary comparison, six classical arms,
  development designs only, one trial per classical cell conditional on a
  shown determinism). Corrects 2.3's lever split from the pre-correction
  "0.481 ns, 7.5x" to "0.581 ns, 6.2x". The metric, the legal-submission bar,
  the tiers and the holdout are unchanged. Section 2.5, the power analysis, is
  added when it is computed.
- **v0.4, 2026-09-21.** Adds 2.5, the power analysis, and the rule it sets for
  the agent arms' trial count (5 pilot trials, then the Bonferroni-row count at
  the measured SD, fixed before the rest run). Written before any agent arm
  exists. Nothing earlier is changed.
