# One-hot invariant, formally discharged (audit finding F1 closed)

Run 2026-08-31. Yosys 0.67+94, SBY 0.67-4, z3, abc pdr, via tools/run_proof.py.

## Why this exists

The 2026-08-31 audit found claim-to-evidence drift in the composition chain between the
first two transforms. Three places (mux_priority_to_parallel/NOTES.md, the header of
rtl/domain_b_onehot_parallel.v, and commit 043fe9b's message) said fsm_reencode "proved
state_r is genuinely one-hot for all time". It did not. That proof established
decoded-state correspondence through decode_state(), a priority encoder that maps many
multi-hot states onto the same output as legal one-hot states, so it structurally cannot
distinguish one-hot from multi-hot. One-hotness rested on a syntactic construction
argument (reset sets exactly one bit; every next-state assignment sets exactly one bit),
which is a good argument and is not a discharged proof. mux_priority's scoped equivalence
proof ASSUMES one-hot on both designs each cycle, so the chain had one undischarged link.

## The proof

`onehot_check.sv`: both designs instantiated independently, inputs free (over-general,
therefore sound for the real system), manual-form one-hot asserted on the raw 10-bit
state tap of each, every clk_div cycle after reset.

| Task | Result | Time |
|---|---|---|
| bmc (depth 40) | PASS | 6s |
| prove (k-induction) | **PROVEN, k-induction closed** | ~8s |
| pdr | PROVEN | 0s |

Worth noting: this is the first property in this project that single-step k-induction
closes on its own (4 prior proofs all needed PDR). That is not luck, it is the shape of
the property: one-hotness is naturally inductive, since from any one-hot state exactly
one branch of the next-state logic fires and every branch writes exactly one bit. The
properties k-induction failed on earlier all related two designs or two clock domains;
this one is a single-design invariant.

## What this changes

The mux_priority scoped proof's one-hot assumptions are now backed by a discharged,
unbounded proof for both the assumed designs, not by a construction argument. The three
drifted wordings are corrected in the same commit as this file. The commit message of
043fe9b cannot be edited; this file is its correction of record.

## Reproduce

    python3 tools/run_proof.py --top onehot_check \
      --file domain_b_onehot_raw_fv.v --file domain_b_onehot_parallel_fv.v \
      --file decode_state.vh --file onehot_check.sv \
      --workdir <scratch> --tasks bmc,prove,pdr

All source files are bundled in this directory, so it reproduces from a cold clone
(the F4 lesson, applied at creation time rather than retrofitted).
