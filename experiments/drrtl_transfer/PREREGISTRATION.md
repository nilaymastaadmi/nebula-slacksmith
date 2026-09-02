# Pre-registration: SlackSmith's instrument on Dr. RTL's benchmark

Written 2026-09-02, **before any design in this study has been timed or
classified**. Git must show this file in an earlier commit than every file in
`results/`:

    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/drrtl_transfer/PREREGISTRATION.md \
      experiments/drrtl_transfer/results/

## Why this study, and why now

Everything this project has measured was measured on one benchmark we built
ourselves, and `tools/classify_path.py`'s thresholds were chosen after looking
at it. A literature pass on 2026-09-02 found the strongest direct prior work,
**Dr. RTL** (Fang et al., ICCAD 2026, arXiv 2604.14989), has published its 20
human-written baseline designs and its 47-entry skill library under Apache
2.0 at `github.com/hkust-zhiyao/Dr_RTL`. Those designs are the transfer test
this project has been missing, and three specific claims in that repository
are testable with instruments this project already has:

1. Its timing analyzer diagnoses "wide fan-in/fan-out" by having the model
   read the report ("Do NOT run any tools") and routes it to
   "combinational: logic restructuring, can fix". This project's measured
   result on its own benchmark is that fanout-dominated paths are not fixed
   by restructuring; a buffering pass beat the best proven RTL transform by
   3.6x at mapping level and 11.3x with placement parasitics.
2. Its **high-confidence skills #7 and #8** are "duplicate register / signal
   copies and split fanout cones". This project's registered prediction H2,
   measured, was that synthesis re-merges duplicated cones: max fanout in
   `aes_key_mem` was 2193 before and 2193 after, 0.0% change (N=1).
3. Its "Do not use" list (#36 priority flatten, #37 selector registering,
   #40 algebraic restructure, #43 memory decode rewrite, #46 comparison
   reorder) is a catalogue of transform classes this project's typed gate
   already discharges or refutes with counterexamples. That is phase 3 and
   is registered separately when it runs.

Only the 20 baseline (`v0`) designs are published. The versioned LLM rewrites,
per-iteration logs and SEC results are not in the repository, so "run their
transforms through our gate" is **not possible** and is not claimed.

## The designs, as found

Verified 2026-09-02: Yosys reads and synthesizes all 20 with zero errors.
Cell counts are Yosys generic `synth` counts, before technology mapping;
sky130-mapped counts are recorded by the runner.

| design | top | generic cells |
|---|---|---|
| aes | key_expansion_128aes | 28,350 |
| arm_cpu1 | arm9_compatiable_code | 21,209 |
| vending_machine | vending_machine | 17,021 |
| LSTM | lstm_cell | 15,647 |
| cpu_fsm | mini_cpu | 13,284 |
| FIFO | fifo | 13,111 |
| arm_cpu2 | risclite_mx | 8,043 |
| datapath | datapath | 6,040 |
| tv80 | tv80s | 6,013 |
| cpu_pipe | dcpu16_cpu | 3,908 |
| DSP | DSP | 3,449 |
| pcie | top | 2,215 |
| router | router_top | 1,841 |
| i2c | i2c_master_top | 652 |
| SPI | spi | 545 |
| simple_spi | simple_spi_top | 427 |
| UART | uart_top_design | 399 |
| communication | sync_serial_communication_tx_rx | 326 |
| controller | control_unit | 169 |
| ticket_machine | ticket_machine | 33 |

Their flow was Synopsys DC on Nangate 45 nm at a 0.1 ns clock with Jasper
SEC. Ours is Yosys/ABC on sky130hd with OpenSTA. **No number here reproduces
theirs and none is compared to theirs.** This study tests our instrument on
their designs, not their results.

## Phase 1 protocol, fixed in advance

For each design, identically:

1. Synthesize with the project's standard flow (`synth`, `dfflibmap`,
   `abc -liberty` with the `lpflow`/`probe` exclusion asserted non-empty,
   `opt_clean -purge`). Two netlists: **A** unbuffered, **B** with
   `buffer -N 16; upsize; dnsize`, exactly the physical lever from
   `experiments/buffering_control/`.
2. One clock, on the port `design_all.json` names. No I/O constraints. Only
   **register-to-register** paths are reported
   (`-from [all_registers -clock_pins] -to [all_registers -data_pins]`), which
   excludes I/O paths and reset recovery. That mirrors Dr. RTL's own #44
   ("do not attack constraint-only paths with RTL") and this project's
   `set_false_path` on resets.
