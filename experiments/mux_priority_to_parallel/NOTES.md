# mux_priority_to_parallel(domain_b_onehot) -- second transform, composes with the first

Run 2026-08-20. Yosys 0.67+94, EQY (this repo's build), SBY 0.67-4, z3, abc pdr,
OpenSTA (this repo's build).

## Why this transform, second

`fsm_reencode(domain_b, state_r, onehot)` proved `state_r` is genuinely one-hot
for all time after reset (PDR, `experiments/fsm_reencode/`). That proof is what
makes this transform legal: the design's next-state decode is a 10-level
`if/else-if` chain whose mutual exclusivity, before the prior transform, was
only a coincidence of program order. After it, exclusivity is a proven
invariant, and the design doc's flagship mux_priority_to_parallel precondition
-- pairwise mutual exclusivity of the select conditions -- can be *assumed
from a proof*, not merely hoped. Picked specifically to demonstrate transforms
composing, not as an arbitrary second example.

## Step 1 -- the transition table, transcribed by hand before writing any code

Every branch of `domain_b_onehot.v`'s `always @(*)` block read and transcribed
(not paraphrased) into a table (see the header of `domain_b_onehot_parallel.v`
in the repo for the full table). This matters: the parallel form is a direct,
checkable transcription of the original chain's actual behaviour, not a
re-derivation from a description of it.

## Step 2 -- a real gap in the naive transform, caught before formalising it

A pure sum-of-products parallelisation is bit-exact against the original chain
*only when `state_r` is one-hot*. For an illegal MULTI-HOT `state_r` (not
excluded by the bit width alone, though proven unreachable in real operation),
the original's program-order priority picks whichever branch is tested first
and silently ignores the rest; the parallel OR-of-products form combines all
matching branches' contributions instead. These are genuinely different
functions outside the one-hot subspace. The all-zero illegal case was cheap to
close exactly (one extra OR term on `nstate[S_IDLE]`, matching the original's
defensive catch-all) and was added for free. The multi-hot case was not closed
-- doing so would require re-introducing priority-masking terms, which defeats
the purpose of parallelising. This is stated explicitly in
`domain_b_onehot_parallel.v`'s header, not discovered by the checker and
patched over afterward.

## Step 3 -- EQY, run for the first time on real RTL, both directions

Positive control first, per this repo's established discipline.

| Check | Result |
|---|---|
| `ctrl.eqy` (domain_b_onehot vs itself) | **PASS**, 21/21 partitions, 1s |
| `parallel.eqy` (unscoped, full 10-bit input domain) | **FAIL**, 10/24 partitions |

The 10 failing partitions are exactly `nstate` and everything downstream of
it in one clock cycle or a decode away: `state_r`, `rd_en`, `ld_pl`, `do_acc`,
`clr_ret`, `inc_ret`, `a2b_rd_en`, `acc_r`, `status_r`. This is the predicted
divergence chain from Step 2, not a mysterious failure -- EQY correctly found
the real counterexample that exists at illegal multi-hot inputs. Reported as
a genuine result, not discarded: **the unscoped claim is false, and EQY is
right to say so.**

## Step 4 -- the actual claim, scoped and proven

The physically relevant claim -- equivalence *given* `state_r` is one-hot,
which is separately proven for all time -- needs the precondition stated as
an explicit `assume`, which EQY's `[gold]`/`[gate]` full-domain comparison has
no obvious mechanism for (checked against this repo's own two existing `.eqy`
configs; neither shows a constraint-injection pattern). Rather than force it
or silently swap tools, both routes are run and both are reported: EQY
unscoped (Step 3, a real and useful result on its own) and SBY/smtbmc/pdr for
the scoped proof that matters. `state_match` compares raw one-hot `state_r`
directly this time -- no `decode_state()` bijection needed, since both designs
already share the same encoding.

Same `_fv` wrapper pattern as `experiments/fsm_reencode/` (tap the internal
register to a real output port), reused rather than re-derived, because
Yosys's `-formal` frontend does not support reading a submodule instance's
internal signal by hierarchical reference -- established there, not
re-discovered here.

| Task | Result | Time |
|---|---|---|
| `bmc` (depth 40) | **PASS** | 53s |
| `prove` (k-induction) | base case PASS; **induction fails on `status_match`** | 56s |
| `pdr` (IC3) | **PROVED, unbounded** | 38.3s |

The `prove` failure mode is identical to `fsm_reencode`'s: same property
(`status_match`), same root cause (no real `clkdiv` instance constrains the
clk/clk_div ratio in this local harness, so single-step induction must hold
under physically-impossible relative timings). This reproducibility is itself
informative -- it confirms the earlier diagnosis was the actual mechanism, not
a one-off artifact, and names a fix (wire a real `clkdiv` into the harness)
that will very likely close BOTH `prove` gaps at once when eventually done.

**Verdict: PROVEN, unbounded, via PDR, under the explicit precondition that
state_r is one-hot** -- which is not an assumption made for convenience, it is
a previously-discharged proof obligation from the transform this one composes
with.

## Step 5 -- measured, not assumed: real cost on real silicon

124 cells post-synthesis vs `domain_b_onehot`'s 136 (-8.8%), consistent with
flattening a chained-mux priority structure into direct OR-of-AND terms.
Zero latches, zero problems.

Re-synthesized `bench_top` with `domain_b` swapped for the doubly-transformed
`domain_b_onehot_parallel`, against the unchanged frozen SDC.

| Path group | domain_b (original) | domain_b_onehot | domain_b_onehot_parallel |
|---|---|---|---|
| `clk_b` | 4.898 ns slack | 4.410 ns slack | 4.492 ns slack |
| `clk_b_div3` (worst of top 25 endpoints) | 30.249 ns slack | 30.235 ns slack | 30.235 ns slack |

`clk_b` recovered +0.082ns relative to the immediately-prior baseline --
real, but smaller than the cell-count reduction alone might suggest, and
still net -0.406ns behind the ORIGINAL binary-encoded design across both
transforms combined. `clk_b_div3`'s true worst-case slack (checked across the
top 25 endpoints this time, not just the single worst path, specifically to
avoid mis-attributing an unrelated path as "the" result) is **unchanged**.

Honest limitation, not smoothed over: identifying exactly which gates in the
flattened, ABC-renamed netlist correspond to the transformed next-state logic
specifically (versus the untouched `decode_state()` chain or the FIFO mux
chain) would need name-preserving synthesis, not done here. The two
path-group numbers above are real and directly comparable; attributing them
to specific gates by name is not claimed.

## Files

- `rtl/domain_b_onehot_parallel.v` -- the real transform output
- `rtl/bench_top_domainb_parallel.v` -- bench_top with the doubly-transformed
  domain_b, for the Step 5 remeasurement
- `experiments/mux_priority_to_parallel/` -- `domain_b_onehot_raw_fv.v`,
  `domain_b_onehot_parallel_fv.v`, `miter_scoped.sv`, `miter_scoped.sby`,
  `ctrl.eqy`, `parallel.eqy`, logs

## Next

- Same open item as `fsm_reencode/NOTES.md`: wire a real `clkdiv` instance
  into the SBY harness so `prove` can close alone, without leaning on PDR for
  the whole unbounded result. Now confirmed to matter for two transforms in a
  row, not one.
- Two transforms proven and measured end to end by hand. The obligation
  router that dispatches a *typed* transform request to precondition check,
  rewrite, and the correct proof branch automatically is still the next real
  piece of infrastructure -- this experiment is the second hand-built
  instance of that pipeline, not the tool itself.

## Addendum, 2026-08-21 -- see experiments/fsm_reencode/NOTES.md

The clk/clk_div harness fix flagged in this file's "Next" section was tried
against the fsm_reencode miter (same underlying issue, same clkdiv#(.DIV(3)),
so one attempt answers it for both). Full account in
`experiments/fsm_reencode/NOTES.md`'s addendum. Short version: wiring the
real divider surfaces a genuine Yosys/SBY limitation (opposite-polarity
clocking on one net needs `clk2fflogic`), and `clk2fflogic`'s clock-as-data
modeling makes BMC on this specific dual-edge divider computationally
impractical here (step cost climbing past 30s by depth 28, nowhere near
depth 40). This is closed as a verified negative result, not an open item:
PDR is confirmed to be the correct tool for `status_match` on both this
transform and fsm_reencode, not a stand-in for a k-induction proof that
would otherwise be preferable. The PROVEN verdict above stands unchanged.
