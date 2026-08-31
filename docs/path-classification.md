# Routing the fix: classifying why a path is slow before proposing anything

`tools/classify_path.py`, added 2026-08-31. This documents what it does, the
five cases it was checked on, and the one place its statistic is known to be
wrong.

## Why it exists

Batch 1 pointed six formally-gated LLM proposals at the `rv32i_core` critical
path. Four were proven correct, three of those made timing worse, and the
best moved the touched group by 0.485 ns. The obvious reading is "LLM RTL
proposals do not help timing". The measured reading is different, and better.

That path is **58.9% fanout-attributable**: most of its delay sits in cells
driving 32 or more loads. Restructuring logic does not shorten a net's load
delay. The proposals were aimed at the wrong variable.

The design-level AES path was worse still, at **91.4%**, with 21.029 ns in a
single `nor4_1` driving **300 loads** inside `aes_key_mem`, a 15-entry by
128-bit register array read through a combinational 15-to-1 mux.

So SlackSmith now routes twice:

1. **Route the fix by measured path pathology.** Fanout-dominated goes to
   buffering and sizing; depth-dominated goes to the RTL proposer. This file.
2. **Route the proof obligation by declared transform type.** k=0 to
   combinational equivalence, k>0 rigid to a k-padded miter, elastic to
   stream equivalence, re-encoded state to mapped-state equivalence. That is
   the project's original contribution and is unchanged.

## The statistic

`fanout_delay_share` = (sum of incremental delay over path cells whose driven
net has at least `FANOUT_HI` loads) / (sum of incremental delay over all path
cells).

Thresholds, all named constants at the top of the tool:

| constant | value | meaning |
|---|---|---|
| `FANOUT_HI` | 32 | loads before a net counts as high fanout |
| `FANOUT_SHARE_HI` | 0.50 | at or above this, FANOUT_DOMINATED |
| `FANOUT_SHARE_LO` | 0.20 | at or below this, DEPTH_DOMINATED |

Path delay is the **sum of incremental cell delays**, not the report's
`data arrival time`. Arrival includes the launch clock edge, which is nonzero
for a generated or divided clock and would silently inflate the denominator.
An earlier version used arrival and scored a divided-clock path at a
meaningless 0.007.

## Validation

Five paths, one tool, one set of thresholds, no per-case tuning.

| # | path | netlist | constraint | slack | fanout share | verdict |
|---|---|---|---|---|---|---|
| 1 | AES `keymem`, clk_b | unbuffered | v2 SDC | -4.957 | **0.914** | FANOUT_DOMINATED |
| 2 | clk_b | buffered | v2 SDC | +12.600 | 0.000 | NO_ACTION |
| 3 | `rv32i_core` ALU (batch 1's target) | core-level | ppa.sdc | -9.838 | **0.589** | FANOUT_DOMINATED |
| 4 | clk_b | buffered | v2 periods / 6 | -1.689 | **0.000** | DEPTH_DOMINATED |
| 5 | clk_a | buffered | v2 periods / 6 | -12.216 | **0.000** | DEPTH_DOMINATED |

Cases 4 and 5 are the ones that matter. A classifier that answered
FANOUT_DOMINATED for everything would be useless, and the first three cases
alone could not tell the difference. Cases 4 and 5 take the **buffered**
netlist, where the fanout has already been repaired, and tighten every clock
period by 6x until it violates again. The same tool with the same thresholds
returns DEPTH_DOMINATED, with 0.0% of the path delay attributable to
high-fanout cells and the delay spread over 15 and 33 cells respectively.

The verdicts also line up with which lever actually worked, which is
independent of the classifier:

- Cases 1 and 3 are FANOUT_DOMINATED. Buffering closed case 1 outright
  (+17.557 ns), and RTL transforms aimed at case 3 mostly made it worse.
- Cases 4 and 5 are DEPTH_DOMINATED, and they only exist *because* buffering
  removed the fanout first.

That is the practical finding: **the two levers are sequential, not
alternative.** Buffer, re-measure, then propose RTL.

## Two limits, both real

**1. The thresholds were chosen after looking at this benchmark.** They
describe it. They are not validated on any held-out design, and no claim is
made that 32 and 0.50 transfer. The separation in the table above is
evidence that they are not degenerate on this design, and nothing more.

**2. Fanout is undercounted for buses crossing a hierarchy boundary.** The
tool resolves modules leaf-first and charges a net the leaf pins its
submodule port ultimately drives. That resolution is keyed by declared port
name, while internal loads are keyed per bit (`dmem_rdata[3]`, not
`dmem_rdata`), so a **bus** input port contributes 0 instead of its real
count.

This is visible in case 5: the top cell is reported at 6.762 ns with
**fanout 1**, which is not physically credible and is the signature of this
undercount.

The consequence is directional and worth stating, because it does not affect
both verdicts equally:

- **FANOUT_DOMINATED is conservative.** True fanout is at least what was
  counted, so the verdict cannot be produced by the bug.
- **DEPTH_DOMINATED can be wrong.** A path whose fanout is hidden behind a
  bus port would be misrouted to the RTL proposer.

Cases 4 and 5 are therefore weaker evidence than cases 1 and 3. Fixing this
needs bit-level net resolution across ports, which is not done.

## Reproduce

    bash experiments/buffering_control/classify_all.sh          # cases 1, 2, 3
    bash experiments/buffering_control/classify_discriminate.sh # cases 4, 5