3. **Closure target by this project's standing method**: time netlist A at
   a 1000 ns period, take the measured requirement, set the period to
   **0.9 x requirement**, rounded to 3 decimals. Same rule as
   `sdc/bench_top_v2.sdc` and `v3`. Recorded per design.
4. Time A at that period, classify the worst path with
   `tools/classify_path.py` using its thresholds **unchanged**
   (`FANOUT_HI=32`, `FANOUT_SHARE_HI=0.50`, `FANOUT_SHARE_LO=0.20`). No
   per-design tuning. If the thresholds are wrong for these designs, that is
   the finding.
5. Time B at the same period. Record the delta as the physical lever's gain.

Everything is written to `results/summary.tsv` plus per-design reports and
classifier JSON, in one run, with no design excluded after the fact.

## Predictions, recorded so the misses are visible

1. **All 20 time and classify** (no NO_PATH, no UNPARSED). High.
2. **Between 6 and 12 of 20 are FANOUT_DOMINATED** at the 0.9x target.
   Medium. Below 6 means this project's fanout finding was largely an
   artifact of its own benchmark's register arrays; that is a limit and
   will be reported as one.
3. **Named calls**, medium-low, recorded because being wrong is informative:
   FANOUT_DOMINATED for `aes`, `FIFO`, `LSTM`, `arm_cpu1`, `cpu_fsm`
   (register-file and array heavy); DEPTH_DOMINATED for `tv80`, `cpu_pipe`,
   `DSP`, `datapath` (arithmetic and decode chains).
4. **The router routes correctly on designs it has never seen.** The
   physical lever improves the worst reg-to-reg slack on **every**
   FANOUT_DOMINATED design, and on **fewer than half** of the
   DEPTH_DOMINATED ones. Medium. **This is the primary prediction.** It is
   the one that says the classifier transfers.
5. At least one DEPTH_DOMINATED verdict will show a top cell with an
   implausible delay at reported fanout of 2 or less. Medium. This is the
   known bus-port undercount in `docs/path-classification.md`, registered as
   a defect check rather than a hope.

## Phase 2, registered now, run after phase 1 reports

On every design phase 1 classifies FANOUT_DOMINATED, apply Dr. RTL skill #7
as written (duplicate the register driving the highest-fanout net on the
worst path, split its consumers), twice: once as plain RTL, once with
`(* keep *)` on the duplicates. Measure max fanout and worst slack after ABC.

6. **Plain duplication changes max fanout by less than 20% on at least 80%
   of those designs**, because ABC re-merges functionally identical cones.
   Medium-high; H2 at N=1 says so.
7. **With `(* keep *)` fanout splits, and the slack gain is smaller than the
   buffering lever's on at least 80% of those designs.** Medium.

## The bar

**Primary:** prediction 4. **Reported regardless:** all 20 rows, both
netlists, the named-call scorecard, and the phase 2 table. A result where the
classifier does not transfer is more useful than one where it does, because
it bounds a claim this report currently makes on N=1 benchmark.

## Amendment 2026-09-02, after run 1, before run 2

Run 1 (commit `534bc35`, preserved unchanged in `results_run1_as_registered/`)
timed 15 of 20 designs. The other 5 were recorded as NO_PATH and that label
was **wrong**: OpenSTA could not read those netlists at all. Two causes, both
flow compatibility, neither a property of the designs:

1. `LSTM` declares 38 `signed` ports, which OpenSTA's Verilog reader rejects.
2. `FIFO`, `SPI`, `UART`, `pcie` use sync-reset flops. `dfflibmap` cannot map
   the `$_SDFF_*` forms, and Yosys wrote them out as behavioral `always`
   blocks. This project's own benchmark uses async resets everywhere and
   never produced them.

A third defect surfaced in the classifier on `DSP` and `tv80`: instances in
**parameterised** submodules (`\$paramod\...` names containing `=`, quotes and
backslashes) never matched the module-header regex, so 5 and 10 cells on
those paths respectively resolved to fanout `None` and their DEPTH verdicts
rested on unresolved fanout.

Changes, all to tooling and none to thresholds or the 0.9x rule:

- Synthesis adds `opt -nodffe -nosdff; dfflegalize ...` before `dfflibmap`,
  strips `signed` from netlist declarations, and labels any netlist that
  still carries `always` or `signed` as `FLOW_FAIL`.
