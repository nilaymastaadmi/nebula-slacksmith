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
driving 32 or more loads. Buffering, not restructuring, is built to shorten a
net's load delay, so those proposals were aimed at the wrong variable. (The
stronger wording once here, that restructuring cannot shorten it, is retracted in
REPORT §1: two proven transforms later moved a 91.4% path.)

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
| 4 | clk_b | buffered | v2 periods / 6 | -1.689 | recorded 0.000, **corrected 0.344** | recorded DEPTH_DOMINATED, **corrected MIXED** |
| 5 | clk_a | buffered | v2 periods / 6 | -12.216 | recorded 0.000, **corrected 0.428** | recorded DEPTH_DOMINATED, **corrected MIXED** |

Cases 4 and 5 were meant to show the tool is not degenerate: take the
**buffered** netlist, where the fanout has been repaired, tighten every
clock period by 6x until it violates again, and see whether the same
thresholds say something other than FANOUT_DOMINATED. As first recorded
they returned DEPTH_DOMINATED at 0.000. **That was the bug described under
limit 2 below**, and the numbers in the table are what the corrected tool
returns from the same netlist and reports (re-run 2026-09-03 with
`experiments/buffering_control/classify_discriminate.sh`): case 4 has a
59-load S-box input carrying 2.058 of 5.98 ns, case 5 a 387-load net
carrying 6.762 of 17.13 ns.

What the corrected table shows is weaker than what the recorded one
claimed, and is stated as such. The tool still separates: 0.914 and 0.589
against 0.344 and 0.428, with case 2 at NO_ACTION. It has produced no
DEPTH_DOMINATED verdict on this benchmark; the only DEPTH verdicts it has
produced are on the external designs (7 of 15, `experiments/drrtl_transfer/`).

The verdicts line up with which lever actually worked, which is independent
of the classifier: buffering closed case 1 outright (+17.557 ns), RTL
transforms aimed at case 3 mostly made it worse, and on cases 4 and 5
buffering alone was the step that helped and sizing was the step the closed
loop reverted (`docs/closed-loop.md`, runs 4 and 5).

That is the practical finding: **the two levers are sequential, not
alternative.** Buffer, re-measure, then classify again.

## One limit that stands, and one that was a bug

**1. The thresholds were chosen after looking at this benchmark.** They
describe it. They are not validated on any held-out design, and no claim is
made that 32 and 0.50 transfer. The separation in the table above is
evidence that they are not degenerate on this design, and nothing more.

**2. Fanout was undercounted across module boundaries. Fixed 2026-09-03.**
The paragraph that stood here until then said: a bus input port contributes
0 instead of its real count; "this is visible in case 5: the top cell is
reported at 6.762 ns with fanout 1, which is not physically credible and is
the signature of this undercount"; and "DEPTH_DOMINATED can be wrong". All
three sentences were true, the tell was written down, and the tool shipped
with it for three days. It was caught when a closed-loop stop line was read
against the OpenSTA report it came from: the cell at "fanout 1" drives
**387** leaf pins, and a 1.952 ns cell recorded at "fanout 0" drives **59**.

Three distinct defects, one cause (a port connection was charged only when
its text equalled a net name):

| shape | example | before | after |
|---|---|---|---|
| whole-bus connection | `.sboxw(tmp_sboxw)` | 0 | 59 |
| concatenation, one bit fanned into many port bits | `.imem_data({imem_data[2], imem_data[2], ...})` | 1 | 387 |
| loads above an output port (parent side) | tv80 `_2297_`, DSP flop | 0, 1 | 34, 53 |

The fix expands bus, part-select and concatenation connections bit by bit,
resolves loads upward through output ports as well as downward, and, when
`report_checks` was asked for `-fields {fanout}`, uses OpenSTA's own
leaf-pin count instead (both query strings in this repo now ask). The
correction can only add loads, so a verdict can move toward FANOUT and
never toward DEPTH.

`tools/classify_regression.py` checks 5 fixtures (two from this benchmark,
tv80, DSP and cpu_pipe from the transfer study) cell by cell against the
fanout column: **0 disagreements at or above fanout 32**, 3 at fanout 1 or
15 where the netlist-only path still misses an alias (stated, not failed).

What it changed: every DEPTH_DOMINATED verdict the closed loop gave on the
post-buffering v3 paths is MIXED (clk_a 0.428, clk_e 0.286), which means the
RTL lever in runs 2 and 3 was routed wrongly (`docs/closed-loop.md`); 1 of
15 external verdicts changed (`experiments/drrtl_transfer/NOTES.md`,
amendment 4). Cases 4 and 5 in the table above carry both values.

## Reproduce

    bash experiments/buffering_control/classify_all.sh          # cases 1, 2, 3
    bash experiments/buffering_control/classify_discriminate.sh # cases 4, 5
