# SlackSmith

**Latency-changing RTL optimization with automatically generated proof obligations.**

Entry for *Nebula*, Astera Labs @ BITS Pilani Goa. Track A (Digital):
*Constraint Optimization through RTL Enhancement Using Generative AI*.

Nilay Toshniwal and Shivani Chaudhary.
Full write-up: **[REPORT.md](REPORT.md)**. Demo shot list: **[DEMO.md](DEMO.md)**.

---

## The idea

Transforms are **typed**. The model does not emit free-text Verilog and hope; it
declares a transform type, and that declaration mechanically selects the proof
obligation:

| declared | obligation | discharged by |
|---|---|---|
| k = 0, state-preserving | combinational / sequential equivalence | EQY, `abc dsec` |
| k > 0, rigid interface | k-padded miter | SymbiYosys, BMC + PDR |
| k > 0, elastic interface | stream equivalence | SymbiYosys + `cover` |
| k = 0, re-encoded state | mapped-state equivalence | SymbiYosys + bijection |

All four branches are proven on real RTL. Latency-changing transforms become
checkable, which is what the published systems avoid.

## What we actually measured, which is the point

We built both halves and then measured the half everyone assumes works. An LLM
pointed at a timing report fails **two** different ways.

**1. It proposes things that are wrong.** Two pre-registered batches, N = 12,
every proposal frozen before any gate ran (git proves the ordering). 3 formally
refuted, 1 rejected at precondition, 1 unresolved. The best one:

| checker on proposal P4 | verdict |
|---|---|
| EQY formal | **CAUGHT** in 46 s, counterexample `a=ae19f605, shamt=7` |
| the design's own shipped firmware, 400 cycles | **MISSED** |
| 20,000 random instruction words | **MISSED** |
| directed SRAI on a negative operand | CAUGHT |

P4 saves 208 cells, passes every precondition, and breaks SRA for every
negative operand. The file it edits carries a comment warning about exactly
that defect, ten lines above the code it changed.

**2. It aims correct transforms at the wrong variable.** The binding paths on
this benchmark are **59% to 91% fanout-attributable delay**, and no RTL rewrite
shortens a net's load delay:

| lever, same clock group, same SDC | clk_b gain | changes RTL? | parasitics? |
|---|---|---|---|
| best LLM RTL transform, batch 1 | +0.485 | yes | no |
| best LLM RTL transform, batch 2 | +4.925 | yes | no |
| ABC buffering control | +17.557 | no | no |
| **OpenROAD `repair_design`** | **+55.805** | **no** | **yes** |

So SlackSmith routes **twice**: the fix by measured path pathology, the proof
obligation by declared transform type.

**3. And we tested that on designs we did not write.** The 20 human-written
designs published with Dr. RTL (ICCAD 2026), pre-registered, same flow, same
unchanged thresholds: 15 in scope, **5 FANOUT / 3 MIXED / 7 DEPTH** after a
classifier correction (2026-09-03, 1 verdict changed), byte-identical across
two independent runs. The physical lever closed **5 of 5** fanout-dominated
designs outright and 4 of 7 depth-dominated ones, with a 6.2x higher median
gain on the former. Three of five registered predictions were wrong,
including the primary one, and the write-up says exactly how.
`experiments/drrtl_transfer/`.

**4. The tool's own log caught its worst bug.** The classifier had been
undercounting fanout across module boundaries; a 6.762 ns cell it recorded
at fanout 1 drives 387 loads. Every DEPTH verdict it gave on this benchmark's
post-buffering paths was wrong, the fix is regression-checked against
OpenSTA's own fanout column, and the wrong logs are kept.
`tools/classify_regression.py`, `docs/closed-loop.md`.

**5. The flow was the biggest lever.** Flattening before ABC moves `clk_a`
by +22.4 ns with no buffering at all; flat plus buffering closes 2 of 3
groups under SDC v3 and leaves `clk_e` at −0.319. Every earlier number is a
hierarchical-flow number and is labelled so. `experiments/flatten_control/`.

**6. Two gates nothing else in this class has.** **G0, constraint
integrity**: one `set_multicycle_path` line takes a group from −0.319
VIOLATED to +4.860 MET on a byte-identical netlist, which is more than our
best proven RTL transform bought and which **no equivalence checker can
catch**, because the two designs are the same file. The loop now hashes the
SDC, counts its timing exceptions, and can refuse. **G6, physical
equivalence**: `repair_design`'s output is proven equivalent to its input,
5,832 compare points in 38 seconds, after four failed attempts whose causes
are all named. A physical step whose logic we cannot vouch for now stops the
loop. `experiments/sdc_integrity/`, `tools/lec_check.py`.

