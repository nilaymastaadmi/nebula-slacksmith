# The online proposer. Registered before any proposer code exists.

**Written 2026-09-05, committed before `tools/proposer.py` exists.** Git is the
evidence for that ordering, the same way `experiments/llm_proposer/` and
`experiments/cdc_gate/` do it.

## Why

`REPORT.md` §7.3 closes with a limit stated in its own words:

> **Honest limit on the phrase.** The proposer is offline: the loop selects
> from proposals frozen before any gate ran, gates and measures them, and does
> not generate them, because the anti-tuning rule forbids generating a proposal
> after seeing a gate result.

The second half of that sentence conflates two different things, and this
experiment exists because of the confusion. Pre-registration forbids **the
experimenter** changing the hypothesis, the prompt, or the scoring after seeing
results. It does not forbid **the system** producing a proposal in response to a
measurement. That is not contamination; that is the loop working.

Organizer deliverable 2 is a *GenAI-based RTL optimization engine*. A loop whose
generative step happened days earlier, by hand, is a selection engine with a
generative step bolted on the front.

## What "online" means here, precisely

At the iteration where the classifier routes to the RTL lever, the proposer is
called **with the state the design is actually in at that moment**, and returns
a transform that is then gated and measured like any other.

The proposer sees, and only sees:

1. the current OpenSTA worst-path report for the binding clock group,
2. the classifier's verdict and its evidence table for that path,
3. the **current** source of the binding module, which may already carry an
   accepted transform from an earlier iteration,
4. the typed-transform schema and the four proof-obligation branches,
5. the iteration number and the slack history so far.

The proposer does **not** see:

- any counterexample from any refuted proposal,
- the G4 verdict of any previous proposal,
- any gate output at all.

### Why that exclusion, explicitly

Feeding counterexamples back to the proposer is **batch 3**, which was
registered and then **deliberately deferred on 2026-09-02** after a literature
pass: counterexample-feedback-to-LLM for RTL is already published for
generation and repair (FormalRTL, Veri-Sure, AutoVeriFix+, HDLFORGE), so batch 3
would have been a narrow "same idea, for timing transforms" claim.

That decision stands and this experiment does not reopen it. What changes here
is **when the proposer sees the design state**, not whether it is told about its
own failures. A run that showed the model its refutations would be batch 3 under
another name, and would need its own registration and its own prior-art
argument.

## Protocol, fixed in advance

1. **Proposer.** Claude Opus 5, via the Claude Code session driving this
   project. **Identical to batches 1 and 2**, which
   `experiments/llm_proposer/PREREGISTRATION.md` §2 disclosed the same way.
   The model is not the variable in this experiment. The timing of the
   information is.
2. **Mechanism.** `tools/proposer.py` with three backends:
   - `frozen`, the existing behaviour, selecting from committed JSON;
   - `handoff`, which writes a complete request file, halts the loop, and
     resumes when a response file appears;
   - `cli`, which shells out to `claude -p` for full automation.
   **This run uses `handoff`.** The `cli` backend is written and committed but
   its OAuth session is expired on this machine, so it is untested and is
   reported as untested rather than as working.
3. **The prompt template is committed before the run** as
   `tools/proposer_prompt.md` and is **not edited after seeing any result**. If
   a run produces nothing usable because the prompt is bad, that is the result.
   A second run with a different prompt is a separate registration with its own
   N added to the trial count.
4. **N = 1 proposal per RTL-lever iteration, capped at 6 online proposals
   total.** The cap exists so the run cannot become "keep asking until
   something passes".
5. **Gates unchanged.** G0 to G6 exactly as the loop already applies them.
   Only PROVEN is accepted at G4; UNRESOLVED is not a pass.
6. **Every request and every response is committed verbatim**, including the
   ones that produce nothing.
7. **Nondeterminism is expected and is not corrected for.** The same prompt on
   the same state may yield a different transform. This run is one sample, is
   reported as one sample, and is not re-rolled. A re-run for a better outcome
   would void it.

## Registered predictions

