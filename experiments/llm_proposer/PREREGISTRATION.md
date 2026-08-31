# Pre-registration: LLM-proposed RTL transforms through the SlackSmith gate

Written 2026-08-31, **before any proposer code or any proposal exists**. Git
proves the ordering:

    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/llm_proposer/PREREGISTRATION.md \
      experiments/llm_proposer/proposals/

This file must appear in an earlier commit than every file in `proposals/`
and than any harness code. If it does not, this registration is void and the
experiment must be reported as unregistered.

## The question

The abstract claims an LLM proposes typed transforms and a formal gate
disposes. That has never been measured. Every transform proven so far
(4 of 4) was proposed by hand, by a human with full project context, and
each was refined until it passed. That is a demonstration, not evidence
about LLM proposals.

**Question:** when an LLM proposes RTL transforms against a real timing
report with no opportunity to iterate, what fraction survive each gate, and
what does the four-checker matrix say about the ones that fail?

## Protocol, fixed in advance

1. **Target.** The module containing the worst reg-to-reg path on the v2
   benchmark, which is `rv32i_core` (instantiated as `u_rv32_a/u_core`).
   Worst path 28.374 ns arrival against an 8 ns period, post-`lpflow` fix.
2. **Proposer.** Claude Opus 5, via the Claude Code session driving this
   project. Disclosed, not disguised: the model is given the OpenSTA
   critical-path report, the target RTL, and the typed transform schema, and
   emits proposals as structured JSON plus complete rewritten module source.
3. **N = 6 proposals**, generated in a single batch.
4. **The anti-tuning rule, which is the point of this registration:** all 6
   proposals are committed **before any gate is run**. No proposal may be
   edited, replaced, or withdrawn after seeing any gate result. If a proposal
   fails, it is reported as failed. The commit containing `proposals/` must
   precede the commit containing any result.
5. **Gates, applied mechanically in order.** Each proposal gets every gate it
   survives, and the outcome of each is recorded:
   - G1 parse: Yosys reads the rewritten module without error.
   - G2 elaborate: synthesizes, cell count recorded, zero latches.
   - G3 precondition: the declared transform type's preconditions, checked
     mechanically per the transform library design doc.
   - G4 formal: the obligation implied by the declared transform type
     (branch 1 EQY / branch 2 k-padded miter / branch 3 stream equivalence /
     branch 4 mapped-state), run through `tools/run_proof.py` with the
     standard engine portfolio, plus a `cover` check where the property is
     guard-gated.
   - G5 timing: `tools/remeasure.py` on the path group the transform touches,
     for proposals that reach this gate only.
6. **The four-checker column.** For every proposal that G4 refutes, the same
   pair is additionally given to `abc cec`, `abc dsec`, EQY, and a
   simulation testbench, to record which weaker checkers would have accepted
   an invalid rewrite. This is the project's differentiating measurement and
   it is registered here as a primary output, not a bonus.

## The bar, fixed in advance

**Primary:** at least 1 of 6 proposals passes G1 through G4 and improves
slack on the touched path group at G5.

**Reported regardless of the bar:** the full 6-row outcome matrix. A result
of 0 of 6 is a publishable finding about LLM-proposed RTL and will be
reported as prominently as a success. This experiment cannot fail to produce
a result; it can only fail to produce a flattering one.

**Not permitted:** re-running with a different prompt after seeing results
and reporting it as this experiment. If a second batch is generated, it is
registered separately, its N is added to the trial count, and both batches
are reported.

## Trial count and the multiple-testing bar

Prior transform trials in this project: 4 (fsm_reencode,
mux_priority_to_parallel, pipeline_cut_domain_a, pipeline_cut_elastic). This
batch adds 6, so N = 10 after it. The bar is not statistical here (each
proposal is a deterministic pass/fail against a formal gate, not a sampled
estimate), so no significance threshold applies. The count is recorded so a
later session cannot start a fresh "family" of proposals after a bad batch
and report only the good one.

## Predictions, recorded so the misses are visible

1. **≥5 of 6 parse and elaborate (G1, G2).** Confidence: high. Modern LLMs
   write syntactically valid Verilog reliably.
2. **≥1 of 6 is rejected at G3 precondition.** Confidence: high. The
   preconditions exist precisely because plausible-looking transforms violate
   them.
3. **≥1 of 6 is formally REFUTED at G4.** Confidence: high, and this is the
   most valuable single outcome: a transform that looks correct, passes
   parse and precondition, and is caught only by the formal gate is the
   entire thesis of the project demonstrated on real LLM output rather than
   on a hand-built mutant.
4. **≤2 of 6 improve timing at G5.** Confidence: medium. Deliberately
   pessimistic: the pipeline_cut_domain_a result already showed a proven
   transform making timing worse.
5. **The dominant failure mode will be timing/latency semantics (a
   transform that changes when a value appears), not syntax or Boolean
   logic.** Confidence: LOW. This is the prediction most likely to be wrong,
   and it is recorded specifically so that being wrong about it is visible
   rather than quietly forgotten. The plausible alternative is that the
   dominant failure is width/truncation handling.

## What would make this experiment void

- Any proposal edited after a gate result is seen.
- Gates run in a different order than G1 to G5, or a gate skipped for a
  proposal that reached it.
- Reporting a subset of the 6.
- The git ordering check at the top of this file failing.
