# Existing equivalence checkers vs a latency-changing transform — measured

Run 9 Aug 2026. Yosys 0.33, `yosys-abc`, EQY (built from tag `yosys-0.47`), z3.

## Why

The submitted abstract asserts that `abc cec` "cannot see an added register" and
routes latency-changing transforms away from EQY. Until now that was an argument
from tool architecture. This runs it.

Design pair is the one from `toy_miter/`: `mac_ref` (latency 1) and `mac_opt`
(latency 2, `(a*b)+c` cut into two stages). **The transform is correct** — the
padded miter proves it under k-induction, unbounded.

## Results

Every checker was given a positive control first, so a FAIL means the checker
rejected a correct transform rather than the setup being broken.

| Checker | control: ref vs identical copy | ref vs opt (latency +1) |
|---|---|---|
| `yosys-abc cec` | **equivalent** ✓ | **cannot build the miter** |
| `yosys-abc dsec` | **equivalent** ✓ | **NOT EQUIVALENT** |
| **EQY** (`use sat`) | **PASS**, partition proved ✓ | **FAIL**, 1/1 partitions unproven |
| padded miter (SBY/smtbmc) | — | **PASSED, unbounded** (see `toy_miter/`) |

## The distinction that matters

All three existing checkers reject a correct transform, but **not for the same
reason**, and the difference is the interesting part:

- **`cec` cannot express the question.** It does not return "not equivalent"; it
  fails to construct the comparison at all:

  > `Networks have different number of latches.`
  > `Miter computation has failed.`

  Combinational EC matches state elements one-for-one. Add a pipeline register
  and the correspondence no longer exists, so there is nothing to compare. This
  is the precise form of the abstract's claim, and "cannot see an added register"
  is looser than what actually happens — **the comparison cannot be set up.**

- **`dsec` and EQY can express the question, and answer no.** `dsec` is
  sequential and tolerates differing latch counts (16 vs 48 here); EQY partitions
  the design and attacks each partition with SAT. Both set up a comparison and
  correctly report failure — because the two designs genuinely are *not*
  cycle-for-cycle equivalent. Neither has any notion of a latency offset.

So the failure mode is not "the tools are broken." It is that **none of them can
express equivalence modulo k cycles**, so a pipeline gated on any of them can
only ever reject a latency change. That is exactly why Dr. RTL forbids latency
changes by construction rather than trying and failing to verify them.

**This is the evidence for the routing decision in the abstract**, now measured
rather than asserted:

```
k = 0                  -> EQY / dsec        (they are correct and fast here)
k > 0, rigid           -> padded miter      (the only thing that can say yes)
k > 0, elastic         -> stream equivalence
```

## A methodology trap I walked into, worth repeating in the report

The first run showed `cec` **and** `dsec` both failing with
*"Networks have different number of primary inputs"*. That looked like a clean
result. It was partly an artifact of my own export.

`write_aiger -zinit` emits one extra primary input per latch. Since the two
designs have different latch counts (16 vs 48), their **input** counts differed
too (50 vs 82) — so the tools were rejecting the pair for a reason that had
nothing to do with the transform. Re-exporting without `-zinit` gave 34 inputs on
both sides (matching the real ports: clk, rst, a[8], b[8], c[16]) and changed
`dsec`'s answer from a setup failure to a genuine `NOT EQUIVALENT`.

The near-miss: I would have reported "dsec cannot handle latency changes" when
the true finding is "dsec handles them fine and says no." Same headline verdict,
wrong mechanism, and a formal-literate judge would have caught it.

Also flushed out earlier in the same session: `opt -full` run *after* `dffunmap`
silently re-merges synchronous reset back into the FF cell, so `aigmap` fails on
`$_SDFF_PP0_`. `dffunmap` must come last.

Both are arguments for the same discipline: **check the instrument before
trusting the measurement**, and give every checker a positive control.

## Reproduce

```bash
# AIG export -- note: no -zinit, and dffunmap AFTER opt
yosys -q -p "read_verilog -sv mac_ref.v; prep -top mac_ref -flatten; \
  memory_map; opt -full; techmap; setundef -zero; dffunmap; opt_clean; \
  aigmap; write_aiger work/mac_ref_nz.aig"

yosys-abc -c "cec  work/mac_ref_nz.aig work/mac_opt_nz.aig"
yosys-abc -c "dsec work/mac_ref_nz.aig work/mac_opt_nz.aig"
eqy -f lat.eqy      # and ctrl.eqy for the positive control
```

## Environment note

EQY is not in Ubuntu's `yosys` package. It needs `yosys-dev` for `yosys-config`,
and **EQY master does not build against yosys 0.33** — tag `yosys-0.47` does. The
0.47-built plugins load and run correctly under yosys 0.33 here, but that is a
version skew worth re-checking on the real benchmark before trusting a result.

## Files

- `mac_ref.v`, `mac_opt.v`, `mac_ref_copy_src.v` — the pair plus the control copy
- `lat.eqy` — EQY config, latency-differing pair (FAIL)
- `ctrl.eqy` — EQY config, identical designs (PASS)
- `work/*.aig` — exported AIGs, `_nz` = without `-zinit`

## Next

This closes three of the four checkers in the matrix. The fourth is
simulation-only (Verilator testbench), which is what RTLScout actually gates on
in practice — and the one most likely to accept a formally invalid rewrite. That
column is where the headline number comes from.
