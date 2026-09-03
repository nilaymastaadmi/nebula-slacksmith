# XPROP addendum: results

Registered in `PREREGISTRATION_xprop.md` before the case was built or run.
**Scored on its own. Never folded into any Tier B number.**

## Result

| checker | verdict | detail |
|---|---|---|
| sim, comparison with `!=` | **ACCEPT** | 0 mismatching cycles of 500 |
| sim, comparison with `!==` | **REJECT** | **50** mismatching cycles of 500 |
| `abc cec` | REJECT | counterexample |
| `abc dsec` | REJECT | not equivalent |

**Identical stimulus. Identical design pair. Identical simulator. The only
difference between the first two rows is one character in the comparison.**

The 50 is not a coincidence and is the check that the mechanism is the one
claimed: the testbench holds the write enable low for exactly the first 50
cycles, which is the window in which the un-reset register is still unknown.
Every mismatch is inside it, and outside it the two designs agree.

## Predictions, scored

- **X1 correct.** `!=` accepts. `s_gold != s_gate` evaluates to `x` when
  either side is unknown, and `if (x)` takes the false branch, so the
  mismatch is not counted. The testbench reports a clean run.
- **X2 correct.** `!==` rejects, 50 cycles.
- **X3 correct**, and it is the finding: **the verdict is a property of the
  checker's comparison operator, not of the design.** A team that writes `==`
  ships this bug and their testbench tells them everything is fine.
- **X4 correct.** `cec` and `dsec` both reject, but **not because they
  modelled the unknown**. Yosys' stack is two-valued; it cannot represent `x`
  at all. The un-reset register becomes a free Boolean variable, the two
  designs genuinely differ over that variable, and the tools report it. They
  got the right answer to a different question.

## Why that last point is worth stating plainly

The open-source formal flow this project is built on **cannot be
X-optimistic, and cannot be asked about X either**. That is a real limitation
of the methodology, not a feature. A four-state property such as "this
register is never read before it is written" is outside what these tools
express, and a commercial X-propagation app is the usual answer.

Here it happens to work in our favour: two-valued formal catches a dropped
reset that a `==` testbench misses. It would not help at all on a defect that
only manifests as `x` in one design and a definite value in the other with no
two-valued difference between them. **We are not claiming coverage of the
XPROP class. We are reporting that one instance of it is caught, for a reason
that is not the reason it looks like.**