- The STA helper labels an unreadable netlist `STA_READ_FAIL`. An empty
  result is never again recorded as a verdict.
- `tools/classify_path.py` accepts parameterised module and instance-type
  names.

Because the flow changed, **all 20 designs are re-run identically** rather
than only the 5 that failed, so treatment stays uniform. For the 15 designs
run 1 timed, run 2's numbers are expected to match run 1 exactly wherever the
design has no sync-reset flops; any difference is reported.

The predictions above are scored against **run 2**. Run 1 is reported next to
it, including that prediction 1 ("all 20 time and classify") was already
false at the tooling level before any design got a chance to falsify it.

## Amendment 2, 2026-09-02, after run 2, before run 3

Run 2 (preserved in `results_run2_nodffe/`) showed the sync-reset hypothesis
above was **wrong**. What actually keeps four designs out of this flow:

- `FIFO`: 32 `$_ALDFF_PN_` **async-load** flops (the reset branch loads a
  non-constant value). No sky130 standard cell implements that.
- `SPI`, `UART`, `pcie`: **inferred latches** (`$_DLATCH_NP0_`: 65, 41 and
  several). This project's own gate G2 rejects latches by policy.

These are properties of the designs, and they are **out of scope for a
stated reason**, labelled `FLOW_FAIL`. `LSTM` has **0 flops** (the cell is
combinational as published), so no reg-to-reg path exists: `NO_PATH`, which
run 2 mislabelled `STA_READ_FAIL` by matching any OpenSTA "Error" line. The
helper now distinguishes a Verilog syntax error from an empty register
collection.

Run 2 also introduced a change that should not have been made. `opt -nodffe`
unrolled enable flops into muxes on 6 designs that timed fine in run 1,
changing their netlists (`cpu_fsm` 7,883 to 12,196 mapped cells) and
flipping `arm_cpu2` from FANOUT_DOMINATED (0.609) to DEPTH_DOMINATED (0.132).
sky130hd has enable flops (`edfxtp`); the option was unnecessary and is
removed for run 3. `opt -nosdff` stays, since sky130hd has no sync-reset flop.

**Run 3 is the scored run.** It is expected to reproduce run 1 exactly on the
15 designs run 1 timed; any difference is reported. The `arm_cpu2` verdict
flip between runs 1 and 2 is itself reported as a **flow sensitivity of the
classifier on 1 of 15 designs**, whichever way run 3 lands.

Predictions 1 and 2 are scored against the 15 in-scope designs with the 5
out-of-scope ones listed, not silently dropped: the registration's "all 20"
wording is kept and marked as failed at the tooling and design-property level.

## Amendment 3, 2026-09-02, after run 3, before run 4

Run 3 (preserved in `results_run3_legalized/`) did **not** reproduce run 1.
`dfflegalize` with an explicit cell list restructured enable-polarity flops
and changed **7 of 15** in-scope netlists: `datapath`'s measured requirement
moved 7.688 to 9.258 ns, `arm_cpu2` read DEPTH_DOMINATED at 0.089 (run 1:
FANOUT_DOMINATED 0.609; run 2: DEPTH 0.132), and `simple_spi`, `i2c`, `tv80`,
`arm_cpu1`, `vending_machine` all moved. None of this rescued a failure,
because the 5 failures are design properties.

The conclusion is that **run 1's flow, the project's unmodified standard
flow, was correct for every in-scope design**, and the only defect in run 1
was five labels. Amendments 1 and 2 changed the flow on a wrong hypothesis
(sync-reset flops) and are reverted for run 4, which keeps only what was
actually needed: the `signed` strip (affects `LSTM` only, which has no
registers anyway) and the READ_FAIL / NO_PATH / FLOW_FAIL labels.

**Run 4 is the scored run.** It must reproduce run 1's 15 timed rows
**exactly**; that is now a determinism check on the flow, and any deviation
is reported. Runs 2 and 3 are reported together as a **flow-sensitivity
study**: the classifier's verdict on `arm_cpu2` depends on how enable flops
are legalized, and that is a limitation of the classifier, stated.

Three amendments to get one run right is itself a finding about this study,
and it is left visible rather than squashed into a clean history.

## What would make this study void

- Any design dropped after being timed.
- Any classifier threshold changed after the first result is seen.
- Per-design clock periods set by anything other than the 0.9x rule.
- The git ordering check at the top failing.
- Reporting phase 2 without phase 1, or a subset of either.
