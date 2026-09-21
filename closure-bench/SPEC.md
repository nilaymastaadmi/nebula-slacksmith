# closure-bench specification v0.1

Phase 2. Written 2026-09-21. **Frozen before any result is generated.**

Version history lives at the bottom. Any change after the first result run is
an amendment with a date and a reason, never a silent edit.

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
not decoration: measured median gain was 3.623 ns on FANOUT against 0.481 ns on
DEPTH, a 7.5x split.

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

1. **Pinned tool versions, recorded by exact build.** Yosys 0.67+94
   (git sha1 `7defa5186-dirty`). OpenSTA and OpenROAD built from source;
   OpenROAD at `f12e2f474102bfb875eeee57fb610d7d7de17770`. Yosys being a dirty
   git build means an exact match from a release tarball is not achievable;
   the container is the fix and is the only supported way to reproduce.
2. **Pinned liberty and PDK, recorded by SHA256** in every run row.
3. **Pinned model IDs and API versions** for every agent baseline.
4. **Fixed seeds; temperature recorded per run.**
5. **Every result row carries the harness commit hash** that produced it.
6. **No absolute paths in any script.** Every path comes from an environment
   variable with a default, following `tools/env.sh`. This repo shipped with
   `cd /mnt/c/Users/toshn/...` at the top of 30 shell scripts until
   2026-09-05; that is the failure being designed out.
7. **Determinism test.** The same design, same seed, a non-LLM baseline: the
   outputs must be byte-identical. This is achievable - it was demonstrated at
   commit `694375d`. It is an automated test, not a claim.
8. **Every instrument is guarded.** Any command returning a count or a list is
   paired with an independent existence check, and an empty result over
   known-present data halts as a broken instrument rather than reporting zero.

---

## Version history

- **v0.1, 2026-09-21.** First draft. Frozen before any result exists.
  Holdout sealed at commit `c2f4186`.
