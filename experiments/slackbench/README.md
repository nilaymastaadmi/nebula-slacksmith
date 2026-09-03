# SlackBench

**An exam for verification methodologies.** Every RTL benchmark we could find
grades a *design* or a *testbench*. SlackBench grades the *checker*.

Each case is a pair of RTL modules, `gold.v` and `gate.v`, with ground truth
declared before any checker ran on it, plus a **trap class** naming the
abstraction the case is built to defeat. Your score is how well you recover
the ground truth.

## Run it

    python3 experiments/slackbench/run_bench.py --workdir ~/sbench
    python3 experiments/slackbench/run_xprop.py  --workdir ~/sbx

Needs `yosys`, `yosys-abc`, `eqy`, `sby`, `iverilog`, `vvp` (all in
OSS CAD Suite). Results land in `results/raw.tsv`.

## Point it at YOUR checker

A case is a directory. Everything a checker needs is in it:

    cases/<CASE>/gold.v      one module
    cases/<CASE>/gate.v      the same module name, transformed
    cases/<CASE>/meta.json   top, clk, rst, ports, declared k, ground truth

Your checker answers one of four things, and the fourth is not a failure:

| verdict | meaning |
|---|---|
| `ACCEPT` | the pair is equivalent |
| `REJECT` | the pair differs |
| `CANNOT` | **the question cannot be expressed** by this method |
| `ERROR` | the run broke |

`CANNOT` is first-class and is scored separately from being wrong. `abc cec`
returns it on 5 of 8 cases, because combinational equivalence checking matches
state elements one-for-one and cannot compare designs whose flop counts
differ. That is not a bug in `cec`; it is the point of the case.

To add a checker, write a function taking `(args, case, workdir)` and
returning `(verdict, detail)`, and add it to the `checkers` list in
`run_bench.py`. The existing ones are 20 to 40 lines each.

## Score it as a confusion matrix, never as one number

**A checker that answers `REJECT` to everything gets every trap right.** That
is why the suite contains correct transforms as well as broken ones, and why
a single score per checker is a misuse of it. Report four numbers: correct,
wrongly accepted, wrongly rejected, could not express.

## Ground truth, and where it is honest about being weak

- **NOT EQUIVALENT** is established by a **counterexample committed in
  `cases/MANIFEST.md`**: an input sequence and the differing output,
  replayable in any simulator, independent of every checker being scored.
- **EQUIVALENT** cannot be established without trusting something. Each such
  case records what established it. Where a case would otherwise score the
  same tool that established its truth, `meta.json` marks it `circular_for`
  and that cell is excluded.

## What is in it

Eight Tier B cases, two each in four classes, with the count **fixed before
construction** so cases could not be added once results were visible:

| class | what it defeats |
|---|---|
| LATENCY | combinational EC cannot match state across an added register |
| STIMULUS | a wrong transform that realistic simulation accepts |
| CDC | correct standalone, unsafe across a clock domain |
| CONTROL | a **correct** transform a naive checker wrongly rejects |

Plus a separately registered XPROP addendum in `cases_xprop/`, kept out of
every Tier B number because Tier B's results were already visible when it was
written.

## Limits, stated

- **Eight cases on five small designs.** These are outcomes, not rates.
- **One of the eight ground truths was wrong on first publication** and the
  first run caught it. The correction is disclosed in `NOTES.md` amendment 2
  rather than quietly applied.
- **Neither CDC case is detected as a CDC defect by anything here**, our own
  checker included. Functional equivalence has no notion of a protocol.
- **The formal stack is two-valued**, so X-optimism cannot be expressed, only
  worked around. See `NOTES_xprop.md`.
- The authors' own checker is scored here too, and gets two wrong under one
  discharge strategy. A suite its author aces would tell you about the suite.

## Files

`PREREGISTRATION.md` and `PREREGISTRATION_xprop.md` (written first),
`cases/MANIFEST.md` (ground truth and counterexamples), `run_bench.py`,
`run_xprop.py`, `NOTES.md` and `NOTES_xprop.md` (results and scoring),
`results/`.
