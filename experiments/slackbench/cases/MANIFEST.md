# SlackBench Tier B: the eight cases and their ground truth

**Written before any checker was run on any of them.** Ground truth here is
what the suite grades against; a checker's verdict never edits this file.
Registered in `../PREREGISTRATION.md`, amendment 1.

Each case is `<CASE>/gold.v` and `<CASE>/gate.v`, one module per file, same
module name on both sides.

| case | class | ground truth | k |
|---|---|---|---|
| LATENCY-1 | LATENCY | **EQUIVALENT** modulo a latency offset | +1 |
| LATENCY-2 | LATENCY | **NOT EQUIVALENT** at any offset | +1 declared |
| STIMULUS-1 | STIMULUS | **NOT EQUIVALENT** | 0 |
| STIMULUS-2 | STIMULUS | **NOT EQUIVALENT** | 0 |
| CDC-1 | CDC | **EQUIVALENT** modulo a latency offset, and a protocol defect no functional checker sees (corrected, see NOTES.md amendment 2) | −1 |
| CDC-2 | CDC | **EQUIVALENT**, and a protocol defect no functional checker sees | 0 |
| CONTROL-1 | CONTROL | **EQUIVALENT** | 0 |
| CONTROL-2 | CONTROL | **EQUIVALENT** | 0 |

## Counterexamples, which is how NOT EQUIVALENT is established

Each is an input sequence and the differing output, replayable in any
simulator and independent of every checker being scored. This is why the
NOT EQUIVALENT rows are not circular.

**LATENCY-2.** Compare gold at cycle t+1 against gate at cycle t+2, which is
the alignment its own declared k asks for. Gate computes
`a[t]*b[t] + c[t+1]`; gold computes `a[t]*b[t] + c[t]`. They differ whenever
`c` changes.

    cycle 0: a=1, b=1, c=0
    cycle 1: a=0, b=0, c=5
    gold y (cycle 1) = 1        gate y (cycle 2) = 6

**STIMULUS-1.** One input pair out of 65,536.

    a=0xA5 (165), b=0x3C (60), c=0
    gold y = 165*60 = 9900 = 0x26AC        gate y = 0xDEAD

**STIMULUS-2.** Two consecutive enabled cycles.

    cycle 0: en=1, d=1
    cycle 1: en=1, d=1
    gold acc = 2        gate acc = 1

## The EQUIVALENT rows, and who established them

Per the registration, a case never scores the tool that established its
ground truth.

- **LATENCY-1**: equivalent under a +1 offset by construction, `c` being
  pipelined alongside the product. Any checker that reports a plain
  inequivalence is right about the literal question and wrong about the
  intended one, which is what the case tests. `CIRCULAR` for the padded
  miter.
- **CDC-2**: `gray(delay(x))` equals `delay(gray(x))` because the encoder is
  combinational and delay commutes with it. This is an algebraic argument,
  not a tool's output, so no checker is excluded.
- **CONTROL-1**: one multiplier feeding both mux arms instead of two. Same
  function by construction.
- **CONTROL-2**: identical `busy` behaviour under a state bijection
  (`00→001`, `01→010`, `10→100`). `CIRCULAR` for the mapped-state obligation.

## The two CDC cases, stated precisely because the framing matters

Neither is a functional bug, and that is the whole point.

**CDC-1** removes one flop from a two-flop synchronizer. Functionally that is
a latency change of one cycle and a checker will report exactly that. A
reviewer reading "latency reduced by 1" may well accept it as intended. The
actual defect is that an asynchronous input now has no metastability guard,
which is invisible to every functional method because metastability is not a
function.

**CDC-2** moves a gray encoder from before the synchronizer to after it. The
function is unchanged and every functional checker should agree. The bus
crossing the boundary is now raw binary, so a four-bit transition such as
0111 to 1000 lets the receiver latch any of sixteen values.

We expect to fail both, including with our own gate. That is registered as
prediction 4 and it is the honest position: **SlackSmith proves module-level
equivalence and has no notion of a protocol.**

## Known gap

**XPROP is absent.** It appears in the registration's class table and was
never allocated a slot in the fixed count. Adding it now would break the
count, which exists so that cases cannot be added once results are visible.
Reported as a gap in the suite rather than removed from the class table.
