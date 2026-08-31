# The buffering control: what the RTL transforms were competing against

Run 2026-08-31. Registered in advance in
`experiments/llm_proposer_aes/PREREGISTRATION.md` as the yardstick for
hypothesis H1, and committed before its output was read.

**This is a control, not a transform.** It changes zero lines of RTL. It is
never reported as a SlackSmith result and no proposal is credited with it.
Its whole job is to answer a question the project had not asked: how much of
the benchmark's timing violation is reachable without touching the RTL at
all?

## Method

`bench_top` is synthesized twice from byte-identical RTL and timed under
byte-identical SDC (`sdc/bench_top_v2.sdc`). The only difference is the ABC
script:

| | ABC script |
|---|---|
| A | the Yosys default for `-liberty` |
| B | the same script with `buffer -N 16; upsize; dnsize` appended |

Yosys already ships `buffer; upsize` in its `-liberty -constr` script but not
in the plain `-liberty` script this project had been using, so B is a stock
pass that the flow was simply not running.

The `lpflow`/`probe` exclusion is applied to both and asserted non-empty
before either build starts (72 flags). That assertion exists because this
project has already shipped one silently-empty exclusion list; see
`docs/measurement-methodology.md` finding 4.

## Result

| clock | A, default | B, buffered | delta |
|---|---|---|---|
| clk_a | +1.333 MET | **+12.784 MET** | +11.451 |
| clk_b | **-4.957 VIOLATED** | **+12.600 MET** | **+17.557** |
| clk_e | **-4.957 VIOLATED** | **+20.394 MET** | **+25.351** |

**Both violated clock groups close.** The design meets timing on every
reported group after a pass that touches no RTL.

## What actually changed in the netlist

| | A | B |
|---|---|---|
| cell instantiations | 28,844 | 30,264 |
| buffers (`buf_`, `clkbuf_`) | 0 | **1,419** |
| inverters | 196 | 196 |
| flip-flops | **5,191** | **5,191** |
| banned `lpflow`/`probe` cells | 0 | 0 |
| nets with fanout > 64 | **112** | **27** |
| p99 fanout | 44 | 25 |

The flop count is identical and the cell growth (+1,420) is almost exactly
the buffer count (+1,419), which is what a pure buffer-insertion pass should
look like. Nets above fanout 64 drop by 76%.

The `clk_b` critical path moves out of `u_aes_b/u_core/keymem/` entirely; in
B the binding `clk_b` path is a 3-cell clock-domain crossing in
`u_domain_b` carrying 0.468 ns.

## Equivalence, checked rather than assumed

`buffer`/`upsize`/`dnsize` are documented as function-preserving, which is
not evidence. Yosys `equiv_make` + `equiv_simple` + `equiv_induct` over the
two flattened netlists discharged **49,923 of 49,924** equivalence
obligations.

The single residual is a top-level 2-input XOR (`sky130_fd_sc_hd__xor2_1`)
for which Yosys reports "No SAT model available". Its input net is undriven
in **both** designs: the log emits `Setting undriven nets to undef` for the
corresponding net on the gold side and the gate side alike. There is no
model to build and no asymmetry between the two designs. A second,
independent run with `equiv_struct` in front reduced the problem to 16 cells
and left the same one, so the count is reproducible rather than a
solver-effort artifact.

Stated plainly: this is 1 obligation in 49,924 left open for a tool reason,
not a counterexample. It is recorded here rather than rounded to "proved
equivalent".

## Why this matters more than a 17 ns number

Set it against the RTL transforms measured under the same SDC:

| lever | best measured gain on the group it targets |
|---|---|
| batch 1 RTL, best of 6 (P2) | +0.485 ns |
| batch 2 RTL, best of 6 (A4) | +4.925 ns |
| **this buffering pass, zero RTL change** | **+17.557 ns** |

Batch 1 spent six formally-gated LLM proposals on a path that
`tools/classify_path.py` scores at **58.9% fanout-attributable delay**. Four
of those six were proven correct and three of them made timing worse. That
is not a surprising outcome once the path is classified: they were
restructuring logic on a path whose delay was mostly net loading.

**The conclusion is not that RTL work is pointless. It is that the two
levers are sequential, not alternative.** After buffering, the remaining
violations on this design are measurably depth-dominated (0.0%
fanout-attributable at period/6 on both `clk_b` and `clk_a`), which is
exactly where an RTL transform has something to bite on. Buffer first,
re-measure, then propose RTL. `tools/classify_path.py` is the router that
tells you which phase you are in, and
`docs/path-classification.md` has its validation table.

## Honest limits

- This is technology mapping plus a buffering pass. It is not place and
  route. Real fanout repair happens in OpenROAD `repair_design` with
  placement-aware loads, and the absolute numbers here would move under a
  real physical flow.
- `buffer -N 16` was run at one setting. No sweep was done, so nothing here
  claims 16 is optimal.
- The gains are reported per clock group under the frozen v2 SDC. Per
  `docs/measurement-methodology.md`, this flow is deterministic (0.000 on a
  self-swap null control) but not local, so group-to-group comparisons carry
  global-remapping effects.

## Reproduce

    bash experiments/buffering_control/run.sh

Builds A and B, times both, and prints the table above.
