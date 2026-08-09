# valid/ready miter — RESULT: the k-padded obligation is unsound under back-pressure

Run 9 Aug 2026. Yosys 0.33, z3 4.8.12. Depth 20.

## The question

`toy_miter/` proved a k-padded miter works on a **rigid** interface. Does the same
obligation work when the interface has valid/ready back-pressure?

**No. And that is the result.**

## Setup

`mac_vr_ref` (1 stage) and `mac_vr_opt` (2 stages, multiply then add), both with
full valid/ready handshaking and back-pressure. The two are genuinely
**stream-equivalent**: the same sequence of accepted inputs produces the same
sequence of emitted output values. Only the timing differs.

Two obligations were pointed at the identical design pair:

- **A — `miter_vr_naive.sv`**: the k-padded miter from `toy_miter/`. Asserts
  `opt.out_valid == delay_K(ref.out_valid)` and matching data.
- **B — `miter_vr_stream.sv`**: stream equivalence. Both designs fed in lockstep
  (a transfer occurs only when both are ready, so input sequences are identical);
  output transactions counted independently; an `anyconst` index `nsel` picks an
  arbitrary transaction; each side latches its `nsel`-th output; the two must match.

## Verdicts

| Obligation | W | BMC(20) | k-induction |
|---|---|---|---|
| **A — k-padded (wrong)** | 3 | **FAILED** (0s) | FAILED (0s) |
| **B — stream-equiv (right)** | 3 | **PASSED** (136s) | FAILED (0s) |
| **B — stream-equiv (right)** | 4 | **PASSED** (194s) | FAILED (0s) |

Reported as three outcomes, not two:

- **A: REFUTED**, with counterexample (`work/naive_cex.vcd`).
- **B: PROVED BOUNDED** to depth 20.
- **B unbounded: UNRESOLVED** — see below. Not a pass.

## What the counterexample says

The first assertion to break is **`opt_ov == ref_ov_pipe`** — the *valid
alignment*, at `miter_vr_naive.sv:74`. Not the data comparison.

That is the cleanest possible statement of the finding: under back-pressure the
two designs' output-valid patterns diverge immediately, because they hold
different numbers of in-flight transactions and drain at different rates. There
is no fixed cycle offset to compare against. The obligation is ill-posed before
you ever get to comparing values.

**A tool that emits a k-padded obligation for a valid/ready interface reports a
correct transform as broken.** That is a false negative, and it is exactly the
failure mode the two-branch obligation generator exists to prevent:

```
rigid interface        -> k-padded miter        (toy_miter/, proved unbounded)
valid/ready interface  -> stream equivalence    (here, proved bounded)
```

## Why induction fails on B, and why that is honest rather than alarming

k-induction fails **in 0 seconds** with `nsel = 0`. The induction step begins from
an *arbitrary* state, so it is free to start with `ref_got && opt_got` already
set and `ref_lat != opt_lat` — a state unreachable from reset, but induction
cannot know that. `initial assume(rst)` constrains only the BMC base case.

Closing it needs a strengthening invariant relating the two pipelines' in-flight
contents to the latched values. That is real work and is not done here.

Reported as **unresolved**. It is not a design bug, and it is not a pass.

## Second confirmation of the solver-hardness finding

At the original **W=8**, BMC on B reached step 18 of 20 and then timed out at
400s — roughly **90 seconds per step**, all of it in the two 8-bit multipliers.
At W=3 the same property proves in 136s total; at W=4, 194s.

The multiplier has nothing to do with the handshake question. Shrinking the
datapath isolated the property from solver hardness and turned an unresolved run
into a clean verdict. **Separate the thing you are testing from the thing that is
hard to solve** — on the real benchmark that means not discovering AES-128
timeouts inside an unrelated experiment.

Note also the asymmetry, which is worth a slide: **A refuted in 0s; B proved in
136s.** Finding a bug is fast, proving absence is slow. Budget accordingly.

## Harness bug found and fixed

The transaction counters were 4 bits, so within depth 20 they could wrap and
re-latch a later transaction under the same index, silently comparing the wrong
pair. Fixed by guarding the latch with `&& !got`.

Worth recording: this was a bug in the *checker*, not the design, and it would
have produced a meaningless result rather than an obvious failure. It is the
argument for mutation-testing the verifier itself (MCY) before trusting any
number it produces.

## Files

- `mac_vr_ref.v`, `mac_vr_opt.v` — stream-equivalent pair, 1 vs 2 stages
- `miter_vr_naive.sv` — the wrong obligation, kept deliberately
- `miter_vr_stream.sv` — the right one
- `work/naive_cex.vcd` — counterexample trace
- `work/w*_*.log` — solver logs for every row in the table

## Next

1. Discharge B unbounded with a strengthening invariant, or record it as
   permanently bounded and say so.
2. Automatic interface classification — detect valid/ready from the port list and
   protocol structure, and pick the obligation without being told. That is the
   two-branch generator, and this experiment is its motivation.
3. Confirm EQY rejects the rigid K=1 pair.
