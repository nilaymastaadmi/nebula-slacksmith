# Pre-registration: SlackBench, an exam for verification methodologies

Written 2026-09-03. **Committed before any new case exists and before any
checker is run on any new case.** Provable:

    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/slackbench/PREREGISTRATION.md experiments/slackbench/cases/

## What this is, and what it is not

Every existing RTL benchmark grades a *design* or a *testbench*. SlackBench
grades a **verification methodology**. Each case is a pair of RTL designs,
(gold, gate), with ground truth declared here, plus a named **trap class**
saying which checker abstraction the case is built to defeat. A checker's
score is how well it recovers the ground truth, not how fast it runs.

It is not a mutation-testing suite. `MCY` (YosysHQ, in our own toolchain)
and Certess Certitude mutate a design to grade a testbench, and discard
equivalent mutants using formal EC. SlackBench constructs transform *pairs*
to grade the checker itself, and covers two classes mutation cannot express
at all: constraint tampering, where the two designs are byte-identical, and
clock-domain-crossing violations, which are protocol properties rather than
functional ones.

## Prior art this is positioned against, and must cite

Established by a literature search before writing this file. Nothing below
is claimed as ours.

- **ROVER** (Coward, Drane, Constantinides; IEEE TCAD 2024,
  arXiv:2406.12421). E-graph datapath rewriting where each intermediate is
  discharged by a commercial equivalence checker. **Architecturally the same
  shape as SlackSmith with the e-graph replaced by an LLM.** The nearest
  landmine and cited first.
- **ElasticMiter** (Elakhras et al., ASPLOS 2025). Coq-formalised rewrites
  for latency-insensitive dataflow, stating explicitly that
  latency-insensitivity is incompatible with standard sequential
  equivalence. **This is our elastic obligation type, formalised, by someone
  else.** Our contribution there is at best an open-source instantiation.
- **EquivFusion** (arXiv:2604.16571). Derives the obligation from a scope,
  combinational or transactional. **Nearest published thing to our
  "obligation from declared transform type"**; our taxonomy is finer, four
  types against two, and that is the whole of the difference.
- **Graphiti** (ASPLOS 2026), **Vericert** (OOPSLA 2021), **Lutsig**
  (CPP 2021), **Kami**, **Koika**: certified/translation-validation lineage.
- **RealBench** (arXiv:2507.16200): **44.2% of GPT-4-Turbo Verilog that
  passes RTLLMv2 testbenches fails formal verification.** The strongest
  published statement that simulation is not an oracle.
- **Dr. RTL** (arXiv:2604.14989): 86% mean SEC pass, so **14% of its
  LLM-proposed transforms fail formal equivalence**, and it publishes no
  failure-mode case studies.

**The gap this fills, stated narrowly.** RealBench measures wrong-code
escaping simulation. Dr. RTL measures wrong-transform escaping into a
correct checker. **Nobody has measured what escapes a checker of the wrong
type.** That is the one sentence SlackBench is for.

## Tiers, because half the material is already scored

I cannot unsee results this repository already published. Pretending
otherwise would be the fraud this file exists to prevent.

- **Tier A, archival, results already known.** Cases lifted from existing
  experiments whose verdicts are committed. Included for coverage. **No
  prediction is registered about them and they are excluded from every
  headline number**, reported in a separate column.
- **Tier B, sealed.** Cases that do not exist yet. Ground truth is declared
  in this file before construction. **No checker is run on any Tier B case
  until this file is committed.** All predictions below concern Tier B only.

## Trap classes

| class | what it defeats | tier |
|---|---|---|
| LATENCY | combinational EC cannot match state elements across an added register | A + B |
| STIMULUS | a wrong transform that realistic simulation accepts | A + B |
| CONSTRAINT | slack manufactured by editing the SDC; the two designs are identical | B |
| CDC | correct standalone, violates a handshake at a domain boundary | B |
| XPROP | X-optimism hides a real mismatch from simulation | B |
| VACUITY | the checker returns PROVEN without having proved anything | A |
| CONTROL | a **correct** transform a naive checker wrongly rejects | A + B |

