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

---

## Attempt 1, 2026-09-11: environmental failure, recorded and retried

    PermissionError: [Errno 13] Permission denied: ''

`run.sh` resolved the binary with `$(command -v claude)`. The script is invoked
non-interactively (`wsl -e bash run.sh`), which is **not** a login shell, so
`~/.profile` never runs and `~/.local/bin` is absent from `PATH`. The empty
string went straight into `subprocess.run`.

**The model was never reached.** Under this registration's void conditions that
is an environmental failure, so it is recorded and retried rather than counted
as the result. Log kept at `results/attempt1_environmental_failure.log`.

Fixed by resolving the binary explicitly and **failing loudly** if it is not
found, rather than handing an empty program name to a subprocess. `propose_cli`
already returns a clean error for `FileNotFoundError`; an empty string raises
`PermissionError` instead and slipped past it.

Predictions C1 to C4 are unchanged and unseen.

---

## Attempt 2, 2026-09-11: the run completed with no human in it

    claude: /home/toshn/.local/bin/claude
    === iteration 1 ===
    measure: clk_b=-18.957
    classify clk_b: FANOUT_DOMINATED (fanout share 0.9139) -> physical
      LEVER FORCED to rtl
      online proposal O1: fanout_replication_round_key_update (declared k=0)
      gate O1: G3=PASS G4=PROVEN
      G7 O1: SKIPPED (aes_key_mem has no clock crossings)
      APPLY O1 provisionally
    1 iterations, 456.1s

| # | registered | outcome |
|---|---|---|
| **C1** | valid JSON on the first attempt | **CONFIRMED.** `_extract_json` and `_validate` both passed first try, with two warnings and a failing hook message mixed into the captured text |
| **C2** | the proposal reaches a G4 verdict of any kind | **CONFIRMED. PROVEN.** The loop measured, classified, proposed, gated and applied with no human in it |
| **C4** | the transform is logic restructuring, not retiming or FSM | **CONFIRMED.** `fanout_replication_round_key_update`, declared branch 1 |
| **C3** | no material improvement to `clk_b` | **NOT YET MEASURED.** `--max-iters 1` stopped the run after the provisional apply, before the confirm-or-revert re-measure |

**D2's disclosure changes.** "The automated backend is committed unexercised"
is no longer true. N = 1, one design, one sample, and the run is preserved at
`results/run1/` with its request, its raw response, the variant and the
decision log.

### What the model proposed, and why C3 now matters more than it did

Its own rationale:

> The single-bit reg `round_key_update` gates one combined if-block that drives
> ~384 bit-positions [...] matching the reported 300-fanout nor4 on the
> critical path. Splitting it into two buffer-duplicated copies [...] halves
> the load per net.

**It went straight at the 300-load net**, which is the correct engineering
response to a `FANOUT_DOMINATED` verdict and a sharper choice than the retiming
this session wrote by hand for the same module.

That makes C3 a test of **this project's central negative claim**, not a
footnote. §1 and §7.2 say no RTL rewrite shortens a net's load delay. This is an
RTL rewrite whose entire purpose is to shorten a net's load delay, and it is
formally proven correct.

**Registered mechanism, before the number exists.** I expect C3 to hold, and
for a specific reason: the two "buffer copies" are pure aliases
(`assign round_key_update_km = round_key_update;`). `opt_clean` merges
equivalent nets, so after synthesis the driver's total load is unchanged and
only the cone duplication survives. If that is what the measurement shows, the
project's claim sharpens from *"RTL cannot shorten a net's load delay"* to
**"RTL cannot express a fanout split that survives logic optimisation, because
net merging is exactly what the optimiser does"** — which is a mechanism rather
than an observation.

If instead `clk_b` improves materially, the claim in §1 is too strong and the
report changes.