| # | prediction | confidence |
|---|---|---|
| **O1** | At least one online proposal passes G1 through G4. Prior: 7 of 12 frozen proposals reached PROVEN. | high |
| **O2** | At least one online proposal is formally REFUTED at G4. Prior refutation rate is 3 of 12. | medium |
| **O3** | The online loop does **not** close the benchmark under SDC v3. It ends with at least one group still violating. | high |
| **O4** | Online proposals are **no better than frozen ones at G5**. The share that are both proven and improve their own group will not exceed the frozen batches' share. The null is that seeing fresh state helps correctness, not timing. | medium |
| **O5** | The online proposer proposes a **different transform class** from the frozen batches, which concentrated on operator sharing in `rv32i_core`, because the state it sees is post-physical-lever and the binding path has moved. | medium |
| **O6** | At least one online proposal will be **rejected before G4**, at parse, elaborate or precondition. Generating against live state with no human editing pass is expected to produce at least one malformed or precondition-violating transform in 6. | medium |

**O4 is the one worth registering.** The tempting claim about an online loop is
that it is better. The honest prior is that it is *the same quality, sooner*,
and that the value is architectural rather than numerical. If O4 is refuted and
online proposals really do land more improvements, that is a finding; if it
holds, the honest headline is "closing the loop did not improve the numbers"
and it will be reported that way.

## What would void this run

- Editing `tools/proposer_prompt.md` after seeing any gate result and reporting
  the re-run as this experiment.
- Re-rolling a proposal because the first one was refuted.
- Showing the proposer a counterexample or a G4 verdict, which is batch 3.
- Reporting the `cli` backend as exercised. It is not.

## Honest limits, stated before results

- **The proposer is the same session that wrote the gate.** That was true of
  batches 1 and 2 and is disclosed identically here. It is a real conflict and
  it is the reason the gate is mechanical and its verdicts are logged.
- **N is at most 6, on one design, one SDC, one model.** Outcomes, not rates.
- **`handoff` is not automation.** It proves the loop can consume a
  freshly-generated transform. It does not prove the loop can run unattended.
  The `cli` backend is the automation and it is untested here.

---

## Amendment 1, 2026-09-05, before the run and before any proposal exists

**The classifier does not route to the RTL lever on this benchmark, so the
protocol above would never call the proposer at all.**

Checked across all nine committed closed-loop logs before writing any of the
run script. Every run using the corrected classifier ends `physical_exhausted`,
and the only verdicts those runs ever produce are `FANOUT_DOMINATED` and
`MIXED`. `DEPTH_DOMINATED` appears only in runs made with the pre-correction
classifier, the one whose fanout undercount is reported in §9.

| run | gates run | ending | verdicts seen |
|---|---|---|---|
| `run_v3_fixed` | 0 | `physical_exhausted` | FANOUT, MIXED |
| `run_v3_flat` | 0 | `physical_exhausted` | FANOUT, MIXED |
| `run_v3_srcmap` | 0 | `physical_exhausted` | FANOUT, MIXED |
| `run_v3_final` | 6 | (pre-correction) | FANOUT, **DEPTH** |

This is not a new discovery. §7.3 already reports it: *"Under SDC v3 with a
correct classifier the RTL lever never fires."* It does mean the registered
protocol, as written, measures nothing.

**Resolution:** the run adds `--force-lever rtl`, which overrides the router for
one iteration so the generative path is exercised. The question this experiment
can then answer is narrowed, and the narrowing is stated rather than hidden:

> **Answered:** given a path routed to the RTL lever, can the loop generate a
> transform against live state, gate it mechanically, and measure it?
>
> **Not answered, and not claimed:** whether the router would choose RTL. It
> would not. Forcing it is disclosed in the results, in the log as
> `lever_forced`, and anywhere the run is quoted.

**Predictions O1, O2, O3, O5 and O6 are unchanged.** O4 is unchanged in wording
but its interpretation narrows with the protocol: it now compares online against
frozen proposals **on a forced-RTL path**, not across a free-running loop.

Presenting a forced-lever run as the router choosing RTL would be the
misreporting this file exists to prevent.
