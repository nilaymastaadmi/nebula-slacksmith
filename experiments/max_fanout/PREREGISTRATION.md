# Pre-registration: give repair_design a fanout limit to repair against

Written 2026-09-03, before any SDC with `set_max_fanout` is generated and
before OpenROAD is run with one.

## Why, and why it is a new file

`experiments/openroad_flat/` ended with `clk_e` at −0.952 ns and the same
`a21o_4` driving **65 loads** on all three worst paths after
`repair_design`. Checked, not assumed:

- `sky130hd_tt.lib` declares `default_fanout_load : 1.0` and **no**
  `default_max_fanout`.
- The OpenROAD `sky130hd` platform sets no max fanout anywhere.
- This OpenROAD build's `repair_design` takes `-max_wire_length`,
  `-max_utilization`, `-slew_margin` and `-cap_margin`, and **no**
  `-max_fanout`; it takes the limit from the constraints.

So no part of this flow has ever declared a fanout limit, and
`repair_design` was not failing to fix a violation. There was no violation
to fix. This experiment supplies the missing rule.

**`sdc/bench_top_v3.sdc` is not edited.** Every measurement published
against v3 stays comparable to itself. `sdc/make_v3_maxfanout.py` copies
v3 verbatim and appends one `set_max_fanout` block, so `diff` shows exactly
the added lines and nothing else.

## The value, chosen before any result

**16.** It is the limit this project's own physical lever has enforced since
before this experiment existed (`buffer -N 16` in `tools/slacksmith.py`), so
both levers are asked for the same thing and the number was not picked by
looking at an outcome. Because a single value could be luck, **8 and 32 are
run as well and all three are reported**, with 16 as the headline whichever
turns out best.

## Arms

Netlists from `~/flatexp`, both already on the record:

| arm | netlist | SDC |
|---|---|---|
| MF16-E | flat, ABC buffer+size (arm E) | v3 + max fanout 16 |
| MF8-E | same | v3 + max fanout 8 |
| MF32-E | same | v3 + max fanout 32 |
| MF16-C | flat, no ABC buffering (arm C) | v3 + max fanout 16 |

Flow unchanged: `experiments/openroad_repair/run.sh`, floorplan, placement,
placement parasitics, timing, `repair_design`, detailed placement,
parasitics, timing. Baselines are the same netlists under plain v3 already
measured in `experiments/openroad_flat/` (MF16-E against OR-E's −0.952,
MF16-C against OR-C's −2.243).

## Predictions

41. Under the new SDC, **zero-parasitic OpenSTA slacks on arm E are
    identical to v3's** (+11.158 / +5.665 / −0.319). High. `set_max_fanout`
    is a design rule, not a timing constraint, so anything else means the
    generated file differs in more than the one line intended.
42. MF16-E after repair leaves **no cell above fanout 16** on the three
    worst paths. Medium-high.
43. MF16-E **closes `clk_e`** (at or above 0 with parasitics). Medium. It
    was −0.952 with a 65-load cell on the path.
44. MF16-E's area growth **exceeds** the +21.7% that OR-E measured without
    the constraint. High; more buffering costs area.
45. Across 8, 16 and 32, `clk_e` after repair is **not monotonic** in the
    limit: 8 is not the best of the three. Low-medium, and registered
    because the tempting story is "tighter is better" and over-buffering a
    59,000-net design is a real way to lose.

## What would make this void

- Editing `sdc/bench_top_v3.sdc`, or generating the new SDC by any route
  other than copying it verbatim.
- Reporting a subset of 8, 16 and 32.
- Choosing the headline value after seeing the results.
- Comparing an OpenROAD slack against a zero-parasitic OpenSTA slack.
