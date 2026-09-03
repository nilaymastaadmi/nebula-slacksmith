# SlackBench Tier B: results

Registered at `5c88521`, amended at `0b7e3fe`, cases committed at `c9786f2`
**before any checker ran on them**. Harness `run_bench.py`, raw output in
`results/raw.tsv`.

## The matrix

`ACCEPT` = the checker says the pair is fine. `REJECT` = it says they differ.
`CANNOT` = it cannot express the question at all. Bold marks a **wrong**
answer against the manifest's ground truth.

| case | truth | cec | dsec | sim_lazy | sim_aggr | miter_k |
|---|---|---|---|---|---|---|
| LATENCY-1 | EQUIVALENT (k=+1) | CANNOT | CANNOT | ACCEPT | ACCEPT | ACCEPT |
| LATENCY-2 | NOT EQUIVALENT | CANNOT | CANNOT | **ACCEPT** | REJECT | REJECT |
| STIMULUS-1 | NOT EQUIVALENT | REJECT | REJECT | **ACCEPT** | **ACCEPT** | REJECT |
| STIMULUS-2 | NOT EQUIVALENT | CANNOT | CANNOT | REJECT | REJECT | REJECT |
| CDC-1 | EQUIVALENT (k=−1), see amendment 2 | CANNOT | CANNOT | ACCEPT | ACCEPT | ACCEPT |
| CDC-2 | EQUIVALENT | **REJECT** | **REJECT** | ACCEPT | ACCEPT | **REJECT** |
| CONTROL-1 | EQUIVALENT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| CONTROL-2 | EQUIVALENT | CANNOT | CANNOT | ACCEPT | ACCEPT | **REJECT** |

Counts, and this is why the score is never one number:

| checker | correct | wrongly ACCEPTED | wrongly REJECTED | could not express |
|---|---|---|---|---|
| `abc cec` | 2 | 0 | 1 | 5 |
| `abc dsec` | 2 | 0 | 1 | 5 |
| sim, lazy stimulus | 6 | **2** | 0 | 0 |
| sim, aggressive | 7 | **1** | 0 | 0 |
| miter_k (ours) | 6 | 0 | **2** | 0 |

## What the suite actually found

**1. A wrong transform survived 40,000 simulated cycles.** STIMULUS-1 is
wrong on one input pair in 65,536. Both simulation regimes accepted it, 20,000
vectors each. Every formal checker that could express the question refuted it,
`cec` and `dsec` in well under a second. This is the escape RealBench measures
at 44.2% on generated code, reproduced here on a *transform* with the exact
input pair published in advance.

**2. Combinational and sequential EC could not express 5 of 8 questions.**
Every CANNOT is evidenced by latch counts rather than asserted: LATENCY-2 is
17 latches against 33, CONTROL-2 is 3 against 4. This is the registered
prediction 1 and the reason the typed router exists at all.

**3. `cec` and `dsec` both raised a false alarm on CDC-2.** That pair is
equivalent by an algebraic argument, `gray(delay(x))` equals `delay(gray(x))`,
and 19,998 simulated cycles agree. Both tools report NOT EQUIVALENT because
they match latches positionally and the state now holds binary where it held
gray. **A checker answering a different question than the one asked can be
confidently wrong**, and neither tool signals that it changed the question.

**4. Our own checker is wrong twice, which was registered in advance.**
`miter_k` false-alarms on CDC-2 for the same latch-correspondence reason, and
on CONTROL-2, the one-hot re-encoding. CONTROL-2 is the honest one: SlackSmith's
type router is *supposed* to send a re-encoded design to the mapped-state
obligation, and **this harness implements only two of the four branches**, the
plain sequential miter and the k-padded one. That is a gap in the harness, not
a defence, and it is scored as a miss rather than excused. Prediction 6 said
our gate would not sweep its own suite; it did not.

**5. Neither CDC defect was detected as a CDC defect by anything.** CDC-1's
missing metastability guard is invisible to all five. CDC-2 was rejected by
three of them for a reason that has nothing to do with the crossing. Prediction
4 holds, including for us: **SlackSmith proves module-level equivalence and has
no notion of a protocol.**

## Predictions, scored

1. **Correct.** `cec` returns CANNOT on both LATENCY cases rather than a verdict.
2. **Correct with a substitution, stated.** STIMULUS-1 is accepted by the lazy
   testbench and refuted by formal. EQY itself was **not run**; `cec` and `dsec`
   stand in, and the prediction named EQY, so this is a partial credit at best.
3. **Correct**, and trivially so. Moved to Tier A by amendment 1: no checker
   here can see a constraint edit, and G0 is the only thing that can.
4. **Correct.** No checker identified either CDC defect as a CDC defect.
5. **Correct.** CONTROL-2, a correct re-encoding, is wrongly rejected by three
   checkers including ours.
6. **Correct.** Our miter is wrong on 2 of 8.

Six of six, which is itself a warning sign: predictions this safe are not
evidence of much. The informative results are the two that were not predicted,
the `cec`/`dsec` false alarm on CDC-2 and the fact that aggressive random
stimulus still missed STIMULUS-1.

## Amendment 2, after the first run: CDC-1's declared ground truth was wrong

**This is an after-the-fact edit to a case's ground truth, which the
registration's void conditions warn about, so it is disclosed loudly rather
than quietly applied.**

`MANIFEST.md` declared CDC-1 NOT EQUIVALENT with k=−1. It is **EQUIVALENT**
under that offset: the padded miter proves it, and both simulation regimes
agree over 19,997 cycles. The label was internally inconsistent with the
manifest's own rule from the moment it was written, because that rule requires
a committed counterexample for every NOT EQUIVALENT case and CDC-1 never had
one. The error was in the declaration, not in the measurement.

What changes: CDC-1's truth becomes EQUIVALENT (k=−1), matching LATENCY-1's
shape. What does not change: any prediction outcome, any other case, or the
point of the case, which is that removing a synchronizer stage is a latency
change to every functional checker and a metastability defect in the silicon.

The correct reading of this suite is therefore that **one of its eight ground
truths was wrong on first publication and the harness caught it**, which is
the same class of finding as everything else in this repository.

## Known gaps

- **EQY is not among the checkers run.** Prediction 2 named it. `cec`, `dsec`
  and the miter are what actually ran.
- **XPROP has no case**, per amendment 1.
- **Two of four obligation branches are implemented in this harness**, so
  CONTROL-2 is scored against a branch SlackSmith would not have chosen.
- **Eight cases on five small designs.** These are outcomes, not rates.
