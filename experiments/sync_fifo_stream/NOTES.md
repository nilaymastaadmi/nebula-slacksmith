# pipeline_cut_elastic(sync_fifo): branch 3, first real RTL, plus a vacuity gap found and fixed

Run 2026-08-27. Yosys 0.67+94, SBY 0.67-4, z3, abc pdr, iverilog. Uses `tools/run_proof.py`.

## Starting point: uncommitted work found in the working tree

`rtl/sync_fifo.v` and `rtl/sync_fifo_pipelined.v` existed, untracked, when this
session resumed. Not written by this session. Read in full, traced by hand
(not just read), and verified correct before building anything on top of it.
Design choice: single clock domain, deliberately, separating the elastic-
interface question from the CDC question `async_fifo.v` already answers.
2 problems, catches:
1. An earlier overflow-register design was abandoned for a real ordering
   hazard: a new write could claim a freed core slot before an older
   overflow item was promoted, breaking FIFO order.
2. A bug found by simulation, not assumed: `rempty_core_r` must update every
   cycle, unconditionally, or a core that never pulled anything can never
   leave empty. Independently reproduced below, exactly.

## The transform

`sync_fifo_pipelined`: 1 extra word of capacity (DEPTH+1, not DEPTH), via an
output register with `s2_ready = ~rdata_valid_r | rinc` forwarding. Reuses
`experiments/vr_miter/mac_vr_opt.v`'s own two-stage forward-flow mechanism,
not re-derived.

Verified by hand: the `rbin_core_nxt` formula's `+1` term uses the exact
same `s2_ready & core_avail` condition that gates the real register update,
so the look-ahead value always matches what the register becomes. Correct.

Elaborates clean: 171 cells (`sync_fifo`) vs 187 (`sync_fifo_pipelined`),
16 more for the output register plus forward logic. 0 latches, both.

## Why branch 3, not a k-padded miter

Real elastic interface: `wfull`/`rempty` are genuine back-pressure signals,
not decoration. `sync_fifo_pipelined` has strictly more capacity, so a
write `sync_fifo` would reject can be accepted by the pipelined version.
Feeding both designs the same raw `winc` would let their accepted-write
sequences diverge, which is not a transform bug, it is a broken test setup.
Fixed with a lockstep environment, reused from `vr_miter`: `winc_real =
winc_raw && !ref_wfull && !opt_wfull`. `rinc` stays shared and unconstrained,
matching `vr_miter`'s own `out_ready` handling exactly.

## Proof, 3 engines

| Task | Result | Time |
|---|---|---|
| `bmc` (depth 40) | TIMEOUT, not a verdict | stopped at 100-200s, per-step cost climbing (step 11: 1s, step 17: 60s+) |
| `pdr` | PROVEN, unbounded | 8-71s across 3 runs (real variance, not a bug, see below) |

`bmc`'s slowdown is a different signature than every prior multiplier case
in this project: no multiplier exists here at all. 2 independent FIFOs with
wraparound pointers plus the `anyconst` symbolic index plus 2 transaction
counters is a state space BMC unrolling scales badly on. Known, separate
class of hardness from arithmetic. `pdr` closes it regardless.

## The vacuity gap: found by mutation testing, not assumed safe

This project's own `vr_miter/NOTES.md` said, on day one: "worth recording:
this was a bug in the checker, not the design... argument for mutation-
testing the verifier itself before trusting any number it produces." That
mutation test was never actually run, on either the toy proof or this one,
until now.

Reconstructed the exact documented `sync_fifo_pipelined` bug (`rempty_core_r`
gated by `if (core_avail)` instead of updated unconditionally) as a mutant.
2 attempts: the first mutant used the wrong guard condition
(misread the original comment). The second, checked against the comment
text directly, matches exactly.

Simulated first, independently, before touching the formal tool:
`rempty` stays stuck at 1 forever after the very first write. 2 words
written, 0 ever read out. Confirmed, not assumed.

Ran the stream-equivalence proof against this mutant. **PDR reported
PROVEN, in 0 seconds, for a design that deadlocks and never produces a
single correct output.**

Root cause: `stream_match` only asserts once `ref_got && opt_got` are both
true. A design that never completes any transaction never triggers the
assert. Vacuously true forever. This gap is structural to the stream-
equivalence technique itself wherever a property is gated behind a
completion flag, which is every branch-3 proof by construction.

Fixed with a `cover` statement (SVA syntax on this Yosys build:
`cover property (expr)`, not bare `cover(expr)`, found by reading the real
parser error): `cover_reachable: cover property (ref_got && opt_got);`.
`cover` proves the guard is reachable, which `assert` alone cannot.

Validated the fix distinguishes real from broken, not just always failing:

| Design | `cover` result |
|---|---|
| Mutant (documented deadlock bug) | **UNREACHABLE** |
| Real `sync_fifo_pipelined` | **REACHED**, 0s |

`tools/run_proof.py` now supports `cover` as a 4th task, with inverted
polarity handled explicitly (UNREACHABLE is the bad outcome here, opposite
of `bmc`/`pdr`'s FAIL), and the summary line flags it specifically: any
PROVEN/PASS alongside an UNREACHABLE cover is called out as untrustworthy,
not silently reported as a clean pass.

## Retroactive check on the toy proof

Added the same `cover` statement to `experiments/vr_miter/miter_vr_stream.sv`
and ran it. **REACHED, 0s.** The original day-one PROVED result was
correct, not vacuous. But it was correct because `mac_vr_opt` happens to
work, not because the method checked for it. The gap existed from day one
and never produced a wrong answer only because nothing was ever broken
enough to expose it, until this session deliberately built something that
was.

## Verdict

`pipeline_cut_elastic(sync_fifo)`: PROVEN, unbounded, via PDR, confirmed
non-vacuous via `cover`. First branch-3 result on real RTL. 4 of 4 obligation
branches from the transform library design doc now have a real-RTL proof.

## Files

- `rtl/sync_fifo.v`, `rtl/sync_fifo_pipelined.v` -- pre-existing, verified
  and built on, not duplicated
- `experiments/sync_fifo_stream/` -- `miter_sync_fifo_stream.sv`, `.sby`,
  the mutant and its testbench, logs
- `tools/run_proof.py` -- `cover` task support added
- `experiments/vr_miter/miter_vr_stream.sv` -- retroactive `cover` statement added

## Next

- `remeasure.py` does not apply here directly: `sync_fifo` is not yet wired
  into `bench_top`. If it replaces one of the 3 FIFO crossings there later,
  remeasure it the same way as every other transform.
- Every future branch-3 proof needs `cover` from the start, not added after
  the fact. Consider making `run_proof.py` warn, not just support, when a
  stream-equivalence-shaped miter (a `_got`-gated assert) has no matching
  `cover` in the same file.
