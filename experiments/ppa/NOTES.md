# PPA comparison, and the finding that core-level and design-level disagree

Run 2026-08-31. OpenSTA + sky130hd_tt, `lpflow`/`probe` excluded,
`opt_clean -purge` applied. Covers organizer deliverable 5 (timing, frequency
and PPA comparison) for the four formally proven LLM proposals.

## Core level: `rv32i_core` alone, the transform is 100% of the design

SDC in `ppa.sdc`: 10 ns clock, every non-clock input driven and delayed,
every output loaded and delayed, plus `set_false_path -from rst_n`. That
false path is required and is not a convenience: without it the async
reset's recovery check dominates and `report_wns` pins at -32.30 for every
variant, masking the data path entirely. That artifact is the same one
documented in `experiments/rv32i_wns/NOTES.md`.

| variant | cells | data WNS (ns) | power (mW) | verdict |
|---|---|---|---|---|
| gold | 6,769 | -9.84 | 6.26 | baseline |
| P1 addsub sharing | 6,702 | -9.46 (+0.38) | 6.25 | slightly better on all three |
| P2 shifter sharing | **6,441 (-328)** | -9.81 (+0.03) | **6.20** | smallest, lowest power |
| P3 comparator sharing | 6,700 | **-12.65 (-2.81)** | 6.62 | worse on all three |
| P6 branch cmp sharing | 6,864 (+95) | **-7.88 (+1.96)** | 6.38 | **best timing** |

Power is vector-free at OpenSTA's default switching activity. That is a
relative comparison between variants of one design, which is what a PPA
table needs, and it is not an absolute power figure for silicon. Stated
rather than implied.

## Design level: the same four transforms inside `bench_top`

From `experiments/llm_proposer/` (55,413-cell design, frozen SDC, clk_a):

| variant | design clk_a delta | core data WNS delta |
|---|---|---|
| P1 | **-2.471** | +0.38 |
| P2 | **+0.829** | +0.03 |
| P3 | **-2.051** | -2.81 |
| P6 | **-3.400** | **+1.96** |

## The finding: the two rankings nearly invert

By core-level timing the best transform is **P6** (+1.96 ns). By design-level
timing P6 is the **worst** (-3.400 ns), and the only design-level winner is
P2, which is nearly neutral at core level (+0.03 ns).

Only P3 agrees with itself: worse in both.

Two mechanisms, both real:

1. **The core's critical path is not the design's critical path.** Inside
   `bench_top` the core sits in `rv32_load` behind a 16-word async-read
   dmem and a ROM, and the design-level worst path runs through that wrapper
   logic and its fanout, not through the ALU cone the transforms touch.
   Improving the ALU can leave the binding path untouched.
2. **Global remapping.** `docs/measurement-methodology.md` established by
   null control that this flow is deterministic (0.000 delta on a
   self-swap) but not local: a module-confined RTL change moves unrelated
   path groups through ABC's global technology mapping, measured at 1.4 ns
   for one such change.

**Reporting consequence.** A single-context PPA number is not a claim about a
transform, it is a claim about a transform in a context. Both contexts are
reported here for all four proposals, and where they disagree that is stated
rather than resolved by picking the flattering one. A submission that
reported only the core-level table would have named P6 the best transform;
one that reported only the design-level table would have named it the worst.

## Reproduce

    # core level
    yosys -p "read_verilog rtl/rv32i_core[_Pn].v; synth -top rv32i_core; \
      dfflibmap -liberty <lib>; abc -liberty <lib> <dont_use flags>; \
      opt_clean -purge; write_verilog -noattr core.v; stat"
    sta -no_init -no_splash -exit q.tcl   # read ppa.sdc, report_wns, report_power

    # design level
    python3 tools/remeasure.py --swap-instance u_rv32_a --swap-module rv32_load \
      --replace rv32i_core.v:rv32i_core_Pn.v --clock clk_a ...
