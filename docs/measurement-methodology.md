# Measurement methodology: three findings that change how timing is reported

Run 2026-08-31, on the v2 benchmark (55,413 cells). Every number below was
produced by running the flow, not by reading it.

## 1. A single library cell was worth 4.83 ns of pure artifact

The first critical-path report on v2 showed 33.0 ns of arrival against an
8 ns period, and 19.5 ns of that (59%) sat in **two cells**:

    12.391 ns  u_rv32_a/_3480_/X   sky130_fd_sc_hd__lpflow_isobufsrc_1
     7.072 ns  u_rv32_a/u_core/_14907_/Y   sky130_fd_sc_hd__clkinv_1

That is not logic depth, so it was investigated before being reported as a
timing result. `abc -D 8000` (an explicit 8 ns target) produced a
**byte-identical netlist**, ruling out mapping effort as the cause.

`sky130_fd_sc_hd__lpflow_*` are low-power isolation and power-gating cells.
They are not general logic, and standard sky130 flows (OpenLane) exclude
them by default. ABC was selecting one on area cost and OpenSTA was
correctly reporting its very poor delay under load. Excluding the `lpflow`
and `probe` families (37 cells, derived from the liberty at run time, not
hardcoded):

| | WNS |
|---|---|
| before | -27.37 ns |
| after | -22.54 ns |
| **delta** | **4.83 ns, from zero RTL change** |

The 12.391 ns cell disappears entirely. `tools/remeasure.py` now applies
this exclusion on every synthesis it runs, baseline and variant alike.

**Reporting consequence:** any timing number produced before 2026-08-31
carries up to ~4.8 ns of this artifact. The v1 numbers in earlier NOTES are
internally consistent (baseline and variant were mapped identically, so
their *deltas* are unaffected), but their absolute values are not comparable
with post-fix numbers.

## 2. The measurement tool has a zero noise floor (null control)

Before attributing any delta to a transform, the obvious control was run:
swap a module for **itself** and measure.

    remeasure.py --swap-instance u_domain_b --swap-module domain_b \
                 --replace domain_b.v:domain_b.v

| clock | baseline | variant | delta |
|---|---|---|---|
| clk_a | -25.287 | -25.287 | **+0.000** |
| clk_b | -18.490 | -18.490 | **+0.000** |
| clk_b_div3 | 30.249 | 30.249 | **+0.000** |

Synthesis and STA are fully deterministic here, and the tool contributes no
measurement noise. Every nonzero delta it reports is a real, reproducible
consequence of the RTL change.

## 3. Local RTL changes have non-local timing effects, and attribution must respect that

Swapping `domain_b` for `domain_b_onehot` (a change confined entirely to
domain B) moved a path group it does not touch:

| clock | baseline | variant | delta |
|---|---|---|---|
| clk_a | -25.287 | -23.889 | **+1.398** |
| clk_b | -18.490 | -18.490 | +0.000 |
| clk_b_div3 | 30.249 | 30.235 | -0.014 |

Given finding 2, the +1.398 ns on `clk_a` is not noise. It is a genuine,
deterministic side effect: changing any module perturbs ABC's global
technology mapping, and unrelated path groups move as a result. On a
3.6K-cell design this was invisible; at 55K it is 1.4 ns.

Note also that `clk_b_div3`'s -0.014 reproduces the v1 measurement of this
same transform **exactly**, which is a strong independent check that the
transform's own local effect is stable across a 15x change in design size.

**Reporting rule adopted from here on:** a transform's timing effect is the
delta in the path group(s) it actually touches. Movement in other groups is
reported separately and labelled as global-remapping side effect, never
folded into the transform's claimed benefit. Claiming the +1.398 ns on
`clk_a` as a win for an FSM re-encoding in domain B would be false, and it
is exactly the kind of number that collapses under one question.

## Standing limitation, disclosed

After the `lpflow` fix, a 5.660 ns single-cell delay remains on a
`sky130_fd_sc_hd__clkinv_1` in the same region. That is high fanout with no
buffer-insertion pass: this flow stops at technology mapping and does not
run a repair or P&R step (OpenROAD `repair_design` is the standard answer).
So the reported violations are an upper bound on what a complete flow would
show, and the benchmark's absolute WNS should be read with that in mind. The
genuine logic-depth component of the worst path, excluding that one cell, is
approximately 22.7 ns against an 8 ns target: still a real, large, structural
violation, and the honest target for a pipelining transform.
