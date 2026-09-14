# Pre-registration: what closure costs, arm by arm

Registered 2026-09-12, before any arm was run. Scored in `NOTES.md` here.
Predictions **R64 to R69 and R83**; R1 to R63 are in the earlier registrations, and R70 to R82 are reserved for the experiments that follow this one.

## Why

§8 reports one closure point: `repair_design`, **+20.2% area and +47.1% power**.
A judge asked to weigh timing against power and area wants the trade-off, and
this project has never asked **whether the design can close for less**.

`repair_design` fixes slew, capacitance and fanout violations everywhere in the
design. `repair_timing -setup` fixes only paths that actually violate setup. The
second may reach the same timing with far fewer buffers, and if it does, the
honest headline for D5 changes from one number to a curve.

## The arms

Everything is the **gold** netlist under `sdc/bench_top_v3.sdc`. Nothing else
varies: one liberty, one `dont_use` list, one top, one clock set.

| arm | what runs | regime |
|---|---|---|
| A0 | plain `abc -liberty`, the flow every baseline number in this project came from | zero-parasitic |
| **A0b** | `_HEAD` only (the resyn2-style script, no buffering, no sizing) | zero-parasitic |
| A1 | `_HEAD` + `upsize; dnsize` (`SIZE_ONLY`) | zero-parasitic |
| A2 | `_HEAD` + `buffer -N 16` (`BUF_ONLY`) | zero-parasitic |
| A3 | `_HEAD` + both (`BOTH`, the loop's lever) | zero-parasitic |
| A4 | placement, then `repair_timing -setup` only | with parasitics |
| A5 | placement, then `repair_design` (the published flow) | with parasitics |
| A6 | placement, `repair_design`, then `repair_timing -setup` | with parasitics |

**A0b is not in the brief and is added on purpose.** A1, A2 and A3 all carry
`_HEAD`. Comparing them against A0 attributes `_HEAD`'s own effect to buffering
or sizing. Without A0b every zero-parasitic number in this table is confounded,
and this project has already shipped one confounded lever comparison and had to
retract it.

Measured per arm: WNS on `clk_a`, `clk_b`, `clk_e`; total cells; buffer cells;
`report_design_area`; and `report_power` by the exact method in
`experiments/ppa/power/run.sh` (vector-free, default activity, one model).

## Null control

**Already measured and not re-run.** R47 put the gold netlist through the
identical OpenROAD flow twice and got identical slacks and identical area in
every digit (`experiments/composed_rtl/`, amendment 1). The physical flow is
deterministic here, so any difference between A4, A5 and A6 is the arm.

The zero-parasitic side has §5's null control: swapping a module for itself
returns 0.000 on every group.

**Power has no floor yet.** `report_power` is deterministic for a fixed netlist,
so the floor is zero by construction, but the estimate is vector-free at default
activity. It is a relative figure for ranking netlists under one model and is
**not a signoff number**. Any power difference under 1% is reported as a tie.

## Predictions

**R64.** A4 closes fewer of the three groups than A5. *Prior: moderate. Targeted
setup repair should be surgical, but it runs on a design whose slew and
capacitance violations have not been cleaned, and OpenROAD's setup repair leans
on legal transition times.*

**R65.** A4 adds **less than half** the area A5 adds. *Prior: strong. A5 touches
every violating net in the design; A4 touches only violating paths.*

**R66.** A6 closes **all three** groups, with area within **5%** of A5. *Prior:
weak, and it is the interesting one. A5 does not close `clk_e` under v3
(−1.471). If A6 does, the project gains a closing flow it has never reported.*

**R67.** **No** arm closes all three groups for less than **+10%** area.
*Prior: moderate. A5 costs +20.2% and does not close all three.*

**R68.** Power ranks the arms in the **same order as buffer count**, scored
**within each regime separately**, never across them. *Prior: strong. Buffers
carry internal and switching power and nothing else here changes activity.*

**R69.** A1 (sizing only) adds **under 3%** area against A0b. *Prior: moderate.
`upsize` adds and `dnsize` removes, so the net is a difference of two larger
numbers and could land either side.*

**R83.** `_HEAD` alone (A0b against A0) moves `clk_b` by **more than 0.5 ns**,
that is, the resyn script is not a no-op and the confound A0b exists to remove
is real. *Prior: moderate. If this misses, A0b was unnecessary and that is worth
knowing too.*

## Stopping rule and what would void this

- The arms are the eight above. **No arm is added after seeing a result**, and
  no arm is dropped for being unflattering.
- If an OpenROAD arm fails to complete, it is reported as failing to complete.
  It is not replaced with a different repair command.
- If A5 here does not reproduce the slacks and area already recorded in
  `experiments/composed_rtl/results/repair_gold.txt`, **the whole table is
  VOID** and the discrepancy is the finding, because the two runs differ only in
  which script invoked them.
- Power differences under 1% are ties, declared now rather than after seeing
  how close they land.

## Not being done, and why

No SDC is edited and no `set_max_fanout` or other constraint is added.
`experiments/max_fanout/` already measured that lever and it made things worse.
Closure bought by changing the target is what G0 exists to catch.

---

## Correction, same day, before any arm was scored

The extra prediction was registered as R70 and renumbered to **R83** minutes
later, without being run. R70 to R82 are reserved by the final-push plan for the
speed-up, open-weight and depth-cell blocks, and two experiments answering to
one id is how a scorecard silently loses a result. Nothing else changed: the
prediction, its prior and its arm are as first written in `6fd2e17`.
