# Giving repair_design a fanout limit: it enforced it, and timing got worse

Registered in `PREREGISTRATION.md` (commit `66eb3dd`) before any SDC with
`set_max_fanout` existed. Run 2026-09-03, `run.sh`, logs and repaired
netlists in `results/`, scored by `score.py`.

All numbers carry placement parasitics. Compare within a netlist only.

## The table

Arm E is the flat netlist with ABC buffering and sizing already applied.
Arm C is the flat netlist with no ABC buffering. The `no limit` rows are
`experiments/openroad_flat/`, unchanged.

| netlist | max fanout | clk_a | clk_b | **clk_e** | area growth |
|---|---|---|---|---|---|
| E | none | +10.175 | +5.225 | **−0.952** | +21.7% |
| E | 8 | +9.795 | +4.403 | **−2.238** | +28.4% |
| E | **16** | +10.058 | +5.358 | **−1.075** | +23.4% |
| E | 32 | +10.192 | +5.453 | **−0.684** | +22.9% |
| C | none | +10.087 | +5.489 | **−2.243** | +18.7% |
| C | 16 | +10.052 | +5.489 | **−1.278** | +23.5% |

## Scored

- **P41 correct.** Zero-parasitic slacks are identical under v3 and under
  v3+mf16 (+11.158 / +5.665 / −0.319), so the generated file differs from
  the frozen one in exactly the intended way. The run script also asserts
  the first 191 lines are byte-identical to v3.
- **P42 correct.** After repair under the limit of 16, **no cell on any of
  the three worst paths drives more than 16 loads**. The constraint was
  enforced. The 65-load cell is gone.
- **P43 wrong, and this is the result.** `clk_e` does not close. At the
  registered limit of 16 it is **−1.075, worse than the −0.952 the same
  netlist reached with no fanout limit at all.**
- **P44 correct.** Area grows +23.4% against +21.7%.
- **P45 correct.** 8 is not the best of the three; the ordering runs the
  other way, 32 better than 16 better than 8, and only 32 beats having no
  limit.

3 of 5 correct, and the one that matters was wrong.

## What this actually says

**Satisfying the fanout rule is not the same as fixing the path.** The
constraint did exactly what it was asked: nothing above 16 loads survives on
the critical paths. Timing still got worse, because the buffers inserted to
split those nets sit on the path and cost more delay than the fanout they
removed. Tightening the limit to 8 costs 1.286 ns against no limit and 4.7
points of area, all of it spent on a rule that was never the binding
constraint.

**A retraction.** Before running this, the report and the previous session
summary both said adding the missing constraint "would likely close" the
group. That was a Medium-confidence registered prediction and it is
**wrong**. It is corrected in `REPORT.md` §7.3 rather than quietly dropped.

**Where the constraint does help is where ABC has not already been.** On
arm C, which no ABC buffering pass has touched, the limit of 16 is worth
**+0.965 ns** (−2.243 to −1.278). On arm E, which `buffer -N 16` already
buffered to that same limit, asking OpenROAD to enforce 16 again makes it
redo the same work with its own buffers, and it comes out behind. Stated as
a hypothesis consistent with all six rows, not as a proven mechanism: the
two tools' buffering does not compose the way their repair strategies do.

**The design still does not close under v3 with parasitics.** The best
configuration measured anywhere in this project is flat synthesis, ABC
buffer and size, then `repair_design` with a max fanout of 32:

    clk_a +10.192    clk_b +5.453    clk_e -0.684    area +22.9%

Two of three groups met, one 0.684 ns short. That is the honest state.

## What is not claimed

32 is not presented as the right limit. It is the best of three values on
one design, and 16 was the registered headline precisely so that this
sentence could not be written the other way round. Choosing 32 because it
won would be the tuning the registration forbids; it is reported as the
best measured value and nothing is re-run under it.