CONTROL is not optional. A checker that answers "not equivalent" to
everything scores perfectly on traps, so **the score is a confusion matrix,
never a single number.** Any presentation of SlackBench that reports one
number per checker is a misuse of it.

## Ground truth, and where it is circular

This is the weakest joint in the design and is stated rather than hidden.

- **NOT EQUIVALENT** is established by a **committed counterexample**: an
  input sequence plus the differing output, replayable in any simulator,
  independent of every checker being scored. This is sound.
- **EQUIVALENT** cannot be established without trusting some prover. Each
  such case records the method and the tool that established it, and **a
  case is never used to score the same tool that established its ground
  truth.** Where that cannot be avoided the case is marked `CIRCULAR` and
  excluded from that checker's row.

## Checkers scored

`abc cec`, `abc dsec`, EQY, simulation with the design's own testbench,
simulation with aggressive random stimulus, the SlackSmith typed gate
(G1 to G5), and G0 constraint integrity. Every checker gets a **positive
control first**: if it cannot pass a known-good pair, the setup is broken
and its row is void rather than reported as a failure.

## Size, fixed now

**Tier B is exactly 8 cases**, two each in LATENCY, STIMULUS, CDC and
CONTROL, plus the CONSTRAINT and XPROP cases counted inside those two. The
count is fixed here so that cases cannot be added until a tool looks bad.
If a case turns out to be unbuildable it is reported as unbuilt, and **not
replaced**.

## Predictions, Tier B only

1. `abc cec` fails to construct the miter on both LATENCY cases, rather
   than returning "not equivalent". High.
2. At least one STIMULUS case is accepted by the design's own testbench and
   refuted by EQY. High.
3. **Every checker except G0 scores zero on the CONSTRAINT case**, because
   the two designs are byte-identical. Near-certain, registered as a wiring
   check on the harness.
4. **No checker scored here catches the CDC case**, including ours. Medium.
   Our gate proves module-level equivalence and has no notion of a
   handshake protocol, so we expect to fail our own exam here.
5. At least one CONTROL case is wrongly rejected by at least one formal
   checker. High: `experiments/cec_check/` already shows three checkers
   rejecting a correct latency change, though that instance is Tier A.
6. The SlackSmith typed gate does **not** score perfectly. Medium-high, and
   registered because a suite on which its author scores 100% is evidence
   the suite was built to flatter it.

Prediction 6 is the one that matters. **If our gate sweeps Tier B, the
honest report is that SlackBench is too easy, not that SlackSmith is
excellent.**

## What would make this void

- Adding, removing or editing a Tier B case after any checker has run on it.
- Reporting a Tier B headline that includes Tier A cases.
- Reporting a single score per checker instead of a confusion matrix.
- Using a case to score the tool that established its ground truth without
  the `CIRCULAR` exclusion.

## Amendment 1, 2026-09-03, before any Tier B case is built

The size clause above says "exactly 8 cases, two each in LATENCY, STIMULUS,
CDC and CONTROL, plus the CONSTRAINT and XPROP cases counted inside those
two." **"Those two" has no referent. That is my drafting error**, caught on
re-reading before construction, and it is resolved here rather than left to
be resolved conveniently later.

Resolution, and the reasoning:

- **Tier B is the eight cases**, two each in LATENCY, STIMULUS, CDC and
  CONTROL. The list is fixed in `cases/MANIFEST.md`, written before any
  checker runs.
- **CONSTRAINT moves to Tier A.** Its measurement already exists in
  `experiments/sdc_integrity/`, taken earlier the same day and before this
  registration was committed. By this file's own rule I cannot unsee it, so
  it is archival and excluded from Tier B headlines. It is still reported,
  because it is the only class no equivalence checker can catch.
- **XPROP is not built and is reported as absent.** It was named in the
  class table and never allocated a slot in the size clause. Adding a ninth
  case now would break the fixed count, which exists precisely so cases
  cannot be added once results are visible. It is listed as a known gap in
  the suite rather than quietly dropped from the class table.

Predictions 1 to 6 are unchanged. Prediction 3 concerns the CONSTRAINT case
and is now scored against Tier A, which weakens it to a wiring check on the
harness, which is all it ever was.
