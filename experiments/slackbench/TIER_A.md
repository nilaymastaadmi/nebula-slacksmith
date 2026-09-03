# SlackBench Tier A: the archival column

`PREREGISTRATION.md` promised this and it was outstanding until now: cases
lifted from experiments whose verdicts were already committed, **included for
coverage, carrying no prediction, and excluded from every Tier B number.**

**Why they are quarantined.** I could not unsee these results, so they cannot
test anything. Presenting them alongside Tier B's sealed cases as if both were
blind would be the fraud the tier split exists to prevent. They are here
because they widen what the suite demonstrates, and for no other reason.

Nothing below is a new measurement. Every row is a pointer to a committed
experiment, assembled into one table for the first time.

## The column

| # | case | class | truth | what happened | source |
|---|---|---|---|---|---|
| A1 | `mac_ref` vs `mac_opt`, k=+1 | LATENCY / CONTROL | EQUIVALENT | `cec` **cannot build the miter**; `dsec` says **NOT EQUIVALENT**; EQY **FAILs**; the k-padded miter proves it unbounded. Three checkers reject a correct transform, each for a different reason | `experiments/cec_check/` |
| A2 | `mut0_correct` | STIMULUS control | EQUIVALENT | lazy PASS, aggressive PASS, formal PASSED. Everything accepts it | `experiments/sim_check/` |
| A3 | `mut1_stale_c` | STIMULUS | NOT EQUIVALENT | **lazy testbench PASSES**, aggressive FAILs, formal FAILED. The classic pipelining bug, invisible when the accumulate operand is held constant | `experiments/sim_check/` |
| A4 | `mut2_rare` | STIMULUS | NOT EQUIVALENT | **both testbenches PASS**, formal FAILED. Wrong on roughly one input in a million; 20,000 vectors is an expected 0.019 hits, so escaping is the reliable outcome, not luck | `experiments/sim_check/` |
| A5 | `mut3_trunc` | STIMULUS | NOT EQUIVALENT | lazy FAIL, aggressive FAIL, formal FAILED. Included deliberately: simulation is not useless, and a matrix where it never works would be rigged | `experiments/sim_check/` |
| A6 | **P4**, a real LLM proposal | STIMULUS | NOT EQUIVALENT | EQY **caught it in 46 s** with a concrete counterexample. The design's own shipped firmware, 400 cycles: **MISSED**. 20,000 random instruction words: **MISSED**. A directed SRAI on a negative operand: caught | `experiments/llm_proposer/fourchecker/` |
| A7 | stream equivalence on a deadlocking FIFO | VACUITY | the checker was wrong | The checker returned **PROVEN in 0 seconds** for a design that never produces output. The assert was guarded on "both sides completed a transaction" and was vacuously true forever. Fixed with a `cover` property | `experiments/sync_fifo_stream/` |
| A8 | one SDC line, identical netlist | CONSTRAINT | the design did not change at all | `clk_e` goes **−0.319 VIOLATED to +4.860 MET**, worth +5.179 ns, on a byte-identical 26,958-cell netlist. **Every equivalence checker correctly calls these equivalent, because they are the same file.** Only G0 can see it | `experiments/sdc_integrity/` |

## What the column adds that Tier B does not

**A6 is the one that matters most, and Tier B has no equivalent.** Every Tier
B case is a transform *I* wrote to defeat a checker. A6 is a transform an LLM
actually proposed against a real timing report, which parses, elaborates,
passes every precondition and reduces cell count, and is wrong. The two
misses are not strawmen: one is the design's own firmware and the other is
20,000 random instructions, and a directed probe confirms the defect is fully
visible to simulation, so both misses are stimulus weakness rather than a
phantom.

**A7 is a checker failing in the dangerous direction.** Every other row here
is a checker being too weak or too strict. A7 is one returning PROVEN while
proving nothing, which is the failure no amount of running it more would
reveal.

**A8 is outside what any equivalence checker can be asked.** It is the only
row where every checker is *correct* and the reported number is still a lie.

## What it does not add

- **No prediction was registered about any of it**, so none of it tests
  anything. It illustrates.
- **A2 to A5 are hand-built mutants**, chosen by me to span failure modes
  rather than sampled from real model output. n=4 is not a rate.
- **A1's checkers are the same tools Tier B scores**, so this row is
  consistent with Tier B rather than independent evidence for it.
- Combining these eight with Tier B's eight to claim "sixteen cases" would be
  the headline the registration forbids. They are two different kinds of
  thing and the counts stay separate.
