# The cheat no equivalence checker can catch

Run 2026-09-03. **Exploratory, not pre-registered**, and labelled as such: this
demonstrates a mechanism rather than testing a hypothesis, so there was nothing
to be wrong about. `run.sh` reproduces it.

## What was measured

One netlist, `~/flatexp/E/mapped.v`, **26,958 cells, unchanged in every row**.
No RTL edit, no resynthesis, no buffer, no gate resized. The only thing that
varies is what the SDC says. Timing is our own OpenSTA under
`sdc/bench_top_v3.sdc` plus one appended line.

| appended constraint | clk_a | clk_b | **clk_e** |
|---|---|---|---|
| none (honest baseline) | 11.158 | 5.665 | **−0.319 VIOLATED** |
| `set_multicycle_path 2 -setup -to <endpoint>/D` | 11.158 | 5.665 | −0.295 |
| `set_false_path -to <endpoint>/D` | 11.158 | 5.665 | −0.295 |
| `set_multicycle_path 2 -setup -from clk_e -to clk_e` | 11.158 | 5.665 | **+4.860 MET** |

**One line closes the group.** It is worth **+5.179 ns**, which is more than
this project's best formally-proven RTL transform (+4.925) and it required
changing nothing at all.

**Withdrawn 2026-09-12 (REPORT §5.2):** the comparison to +4.925 is not like for
like. The +5.179 is measured on this 26,958-cell flat netlist and the +4.925 on the
55,413-cell hierarchical benchmark, so the two are not quoted against each other.

## The two things this shows

**1. Equivalence checking cannot see it, by construction.** Every checker we
own would return "equivalent" on this pair, correctly, because the two designs
are the same file. A project whose entire correctness story is functional
equivalence has **no defence at all** against a constraint edit. Proof of
equivalence is necessary and nowhere near sufficient for believing a slack
number.

**2. The narrow version does not work, and that is mechanistically
interesting.** Aiming the exception at the reported endpoint buys 0.024 ns,
because the worst path simply moves to the next endpoint in the same group.
Only the domain-wide exception pays, and a domain-wide exception is a
conspicuous line in an SDC diff. The cheat that pays is the cheat that is
easiest to see, provided anyone looks.

## What this changes in the tool

The project already forbade timing exceptions by policy, and
`sdc/bench_top_v3.sdc` says so in a comment: "No multicycle_path is used
anywhere in this file: a multicycle path is an SDC statement that can
manufacture slack without changing the design." That was an assertion. It is
now a number.

The gate should enforce it rather than trust it. **G0, constraint integrity:**
before any slack number is believed, hash the SDC actually loaded and compare
it against the registered one; refuse to report a measurement taken under
constraints that differ from the frozen file. Cheap, and it closes the one
attack surface that G1 to G5 structurally cannot.

This is also why `sdc/make_v3_maxfanout.py` copies v3 verbatim and appends,
and why `experiments/max_fanout/run.sh` asserts the first 191 lines are
byte-identical before any arm runs. That discipline was already right; this
measurement says what it is worth.

## Honest limits

One design, one tool, one exception type. `set_false_path` and
`set_multicycle_path` are legitimate constraints in real flows, used correctly
every day. Nothing here says they are dishonest. The claim is narrower and
harder to argue with: **a slack number is only meaningful relative to the
constraints it was measured under, and equivalence checking does not check
those.**
