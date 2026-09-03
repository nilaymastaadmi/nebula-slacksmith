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
2. **Superseded, see the update below: WRONG.** EQY was not run at the time
   this line was written and `cec`/`dsec` were substituted. With EQY actually
   run it declines STIMULUS-1 rather than refuting it.
3. **Correct**, and trivially so. Moved to Tier A by amendment 1: no checker
   here can see a constraint edit, and G0 is the only thing that can.
4. **Correct.** No checker identified either CDC defect as a CDC defect.
5. **Correct.** CONTROL-2, a correct re-encoding, is wrongly rejected by three
   checkers including ours.
6. **Correct.** Our miter is wrong on 2 of 8.

Six of six as scored here, which was itself a warning sign. Running EQY
afterwards turned prediction 2 into a miss, so the real tally is **5 of 6**;
see the update below.

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

- **XPROP has no case**, per amendment 1.
- **Two of four obligation branches are implemented in this harness**, so
  CONTROL-2 is scored against a branch SlackSmith would not have chosen.
- **Eight cases on five small designs.** These are outcomes, not rates.

---

# Update: two checkers added, and the reachability result

EQY and a PDR discharge were added **after** the first run and are marked as
such. No case was touched; the registration's void conditions protect the
cases, not the checker list. EQY was added because prediction 2 named it and
its absence was the suite's most conspicuous hole. PDR was added because
`miter_k`'s two false alarms both smelled like an induction artifact rather
than a real disagreement.

Two harness bugs of mine were fixed first, and both were bugs rather than
findings: the EQY config used an option EQY does not have, and the PDR run
rejected even a trivially equivalent pair because a proof engine starts from
an **arbitrary** state and nothing in the miter forced a reset. The miter now
carries an initialised boot counter that holds reset low for two cycles.

## The full matrix

| case | truth | cec | dsec | eqy | sim_lazy | sim_aggr | miter_k | miter_pdr |
|---|---|---|---|---|---|---|---|---|
| LATENCY-1 | EQ | CANNOT | CANNOT | CANNOT | ACCEPT | ACCEPT | ACCEPT | CANNOT |
| LATENCY-2 | NOT EQ | CANNOT | CANNOT | CANNOT | **ACCEPT** | REJECT | REJECT | REJECT |
| STIMULUS-1 | NOT EQ | REJECT | REJECT | CANNOT | **ACCEPT** | **ACCEPT** | REJECT | REJECT |
| STIMULUS-2 | NOT EQ | CANNOT | CANNOT | CANNOT | REJECT | REJECT | REJECT | REJECT |
| CDC-1 | EQ | CANNOT | CANNOT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| CDC-2 | EQ | **REJECT** | **REJECT** | CANNOT | ACCEPT | ACCEPT | **REJECT** | ACCEPT |
| CONTROL-1 | EQ | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| CONTROL-2 | EQ | CANNOT | CANNOT | ACCEPT | ACCEPT | ACCEPT | **REJECT** | ACCEPT |

| checker | correct | wrongly ACCEPTED | wrongly REJECTED | could not express |
|---|---|---|---|---|
| `abc cec` | 2 | 0 | 1 | 5 |
| `abc dsec` | 2 | 0 | 1 | 5 |
| EQY | 3 | 0 | **0** | 5 |
| sim, lazy | 6 | **2** | 0 | 0 |
| sim, aggressive | 7 | **1** | 0 | 0 |
| miter, induction | 6 | 0 | **2** | 0 |
| miter, PDR | **7** | 0 | **0** | 1 |

## The finding this update produced

**Both of our false alarms were an induction artifact, not a disagreement.**
Temporal induction quantifies over *all* states including unreachable ones. A
one-hot register is never `011`, and the gray/binary synchronizer never holds
an inconsistent pair, but induction is free to start there and report a
counterexample that no execution can reach. PDR computes reachability and
both false alarms disappear: CDC-2 and CONTROL-2 both prove, unbounded.

This is the same split this repository already measured a month earlier in
`experiments/fsm_reencode/`, where `prove` did not close and `pdr` did on the
identical property. **We had the result and did not carry it forward into the
gate.** The practical consequence is that the fourth obligation branch does
not need a hand-supplied state bijection to work on these cases; it needs a
reachability-aware engine.

**PDR is right on 7 of 8 and wrong on none**, at the cost of one timeout on
the k=+1 pipeline cut with a 16-bit multiplier in its cone. That is the
honest trade: the engine that never lies is the one that sometimes declines.

**EQY never gives a wrong answer either.** It proves 3 and declines 5,
including CONTROL-2, the one-hot re-encoding that `cec` and `dsec` cannot
express at all and that our own induction-based miter wrongly rejects. Its
declines are all "failed to prove, no counterexample", which our gate's
standing rule already treats as UNRESOLVED rather than a refutation, and this
suite is exactly why that rule exists.

## Prediction 6, re-scored honestly

Our tool is two tools here. Discharged by induction it is **wrong twice**.
Discharged by PDR it is **wrong zero times but declines once**. Neither is a
perfect score, so prediction 6 holds either way, and reporting only the PDR
row would be the cherry-pick the registration exists to prevent.

## Prediction 2 is now scored properly, and it is WRONG

Prediction 2 read: "At least one STIMULUS case is accepted by the design's own
testbench and **refuted by EQY**." With EQY actually run, STIMULUS-1 is
accepted by the lazy testbench and EQY **declines** it: "failed to prove, no
counterexample". EQY refutes neither STIMULUS case. The first half holds and
the named checker does not do what the prediction said.

**So the score is 5 of 6, not 6 of 6**, and the earlier write-up recorded it
as "correct with a substitution" only because the checker the prediction named
had not been run. That substitution was the wrong call and this supersedes it.
The corrected tally:

1. correct, 2. **WRONG**, 3. correct, 4. correct, 5. correct, 6. correct.

This is a better outcome than 6 of 6. A prediction set with a miss in it is
evidence the predictions were doing work.

## Known gaps, updated

- **XPROP still has no case**, per amendment 1.
- **The suite's own ground truth needed one correction** (amendment 2).
- **PDR times out on one case**, so its 7 of 8 comes with a decline.
- **Eight cases on five small designs.** Outcomes, not rates.
- Superseded: "EQY is not among the checkers run" and "two of four obligation
  branches" no longer hold. EQY runs, and the reachability engine removes the
  need for the hand-supplied bijection on these cases.
