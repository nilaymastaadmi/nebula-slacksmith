# pipeline_cut_rigid(domain_a): first Tier 3 transform, on real RTL

Run 2026-08-21. Yosys 0.67+94, SBY 0.67-4, z3, abc pdr, OpenSTA (this repo's build).

## Why this transform, and why now rather than at the scheduled date

The abstract's headline claim -- latency-*changing* transforms with an
automatically generated proof -- had, until this experiment, only ever been
shown on the toy MAC from day one of the project. Both prior real-RTL
transforms (`fsm_reencode`, `mux_priority_to_parallel`) are k=0,
latency-preserving. Went looking for a genuine k>0 target in the current
benchmark and found the honest problem: the skeleton is deliberately lean
(per its own build spec, "don't pad"), and every arithmetic operation in it
is either already registered (domain_a's own multiply/scale front end) or has
real feedback (the accumulator, the FSM state, the timer's counter) --
explicitly ineligible for the simple k-padded-miter treatment per the
transform library design doc ("if the pipelined block's output feeds back to
its own input, adding k cycles does not shift the output, it changes the
machine"). Rather than wait until 9 Sept to discover this gap under deadline
pressure, addressed it now, 19 days early.

## Step 1 -- growing the design honestly, for a stated reason

Extended `domain_a`'s multiply-scale front end with a saturating clamp
(`(scaled_r > 16'hFF00) ? 16'hFF00 : scaled_r`) between `scaled_r` and where
it feeds the accumulator. This is standard, defensible DSP/MAC practice
(saturating output), not padding for a cell-count target -- it exists
specifically because it is a genuine, feed-forward (no self-loop),
currently-unpipelined combinational operation, which the unmodified benchmark
did not otherwise contain.

Two new files, mirroring the module's own existing idiom rather than
introducing a new one:
- `domain_a_clamped_comb.v` -- clamp computed combinationally, same cycle as
  `scaled_r`, feeding `cap_r` with no added latency. This is the k=0
  reference for the obligation below, not itself "the transform."
- `domain_a_clamped_pipelined.v` -- the clamp compare registered
  (`clamped_r`, `clamp_valid_r`), one clk cycle after `scaled_r`, exactly
  mirroring the existing `valid_r` -> `prod_valid_r` pattern already in the
  module. This is the actual `pipeline_cut_rigid` output.

Everything from `cap_r` onward (the accumulate loop, `cnt_r`/`ctrl_r` window
logic, `result_r`, `a2b_wr_en`/`wdata`) is byte-for-byte identical to
`domain_a.v` in both files -- the transform is local to the clk-domain front
end and touches neither FIFO protocol.

Both synthesize clean: 52 -> 69 `$_DFF_PN0_` cells, exactly the 17 bits added
(16-bit `clamped_r` + 1-bit `clamp_valid_r`), everything else identical. Zero
latches, zero problems.

## Step 2 -- scoping the obligation to avoid a real cross-domain trap

`mac_result` and `a2b_wr_en`/`wdata` live in the `clk_div` domain. A 1-cycle
shift in the `clk`-domain front end does not translate to a fixed,
guessable number of `clk_div` cycles at those outputs without assuming a
specific `clk`:`clk_div` phase relationship -- precisely the kind of
cross-domain guess this project has been careful not to make (see the SDC's
own documented reset-phase assumption for the same reason). Rather than
guess, the obligation is scoped to the one point where k=1 is unambiguous:
`clamped_w`/`clamped_r` and their paired valid signals, both still entirely
within the `clk` domain, before anything crosses to `clk_div`. Everything
downstream is identical logic between the two designs, so proving
equivalence up to this boundary is sufficient.

Precondition P1 (design doc): every path from the cut to any consumer
crosses it exactly once. Holds by construction here -- `clamped_r` has
exactly one consumer (`cap_r`), `clamp_valid_r` has exactly one consumer
(`cap_v_r`). Precondition P4 (rigid interface): `domain_a` has no
valid/ready handshake anywhere; `valid_in` is a one-way strobe, matching the
same lexical/structural criteria the interface classifier
(`experiments/classify/`) already established for distinguishing rigid from
elastic.

## Step 3 -- the proof, and the first real difficulty this project has hit

Reused the exact `toy_miter/miter.sv` k-padding technique from day one of
the project -- pad the reference's outputs with K=1 matched registers,
assert the optimized design's outputs equal the padded reference, once
primed. First time this recipe has been run on real RTL rather than the toy
case it was originally proven on.

| Task | Result | Time |
|---|---|---|
| `bmc` (depth 40) | **incomplete, stopped deliberately** -- per-step cost climbed from <1s to ~60s by step 9, clearly not reaching depth 40 in reasonable time | stopped at ~3 min |
| `prove` (k-induction) | induction fails on `clamped_match` at step 0 (~1 min); basecase itself also slow, stopped before confirming | stopped at 150s |
| `pdr` (IC3) | **PROVED, unbounded** | 174.4s (~2m55s) |

This is the first proof in the project whose cone includes a real
multiplier (`sample_r * coeff_r`), and it reproduces -- almost exactly,
but with the engines' roles REVERSED -- the finding the project's own README
predicted on day one from a toy multiplier: *"PDR hung >440s ... SMT proved
the same property in under a second."* Here, SMT/BMC is the one that
struggled (climbing step cost, no realistic path to depth 40) and PDR is
what closed it, in under 3 minutes. The lesson from the toy case does not
generalize as a fixed ordering -- which engine wins on a multiplier-bearing
property is not predictable in advance, which is exactly why this project's
own stated principle is "engine portfolio racing is load-bearing, not
optional," not "always use engine X for arithmetic."

`prove`'s induction failure has a different, and better-understood, root
cause than the previous two transforms' `status_match` failures (which were
diagnosed and confirmed to be a genuine `clk`/`clk_div` cross-domain
modeling gap -- see `experiments/fsm_reencode/NOTES.md`'s addendum). This
proof is entirely within the `clk` domain; there is no cross-clock
assertion here at all. The more likely explanation is textbook: a
latency-shifted comparison (`opt == padded(ref)`) gives single-step
induction nothing to lean on beyond the property itself -- there is no
separate same-cycle auxiliary lemma here the way `state_inv` was for
`fsm_reencode`, so the induction has to somehow re-derive the padding
register's own correctness from a single step, which a first-order
induction step is not well suited to. This is a known, classical difficulty
with Burch-Dill-style latency-shifted equivalence proofs, not a new gap
specific to this design. **Verdict: PROVEN, unbounded, via PDR.**

## Step 4 -- measured, not assumed, and the result matters

Re-synthesized `bench_top` with `domain_a` swapped for
`domain_a_clamped_pipelined`, against the unchanged frozen SDC. Baseline
re-confirmed fresh (domain_a had not been touched by any prior transform)
rather than trusted from memory.

| Path group | domain_a (original) | domain_a_clamped_pipelined | delta |
|---|---|---|---|
| `clk_a` | 3.932 ns slack | 3.838 ns slack | **-0.094 ns** |
| `clk_a_div2` | 5.699 ns slack | 5.134 ns slack | **-0.565 ns** |

**The transform is formally proven correct and measurably makes the reported
worst-case timing slightly worse on both groups it touches, not better.**
Not a contradiction: `clk_a`'s worst path runs through a chain unrelated to
the multiply/scale/clamp datapath entirely (a different 16-cell chain,
present in the original baseline too). Pipelining an operation that was
never on the reported critical path adds real flops (fanout, routing,
mapping pressure) without buying back anything the timing report actually
cared about. `clk_a_div2` moved more (-0.565ns), consistent with the new
register pair sitting directly in the path feeding the accumulate loop, but
still a cost, not a win, since the accumulate loop's own logic was not the
bottleneck either.

This is reported prominently, not buried, because it is the clearest
evidence in this project so far that the measurement pipeline is honest
rather than flattering: proof and profit are independent questions, and this
transform answers only the first one. It also states plainly what an
eventual transform-*proposing* agent needs to do that this hand-built
experiment did not: check the timing report for where the actual critical
path is *before* proposing a cut, not merely find a legally eligible one.
A provably-correct transform in the wrong place is still the wrong
transform.

## Files

- `rtl/domain_a_clamped_comb.v`, `rtl/domain_a_clamped_pipelined.v` -- the
  real transform output and its k=0 reference
- `rtl/bench_top_domaina_pipelined.v` -- bench_top with domain_a swapped,
  for the Step 4 remeasurement
- `experiments/pipeline_cut_domain_a/` -- `domain_a_clamped_comb_fv.v`,
  `domain_a_clamped_pipelined_fv.v`, `miter_pipeline_domain_a.sv`,
  `miter.sby`, logs

## Next

- Three transforms now, three distinct engine-selection lessons: none of
  them "just worked" on the first honest attempt, and all three needed PDR
  specifically, for three different reasons (cross-domain clock modeling
  gap x2, latency-shifted induction difficulty x1). This is itself worth
  stating in the report as the actual empirical case for engine racing,
  replacing the toy-MAC prediction with three real, measured instances.
- The obligation router as general software remains the largest open gap.
  Three hand-built instances of propose -> precondition -> rewrite -> prove
  -> measure now exist as templates (one k=0/EQY, one k=0/scoped-SBY, one
  k=1/padded-SBY) covering three of the four routing branches from the
  design doc. Branch 3 (stream equivalence, elastic interfaces) is the one
  remaining untested on real RTL, and this benchmark's FIFOs are exactly
  where it would apply.
- This transform's own negative timing result suggests the next honest move
  is not another blind pipeline cut, but checking whether ANY real critical
  path in the current benchmark would actually benefit from pipelining --
  which the domain_a baseline measurement (the 16-cell chain dominating
  `clk_a`) already identifies as a candidate worth investigating on its own
  terms, rather than picking a target for demonstration purposes.
