# What closure costs, arm by arm

Registered in `PREREGISTRATION.md` (`6fd2e17`), scripts in `fe911f1`, both
before any arm ran. **Physical arms A4 to A6 are still running; this file covers
the five zero-parasitic arms and will be extended, not rewritten.**

## Zero-parasitic arms, gold netlist, SDC v3, one liberty, one flow

| arm | abc script | clk_a | clk_b | clk_e | groups met | cells | buffer-like | area (u²) | area vs A0 | power (W) | power vs A0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A0** | plain `-liberty` | −13.167 | −18.957 | −25.957 | **0 of 3** | 46,255 | 247 | 448,840 | baseline | 0.282 | baseline |
| **A0b** | `_HEAD` only | −13.167 | −18.957 | −25.957 | **0 of 3** | 46,255 | 247 | 448,840 | +0.00% | 0.282 | +0.0% |
| **A1** | `upsize; dnsize` | −9.270 | **+0.282** | −6.718 | **1 of 3** | 46,255 | 247 | 455,101 | **+1.39%** | 0.286 | +1.4% |
| **A2** | `buffer -N 16` | **+1.750** | **+5.556** | −1.444 | **2 of 3** | 48,616 | 2,600 | 484,325 | **+7.91%** | 0.299 | +6.0% |
| **A3** | both (**the loop's lever**) | −1.716 | **+5.600** | −0.606 | **1 of 3** | 48,616 | 2,606 | 466,933 | **+4.03%** | 0.291 | +3.2% |

Area is summed from the liberty's own `area :` values over **every instance** of
each netlist (`area_hier.py`), with **0 unpriced cells**, because `report_design_area` is an OpenROAD command and
OpenSTA rejects it (§ below). Power is vector-free at default activity, one
model for every arm, relative and not a signoff number.

## The finding

**The lever this project ships closes fewer groups than one of its two halves.**

`A2`, buffering alone, meets `clk_a` and `clk_b`. `A3`, the `buffer; upsize;
dnsize` lever the loop actually pulls, meets only `clk_b`. Isolating the part
A3 adds over A2, which is `upsize; dnsize`:

| `dnsize/upsize` on top of buffering | |
|---|---|
| `clk_b` | **+0.044 ns** |
| `clk_e` | **+0.838 ns** |
| `clk_a` | **−3.466 ns**, and that is the difference between meeting and not |
| area | **−17,392 u², −3.6%** |
| power | **−0.008 W, −2.7%** |

So sizing after buffering is an **area-for-timing trade that nobody in this
project decided to make**. It saves 3.6% area and gives up a met clock group.
`tools/slacksmith.py` already has `--lever-policy verdict`, which lets the
classifier pick the component; the default is `blunt`, which is A3.

**And sizing alone is the cheapest closure in the table.** A1 meets `clk_b` for
**+1.39% area and +1.4% power**, with **the same 46,255 cells and the same 247
buffer-like cells as the untouched netlist**: it closes a group by changing
drive strengths, not by adding anything.

## Scorecard, zero-parasitic half

**R83. WRONG.** `_HEAD` alone was predicted to move `clk_b` by more than 0.5 ns.
It moved it by **0.000**, and A0b matches A0 in slack, cell count, buffer count,
area and power, every digit. Yosys's default `abc -liberty` script already **is**
`_HEAD`. The confound this arm was added to remove does not exist, so A1, A2 and
A3's deltas against A0 are clean, which is what the arm was for. It also
demonstrates the `-script` argument is honoured rather than silently dropped,
because A1, A2 and A3 do differ.

**R69. CONFIRMED.** A1 adds **+1.39%** area, under the predicted 3% (first published as +1.31%; see the correction below).

**R68. WRONG in this regime.** Power was predicted to rank the arms in the same
order as buffer count. It does not. **A3 carries more buffer-like cells than A2
(2,606 against 2,600) and less power (0.291 W against 0.299 W)**, because
`dnsize` shrinks cells that buffering had grown. **Power tracks area, not buffer
count**, in every row of this table. Scored WRONG on the zero-parasitic arms;
the physical arms are scored separately, as registered.

**R64 to R67 need the physical arms** and are not scored here.

## An instrument defect found while running this

`report_design_area` is an **OpenROAD** command. OpenSTA answers `invalid
command name`, so the first pass returned no area for any zero-parasitic arm.
Rather than change the arm driver mid-experiment, area was derived afterwards
from the netlists the arms had already written, using the liberty's own values,
which is what OpenROAD sums as well. No arm and no timing number changed.

A second defect, in this file's own first draft: the buffer-count regex
`sky130_fd_sc_hd__(buf|clkbuf|bufinv|inv)_` reported **0** buffer-like cells in
the untouched netlist. It cannot match `clkinv_*`, which is what those cells
are. The corrected count comes from `area_from_liberty.py`. A count of zero in a
netlist this size should have been read as a broken regex immediately and was
not.

**A third, found on 2026-09-13, and it was in the corrected tool.**
`area_from_liberty.py` sums cell lines in the netlist **text**. A hierarchical
netlist writes each module once, and `bench_top` instantiates `aes_load` twice
(`u_aes_b`, `u_aes_e`), so every cell count, buffer count and area in the table
above was first published for one AES instance and not two: 28,844 and 30,264
cells, 196, 1,611 and 1,615 buffer-like, 288,816 to 310,381 u², **+1.31%, +7.47%
and +3.65%**. `area_hier.py` walks the hierarchy and counts each instance. Two
independent figures check it: A0 comes out at **448,840 u²**, the area OpenROAD's
`report_design_area` gives the same gold netlist below, and A2 and A3 at
**48,616 cells**, what `tools/bench_size.py` counts on the flattened buffered
netlist. The table now carries the per-instance numbers. **No slack and no power
figure changes**, because OpenSTA links the hierarchy; the ranking of arms by
area is unchanged; R69 stays CONFIRMED at +1.39%. The relative saving of sizing
after buffering stays 3.6% of A2's area. Raw output:
`results/area_zero_parasitic_per_instance.txt`.

---

## Physical arms, same placed gold, SDC v3

All three start from the identical floorplan and global placement: **448,840 u²**,
`clk_a −51.223`, `clk_b −57.438`, `clk_e −68.683`.

| arm | repair command | clk_a | clk_b | clk_e | groups met | **worst group** | area (u²) | area added | power (W) | buffers | cells |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A4** | `repair_timing -setup` | −0.583 | −0.699 | −0.947 | **0 of 3** | **−0.947** | 479,814 | **+6.90%** | **0.313** | 719 | 48,083 |
| **A5** | `repair_design` (**published**) | **+3.093** | **+5.283** | −1.471 | **2 of 3** | −1.471 | 539,351 | **+20.17%** | 0.408 | 1,162 | 47,294 |
| **A6** | both, in sequence | **+3.093** | **+5.283** | **−0.777** | **2 of 3** | **−0.777** | 544,271 | **+21.26%** | 0.414 | 1,337 | 47,747 |

**Void check passed.** A5 here returns `+3.093 / +5.283 / −1.471` and
**539,351 u²**, identical in every digit to
`experiments/composed_rtl/results/repair_gold.txt`. The two runs share only the
netlist and the SDC, so the table is a measurement rather than an artifact of
this script.

## The finding on the physical side

**The published flow is dominated in both directions, and nobody had measured
it.**

- **On timing:** A6 reaches `clk_e −0.777` where A5 reaches **−1.471**, for
  **+0.91% more area** and **+1.5% more power**. Running `repair_timing -setup`
  after `repair_design` halves the remaining violation for under one percent.
- **On cost:** A4 gets **every group inside 0.947 ns** for **+6.90% area** and
  **0.313 W**, against A5's **+20.17%** and **0.408 W**. A4 meets no group
  outright, but its **worst** group is 0.524 ns better than A5's, at **one third
  the area added** and **77% of the power**.

Which arm is best depends on the question. If the metric is groups met, A5 and
A6 tie and A4 loses. **If the metric is worst-group slack, the order is A6
(−0.777), A4 (−0.947), A5 (−1.471), and the published flow is last.**

## Scorecard, physical half

**R64. CONFIRMED.** A4 closes **0 of 3**, A5 closes **2 of 3**.

**R65. CONFIRMED.** A4 adds **30,974 u²** against A5's **90,511 u²**, which is
**34.2%**, under the predicted half.

**R66. WRONG.** A6 was predicted to close **all three** groups with area within
5% of A5. The area half held (**+0.91%**). The closure half did not: `clk_e`
remains **−0.777**, violated. Scored as written.

**R67. CONFIRMED, and for a stronger reason than predicted.** No arm closes all
three groups for under +10% area, because **no arm closes all three groups at
all**, at any cost in this table. The prediction is right and the reason it is
right is worse news than the prediction assumed.

**R68. WRONG.** Power was predicted to rank the arms in buffer-count order in
each regime. It does in the physical regime (A4 719 buffers 0.313 W, A5 1,162
0.408 W, A6 1,337 0.414 W) and it does **not** in the zero-parasitic regime,
where A3 carries more buffer-like cells than A2 and less power. A prediction
that fails in one of the two regimes it covers is wrong, not half right.

**Five of the seven predictions decided: R64, R65, R67, R69 confirmed; R66,
R68, R83 missed.**

## What this changes in the submission

§8 has reported one closure point, `repair_design` at +20.2% area. That number
stands, and it is now one row of a curve rather than the answer. The cheapest
arm that gets every group inside a nanosecond costs **+6.90%**, and the best
worst-group slack costs **+21.26%** and is not the published flow.