**7. We built the exam and published our own score on it.** SlackBench is a
suite of RTL transform pairs with declared ground truth, built to defeat
specific checker abstractions, used to grade **verification methodologies**
rather than designs or testbenches. The literature search found nothing like
it. Our own checker gets two of eight wrong, which was registered in advance,
because a suite its author aces is evidence the suite was rigged.
`experiments/slackbench/`.

## Run it

    git clone <repo> && cd slacksmith-benchmark
    bash tools/preflight.sh      # names any missing dependency and where to get it
    bash tools/demo_check.sh     # all 8 demo beats, 12 assertions

Or the tool on its own:

    python3 tools/slacksmith.py \
      --sdc sdc/bench_top_v2.sdc \
      --clock clk_a --clock clk_b --clock clk_e \
      --workdir ~/run --engine sta

Closes the benchmark in **2 iterations, 46.7 seconds**, and writes every
routing decision with its evidence to `decisions.jsonl`.

Tool paths come from environment variables with defaults (`OSS_CAD_BIN`,
`STA_BIN`, `LIBERTY`, `OPENROAD_BIN`). **[SETUP.md](SETUP.md)** lists them, the
versions the committed results were measured with, and specifically which
claims you can re-derive in minutes and which would cost you an afternoon of
synthesis. Clone rather than downloading a zip: one demo assertion checks that
the pre-registration commit precedes the results commit, which needs history.

## The benchmark

`bench_top`, **55,413 standard cells**. Five asynchronous domains, each with
its own async reset and its own in-RTL generated clock including odd /3 and /5
dividers. Gray-code async FIFOs on every multi-bit crossing, two-flop
synchronizers on every single-bit one. An RV32I core and two AES-128 cores.
The SDC is written once and frozen; no `set_multicycle_path` anywhere, because
a multicycle exception manufactures slack without changing the design.

## Layout

```
REPORT.md                  the submission. tools/render_report.py measures its page count
DEMO.md                    shot list for the demo video
rtl/                       bench_top and its five domains; rtl/aes is vendored, BSD-2
sdc/                       v1 frozen, v2 closure targets, v3 generated by make_v3.py
tools/  slacksmith.py      the closed loop
        classify_path.py   routes the fix by fanout-attributable delay share
        gate_proposal.py   routes the obligation by declared type, runs G1 to G4
        remeasure.py       synthesis + STA, with the null control that has 0.000 noise
        verdict_regression.sh  P4 must read REFUTED, A2 must read UNRESOLVED
docs/   measurement-methodology.md   four findings that changed how we report numbers
        path-classification.md       the classifier, its 5-case validation, its 2 limits
        closed-loop.md               the loop, and the bugs running it exposed
experiments/               every number above, with the command that produced it
```

## What we got wrong

Kept deliberately, because a submission that cannot show its corrections is
not measuring anything. Full list in REPORT.md §9. The two worth naming here:

**Our own gate reported a solver timeout as a refutation.** EQY prints the same
line for a counterexample and for running out of depth, and we matched on the
string. Caught only because a partition failed while all 128 partitions feeding
it had passed. `tools/verdict_regression.sh` now pins both directions.

**Every number we published before 2026-09-01 was zero-parasitic.** With
placement parasitics the `clk_a` baseline we reported as "+1.333, meets" is
**−36.723**. The baseline-versus-variant comparisons survive, because both
sides always used one consistent model. The absolute closure claims did not.

## Honest limits

- The proposer is offline. The loop selects, gates and measures proposals
  frozen before any gate ran. It does not generate them, because the
  anti-tuning rule in both pre-registrations forbids generating a proposal
  after seeing a gate result.
- `repair_design`'s equivalence is **not** verified. Three attempts failed for
  tooling reasons and none produced a counterexample, which is not the same as
  passing. See `experiments/openroad_repair/NOTES.md`.
- The classifier's thresholds were chosen after looking at this benchmark.
  They are not validated on any held-out design.
- N = 12 proposals, one proposer model. These are outcomes, not rates with
  confidence intervals.
