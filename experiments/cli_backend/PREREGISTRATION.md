# Pre-registration: does the automated backend actually work?

Registered 2026-09-11, **before** `tools/proposer.py --proposer cli` has ever
been executed. Ordering is provable:

    git log --diff-filter=A -- experiments/cli_backend/PREREGISTRATION.md
    git log -- experiments/cli_backend/results/

## Why this exists

`propose_cli()` has been committed since batch 3 with this docstring:

> **UNTESTED**: see the module docstring and the registration's void
> conditions. It is committed so the automation path is reviewable, not so it
> can be claimed as exercised.

`REPORT.md` §10 and `SUBMISSION_PACK.md` both disclose it as unexercised, and
the external review (`REVIEW_RESULT_2026-09-11.md`) scored deliverable D2
**PARTIAL** partly for this reason:

> What exists is a gated proposal checker with a human in the loop, not an
> engine that ran unattended.

The blocker was authentication, not code: `~/.claude/.credentials.json` carried
`expiresAt: 0`. A token was minted on 2026-09-11 and verified with a trivial
round trip.

## What is being tested

**One question: does the loop produce a gated proposal with no human in it?**
Not whether the proposal is good. A refuted or timing-negative proposal is a
complete answer to this experiment.

## Predictions

| # | prediction | prior |
|---|---|---|
| **C1** | `claude -p` returns output from which `_extract_json` recovers a JSON object that passes `_validate`, first attempt | uncertain. The prompt says "a single JSON object, and nothing else", and models append prose to that instruction often. `stderr` is concatenated into the parsed text and already carries two warnings on this machine |
| **C2** | the proposal reaches a **G4 verdict of any kind**, so the loop runs end to end without a human | this is the deliverable claim |
| **C3** | the proposal does **not** materially improve `clk_b` | same reasoning as R5 and R18: the binding path is 91.4% fanout-attributable and no RTL rewrite shortens a net's load delay. Registered as expected-to-hold, i.e. a prediction that the flagship result stays negative |
| **C4** | the transform proposed is **logic restructuring**, not retiming or FSM | prompt v2 offers all five branches. If the model reaches for branch 4 or 5 unprompted that is worth recording, and I expect it will not |

## Void conditions

- Editing `tools/proposer_prompt_v2.md` after seeing a result and reporting the
  re-run as this experiment.
- Running more than once and reporting the better run. **The first run is the
  run.** If it fails for an environmental reason (network, auth, a crash before
  the model is reached) that is recorded and retried; if it fails because the
  model's output was unusable, that **is** the result.

## Disclosure

Same model family as every other proposer batch in this project, and the same
standing conflict: the harness, the prompt and this registration are written by
the same session that the proposer runs in.
