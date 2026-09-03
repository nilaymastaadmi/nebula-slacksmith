# Pre-registration: run 8, module attribution on the flat netlist

Written 2026-09-03 before the run, after the mechanism was verified once in
a scratch script whose output is quoted below.

## The problem this fixes

`synth -flatten` renames every cell (`_44958_`, `_32468_`), so the
classifier could not say which RTL module a path cell came from, and the
loop's RTL lever filters candidate proposals on exactly that. Run 6's log
attributes every cell to `bench_top`.

Yosys stamps each cell with the source line that created it.
`tools/remeasure.py` now writes a second netlist **with** attributes
(OpenSTA rejects them, so the timed netlist keeps `-noattr`) and
`classify_path.src_module_map()` maps cell to module by file and line
range. Verified once before this registration, on a fresh flat build:

    slacks: clk_a 11.158  clk_b 5.665  clk_e -0.319     (= arm E exactly)
    src map entries: 5567
    without src map: 1.888 ns dfrtp_1 fanout 136 module bench_top
    with    src map: 1.888 ns dfrtp_1 fanout 136 module aes_encipher_block

Two things in that output matter beyond the fix. **The slacks are arm E to
the decimal**, so adding the attributed write does not perturb synthesis.
And **the binding module is `aes_encipher_block`**, not the
`aes_decipher_block` / `aes_inv_sbox` pair that binds on the hierarchical
flow. A proposal batch written against the hierarchical target would have
been aimed at a module that no longer binds.

## Stated limit, measured not guessed

The map covers 5,567 cells. Yosys keeps a `src` for cells it created from
RTL (largely registers and the logic it did not remap); cells ABC produced
during technology mapping carry none, and those fall back to the netlist's
own answer, which on a flat netlist is the top module. So on a flat netlist
module attribution is **reliable for the path's endpoints and partial for
its middle**. That is enough to filter proposals by the module owning a
path's start or end, and it is not enough to claim every cell's owner.

## Predictions

39. Run 8 (`--flatten`, same policy and bar as run 6) reproduces run 6's
    trajectory exactly: same three measurements, same two confirms, stop
    `physical_exhausted`. High.
40. In run 8's log, at least one `top_cells` entry across the three
    classify records names a module other than `bench_top`, and none names
    a module the corresponding hierarchical run named for the same clock.
    Medium-high on the first half; the second half is the claim that the
    flow changed the target and is the one worth being wrong about.

## Why no RTL batch follows here

The loop's registered policy routes MIXED to the physical lever and stops.
`clk_e` is MIXED at 0.3374 on this netlist, so **the RTL lever does not
fire on the flat flow either**, and a batch aimed at `aes_encipher_block`
would be measured outside the router's own decision. Writing one anyway,
after seeing which module binds, is also precisely the tuning both proposer
registrations forbid. The target is recorded here so a future batch has a
registered starting point; it is not generated now.

## Outcome, 2026-09-03

Run 8 (`run_v3_srcmap.jsonl`, scorer `score_srcmap.py`): **P39 and P40 both
correct.** The trajectory is run 6's, measurement for measurement, and the
final state is identical (+11.158 / +5.665 / −0.319), so the attributed
netlist write does not perturb the flow. Module attribution:

| iteration | top cells, run 6 | top cells, run 8 |
|---|---|---|
| 1 | bench_top, bench_top, bench_top | bench_top, bench_top, bench_top |
| 2 | bench_top, bench_top, bench_top | **aes_encipher_block**, bench_top, bench_top |
| 3 | bench_top, bench_top, bench_top | **aes_encipher_block**, bench_top, bench_top |

The stated limit shows exactly where it bites. In iterations 2 and 3 the
binding cell is a flop, Yosys kept its `src`, and the loop now knows the
module. In iteration 1 it is a `nor4_1` that ABC produced during technology
mapping, which carries no `src`, so it still reads `bench_top`. The RTL
lever can filter on the module owning a path's endpoints; it cannot claim
the owner of every cell in between.
