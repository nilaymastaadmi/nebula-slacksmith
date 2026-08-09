# Toy miter — RESULT: the thesis has a working spine ✅

Run 9 Aug 2026. Yosys 0.33, z3 4.8.12, `yosys-smtbmc`, `yosys-abc`. No sby needed.

## What was tested

`mac_ref` (latency 1: combinational `(a*b)+c`, registered once) vs `mac_opt`
(latency 2: multiply registered in stage 1, add in stage 2, `c` delayed to stay
aligned). That is the textbook pipelining transform — one extra cycle bought for
a shorter critical path — and it is exactly what `abc cec` cannot check.

Obligation: `opt.y[t+K] == ref.y[t]`, realised as a K-register-padded miter with
a `primed` guard for reset alignment.

## Verdict matrix

| Case | BMC(24) | k-induction | Expected | |
|---|---|---|---|---|
| K=0, claims latency preserved | FAILED | FAILED | fail | ✅ |
| **K=1, correct** | **PASSED** | **PASSED** | pass | ✅ |
| K=2, wrong latency claim | FAILED | FAILED | fail | ✅ |
| K=1, arithmetic mutated (`+`→`-`) | FAILED | FAILED | fail | ✅ |

**Two things this establishes.**

1. **The obligation discharges unbounded, not just bounded.** k-induction
   reported *"Temporal induction successful"* — this is a proof for all time, not
   a bounded check. I expected to need a strengthening invariant because the
   induction step starts from an arbitrary state where `initial assume(rst)`
   does not apply. For this design it converged without one. Do not assume that
   holds on RV32I; budget for needing invariants there.
2. **The proof is not vacuous.** Three mutants all fail, including the two that
   matter most: a *wrong latency claim* (K=0 and K=2) and a *broken datapath*.
   A miter that passes everything proves nothing; this one discriminates.

## ⚠️ The finding that matters for your benchmark

**PDR hung for >440s on an 8-bit multiplier. SMT solved the same property in
under a second.**

Both engines, same design, same property:

| Engine | Result |
|---|---|
| `yosys-smtbmc -s z3` (BMC, depth 24) | PASSED, <1s |
| `yosys-smtbmc -s z3 -i` (k-induction) | PASSED, <1s |
| `yosys-abc … pdr` (IC3/PDR on the AIG) | **killed at 440s, no answer** |

The reason is structural: SMT reasons about multiplication in the bit-vector
theory, while AIG-based PDR bit-blasts it into a gate netlist where the
multiplier becomes a wall. **This is the AES-128 hardness problem in miniature,
found on day one on an 8-bit toy.**

Consequences for the plan:
- Engine portfolio racing is not a nice-to-have, it is load-bearing. Run
  smtbmc-BMC, smtbmc-induction, EQY and abc-pdr in parallel; take the first
  answer. A day of plumbing.
- Prefer SMT-backed engines for anything with arithmetic in the cone.
- Your AES-128 block will be the case that times out. Say so in the report
  before a judge finds it, and report it as `unresolved`, never as passed.
- **Three-way outcome reporting is mandatory:** proved / refuted-with-counterexample
  / unresolved. A timeout folded into "passed" is the one thing that will
  destroy credibility with this panel.

## Code note

`K=0` originally would not elaborate — `reg [DW-1:0] ref_pipe [0:K-1]` becomes
`[0:-1]`. Now guarded by a `generate` that degenerates to a wire. K=0 matters:
it is the latency-preserving control case and the branch that should route to
EQY rather than to this miter.

## What is assumed, not proved

State these explicitly in the report; the distinction is the project.

1. **Reset alignment.** The `primed` guard holds the assertion off for LAT cycles
   after reset. The property is trivially false before that.
2. **Rigid interface.** `mac_ref`/`mac_opt` have no valid/ready handshake and
   never stall, so a fixed K-cycle offset is sound. **On a back-pressured
   interface it is not** — that needs stream equivalence, and this miter would be
   the wrong obligation. Interface-aware branching between the two is the deepest
   idea available to SlackSmith.

## Files

- `mac_ref.v`, `mac_opt.v` — the design pair
- `miter.sv` — parameterised K-padded miter with the reset-alignment guard
- `run.sh` — three engines, three separate verdicts (no sby required)
- `miter.sby` — same experiment for a machine that has sby
- `work/` — generated smt2/aiger and per-case logs

## Reproduce

```bash
apt-get install -y yosys z3      # yosys ships yosys-smtbmc and yosys-abc
./run.sh 24
```

## Next

1. Repeat on a **valid/ready** pair — confirm the k-padded miter gives a false
   negative under back-pressure. That failure is a *result*, and it motivates the
   two-branch obligation generator.
2. Repeat with a **deeper pipeline** (K=2,3) on something without a multiplier,
   to isolate latency scaling from solver hardness.
3. Confirm **EQY rejects the K=1 pair** — you assert it cannot express a latency
   difference; "we ran it, here is the error" beats a citation.
4. Then start the corpus for the four-checker matrix.
