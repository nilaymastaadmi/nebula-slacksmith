# fsm_reencode(domain_b, state_r, onehot) -- first real end-to-end transform

Run 2026-08-20. Yosys 0.67+94, SBY 0.67-4, OpenSTA (this repo's build), z3, abc pdr.

## Why

First transform run against the real benchmark rather than the toy MAC, and the
first test of branch 4 (mapped-state equivalence) from the design doc. FSM
re-encoding is one of the four organizer-named transform categories. Chosen
over a Tier-1/Tier-3 target because it directly answers a question the design
doc left open: does bare `dsec` need the encoding-bijection hint, or does it
cope unhinted at real (not toy) scale.

## Step 1 -- precondition check found a real problem

P2 ("state bits fan out only to next-state/output logic, not to a module
output") was checked mechanically, not by reading the RTL: a Yosys fanin-cone
selection (`select domain_b/status_r %ci*`) on the real `domain_b.v` confirms
`state_r` is in `status_r`'s fanin cone. `status_b[3:0]` exposes the raw
encoding today. Re-encoding as-is would silently change external behaviour --
correctly rejected by the precondition.

## Step 2 -- the fix, disclosed rather than hidden

`domain_b_onehot.v` re-encodes `state_r` to one-hot (4 bits -> 10), and
`status_r` is changed to re-derive the *original* binary value via a new
`decode_state()` priority encoder, so `status_b` is bit-exact against the
original despite the internal encoding change. `decode_state()` lives in one
place, `decode_state.vh`, included verbatim by the RTL and (via the `_fv`
formal wrappers) by the proof -- one function, two consumers, no drift.
Everything else in the module (payload_r, acc_r, lfsr_r, retry_r, b2c_r,
a2b_rd_en, b2c_ctrl) is untouched.

Elaborates and synthesizes clean: 136 cells vs the original 118 (+15%,
expected: 6 more state flops plus the decoder), zero latches, zero problems.

## Step 3 -- bare, unhinted checkers (does branch 4 earn its keep?)

Positive control first, per this repo's own established discipline
(`experiments/cec_check/`).

| Checker | control: domain_b vs itself | domain_b vs domain_b_onehot |
|---|---|---|
| `yosys-abc cec`  | equivalent, 0.05s | **cannot build the miter** (different latch counts) |
| `yosys-abc dsec` | equivalent, 0.07s | **NOT EQUIVALENT**, 0.08s |

Same qualitative signature as the toy MAC's latency-changing case (`cec` can't
even set up the comparison, `dsec` sets it up and correctly says no) but for a
genuinely different underlying reason -- encoding, not latency. `dsec`'s fast,
clean "no" answers the design doc's open question directly: **branch 4 is
necessary, not redundant with what an off-the-shelf checker already does**,
confirmed by measurement rather than assumed.

## Step 4 -- a methodology trap, caught before it produced a false result

The first attempt at the mapped-state miter referenced `u_opt.state_r` and
`u_opt.decode(...)` by hierarchical dot-path from the top-level miter module.
Yosys's `-formal` frontend does not support this: it silently treated
`u_opt.state_r` as an undeclared, undriven free wire (two warnings said so:
"implicitly declared", "used but has no driver"), and the very first BMC run
promptly failed -- against garbage, not against the real state. This is the
same class of near-miss the project's own `cec_check/NOTES.md` already warned
about ("check the instrument before trusting the measurement"). Fixed by
building `domain_b_fv.v` / `domain_b_onehot_fv.v`: exact copies of the real
RTL plus one added output port (`dbg_state`) that taps the internal state
register out to the top level, so the miter compares two ordinary wires with
no hierarchical reference at all. The real deliverable RTL (`domain_b.v`,
`domain_b_onehot.v`) is untouched by this; the `_fv` files exist only for the
formal harness.

## Step 5 -- the proof

Four properties: `state_inv` (the mapping bijection itself), `rd_en_match`,
`ctrl_match`, `status_match`. Three tasks, same convention as `toy_miter/`:

| Task | Result | Time |
|---|---|---|
| `bmc` (depth 40) | **PASS**, no counterexample | 2m29s |
| `prove` (k-induction) | base case PASS; **induction step FAILS on `status_match`** | 2m25s |
| `pdr` (IC3) | **PROVED, unbounded** | 35.7s |

Report all three, not just the best one. `prove`'s induction failure is a real
signal, not noise: `clk` and `clk_div` are both raw primary inputs to this
local harness with no declared ratio between them (no `clkdiv` instance feeds
it, unlike the real `bench_top`), so single-step induction has to hold under
*any* relative clk/clk_div timing, including physically-impossible ones the
real design never sees. `status_r` is a one-cycle-stale snapshot captured on
`clk`; an adversarial, unconstrained `clk_div` plausibly produces a torn
snapshot single-step induction can't rule out on its own. PDR does not need
this hand-supplied structure -- it discovers its own invariants -- and closes
completely. **Verdict: PROVEN, unbounded, via PDR.** The `prove` gap is left
here as a known limitation of this harness, not smoothed over: the fix, if
ever needed, is wiring a real `clkdiv` instance into the miter so the proof
reflects the true ratio-constrained relationship instead of an unconstrained
one.

## Step 6 -- measured, not assumed: what it costs on real silicon

Re-synthesized `bench_top` with `domain_b` swapped for the proven
`domain_b_onehot`, against the same frozen `sdc/bench_top.sdc`, no constraint
changes needed (identical port list).

| Path group | domain_b (binary) | domain_b_onehot | delta |
|---|---|---|---|
| `clk_b` (status_r, clk_div->clk) | 4.898 ns slack | 4.410 ns slack | **-0.488 ns** |
| `clk_b_div3` (FSM internal) | 30.249 ns slack | 30.235 ns slack | -0.014 ns |

Both still meet timing comfortably. The cost lands exactly where physics
predicts: `decode_state()`'s priority-encoder chain sits directly in
`status_r`'s fanin cone, which *is* the `clk_b` path group, and nowhere else
moved. This transform is proven correct and has a real, small, disclosed
cost -- not a free win. Consistent with the abstract's own commitment: report
measured deltas, including where they are small or negative.

## Files

- `rtl/domain_b_onehot.v`, `rtl/decode_state.vh` -- the real transform output
- `rtl/bench_top_domainb_onehot.v` -- bench_top with domain_b swapped, for
  the re-measurement in Step 6
- `experiments/fsm_reencode/` -- `domain_b_fv.v`, `domain_b_onehot_fv.v`,
  `miter_mapped.sv`, `miter.sby`, AIG export logs, sby run directories

## Next

- Wire a real `clkdiv` instance into the miter harness so `prove` can close
  without needing PDR to carry the whole proof (informative but not urgent --
  PDR already gives an unbounded result).
- This is one transform, one module, proven and measured end to end. The
  obligation router that dispatches a *typed* transform request to the right
  branch automatically (rather than me hand-building the miter and `.sby`
  file per transform) is still not written -- that is the next real piece of
  infrastructure, not this experiment repeated by hand five more times.

## Addendum, 2026-08-21 -- the harness fix was tried, and found intractable

Both this experiment's and `mux_priority_to_parallel`'s "Next" section flagged
the same open item: wire a real `clkdiv#(.DIV(3))` instance into the miter so
`clk_div` is derived from `clk` instead of taken as an independent free input,
on the theory that this would let single-step k-induction close `prove`
without needing PDR to carry the whole proof.

Tried directly, not assumed. Wiring in the real divider surfaces a genuine
Yosys/SBY limitation first: `clkdiv`'s odd-ratio branch uses both `posedge`
and `negedge` of the same `clk_in` net (that is its documented mechanism for
exact 50% duty on DIV=3), and SBY's default `prep` flow does not accept a
clock net used with opposite polarity across a design without `clk2fflogic`
-- it errors and says so explicitly.

Adding `clk2fflogic` (in the position Yosys formal practice expects, after
`prep`) does resolve that error and BMC begins making progress. But
`clk2fflogic` works by converting every flip-flop into an explicit two-state
model where the CLOCK ITSELF becomes free-toggling data rather than an
idealized edge -- and for a divider whose odd-ratio output needs multiple
real source-clock edges of both polarities to produce a single output
transition, this multiplies the state space far beyond what stayed tractable
here: BMC step cost grew from sub-second to ~30 seconds per step by depth 28
and was still climbing, on a trajectory nowhere near depth 40 in reasonable
time. Stopped deliberately rather than let it run unbounded; no orphaned
solver process was left behind (checked, killed the one transient match,
confirmed clean).

**Conclusion, and it is a real one, not a shrug**: the free-`clk_div`-input
harness used in both this experiment and `mux_priority_to_parallel` is more
general than the real system (it explores relative clock timings the actual
divided clock can never produce), which is exactly why single-step induction
could not close on `status_match` in either case. But the PRINCIPLED fix, as
implemented via `clk2fflogic`, is computationally impractical for this
specific divider's dual-edge mechanism with the tools available here. PDR is
therefore not a workaround standing in for a "real" k-induction proof that
was simply never attempted -- it is the correct tool for this property,
verified to be necessary rather than assumed to be. Both PROVEN verdicts
(this experiment and `mux_priority_to_parallel`) stand exactly as reported,
unbounded, via PDR.

Files from the attempt are not committed (the reverted `miter_mapped.sv` and
`miter.sby` in this directory are back to the versions that produced the
original PDR-proven results). If this is revisited, the likely productive
directions are: prove the divider's own output-timing property separately
and supply it as an assumption rather than deriving it structurally inside
the same induction, or accept PDR as the standing method for any property
that depends on a dual-edge generated clock and stop trying to force
single-step induction to close on it.
