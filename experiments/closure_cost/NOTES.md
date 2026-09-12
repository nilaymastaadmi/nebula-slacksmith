# What closure costs, arm by arm

Registered in `PREREGISTRATION.md` (`b614b2c`), scripts in `6132e8c`, both
before any arm ran. **Physical arms A4 to A6 are still running; this file covers
the five zero-parasitic arms and will be extended, not rewritten.**

## Zero-parasitic arms, gold netlist, SDC v3, one liberty, one flow

| arm | abc script | clk_a | clk_b | clk_e | groups met | cells | buffer-like | area (u²) | area vs A0 | power (W) | power vs A0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **A0** | plain `-liberty` | −13.167 | −18.957 | −25.957 | **0 of 3** | 28,844 | 196 | 288,816 | — | 0.282 | — |
| **A0b** | `_HEAD` only | −13.167 | −18.957 | −25.957 | **0 of 3** | 28,844 | 196 | 288,816 | +0.00% | 0.282 | +0.0% |
| **A1** | `upsize; dnsize` | −9.270 | **+0.282** | −6.718 | **1 of 3** | 28,844 | 196 | 292,588 | **+1.31%** | 0.286 | +1.4% |
| **A2** | `buffer -N 16` | **+1.750** | **+5.556** | −1.444 | **2 of 3** | 30,264 | 1,611 | 310,381 | **+7.47%** | 0.299 | +6.0% |
| **A3** | both (**the loop's lever**) | −1.716 | **+5.600** | −0.606 | **1 of 3** | 30,264 | 1,615 | 299,346 | **+3.65%** | 0.291 | +3.2% |

Area is summed from the liberty's own `area :` values over each netlist, with
**0 unpriced cells**, because `report_design_area` is an OpenROAD command and
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
| area | **−11,035 u², −3.6%** |
| power | **−0.008 W, −2.7%** |

So sizing after buffering is an **area-for-timing trade that nobody in this
project decided to make**. It saves 3.6% area and gives up a met clock group.
`tools/slacksmith.py` already has `--lever-policy verdict`, which lets the
classifier pick the component; the default is `blunt`, which is A3.

**And sizing alone is the cheapest closure in the table.** A1 meets `clk_b` for
**+1.31% area and +1.4% power**, with **the same 28,844 cells and the same 196
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

**R69. CONFIRMED.** A1 adds **+1.31%** area, under the predicted 3%.

**R68. WRONG in this regime.** Power was predicted to rank the arms in the same
order as buffer count. It does not. **A3 carries more buffer-like cells than A2
(1,615 against 1,611) and less power (0.291 W against 0.299 W)**, because
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
the untouched netlist. It cannot match `clkinv_*`, which is what those 196 cells
are. The corrected count comes from `area_from_liberty.py`. A count of zero in a
28,844-cell netlist should have been read as a broken regex immediately and was
not.
