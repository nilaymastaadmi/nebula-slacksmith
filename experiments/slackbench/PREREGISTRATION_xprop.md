# Pre-registration addendum: the XPROP case

Written 2026-09-03, **before the case is built and before it is run**.

## Why this is an addendum and not a ninth Tier B case

`PREREGISTRATION.md` fixes Tier B at exactly 8 cases so that cases cannot be
added once results are visible, and amendment 1 recorded XPROP as an unbuilt
gap for that reason. **Adding it to Tier B now would be precisely the move
the fixed count exists to stop**, because Tier B's results are visible. So it
is registered separately here, lives in `cases_xprop/`, and is **scored on its
own and never folded into any Tier B number**.

## What X-optimism actually is, and the complication

X-optimism is a simulation artifact where an unknown value is resolved to a
definite one, hiding a real difference. The canonical form is not in the
design at all: it is in the **comparison**. `gold == gate` evaluates to `x`
when either side is `x`, and `if (x)` takes the false branch, so a testbench
written with `==` silently skips every cycle where an unknown is present.
`!==` compares 4-state and does not.

**The complication, stated up front because it shapes the result.** Yosys'
formal stack is **2-valued**. It cannot represent `x` at all; an
uninitialised register becomes a free Boolean variable. So formal cannot be
X-optimistic, and it also cannot be asked the question. That is a real
limitation of the open-source methodology and reporting it is the point of
this case, not a workaround.

## The case

`cases_xprop/XPROP-1/`. Gold resets a status register; gate omits the reset.
Every observable difference is therefore reachable only through a register
that is unknown until first written.

**Ground truth: NOT EQUIVALENT.** Established by a counterexample independent
of any checker: hold the write enable low and read the status output. Gold
reports its reset value; gate reports whatever the register powered up as,
which two-valued formal will exhibit as a concrete differing assignment.

## Checkers, and the two that matter

The Tier B checkers, plus the same simulation run twice with the only
difference being the comparison operator:

- `sim_eq` compares with `==`, the operator a person writes.
- `sim_neq` compares with `!==`.

## Predictions

X1. `sim_eq` **accepts** the pair: the mismatch is masked because the
    comparison of an unknown yields `x` and the check is skipped. High.
X2. `sim_neq` **rejects** it. High.
X3. The two differ **on identical stimulus and an identical design pair**,
    so the verdict is a property of the checker's comparison operator alone.
    High; X1 and X2 together are the finding.
X4. The formal checkers reject it too, but **for the wrong reason**: not
    because they modelled the unknown, but because two-valued formal turns
    the uninitialised register into a free variable. Medium-high, and it is
    the honest limitation this case exists to expose.

## What would make this void

- Folding this case into any Tier B count.
- Changing the comparison operators after seeing either verdict.
