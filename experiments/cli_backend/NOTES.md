# The unattended run

Registered in `PREREGISTRATION.md` (`886f80b`) **before `propose_cli` had ever
been executed**, with two amendments recording an environmental failure and the
prediction that missed.

## Why it had never run

`propose_cli()` shipped with this docstring:

> **UNTESTED**: it is committed so the automation path is reviewable, not so it
> can be claimed as exercised.

The blocker was authentication, not code. `~/.claude/.credentials.json` carried
`expiresAt: 0`. That left deliverable D2 **PARTIAL**: what existed was a gated
proposal checker with a human in the loop, not an engine that ran unattended.

## Attempt 1: died before the model

    PermissionError: [Errno 13] Permission denied: ''

`run.sh` resolved the binary with `command -v claude`. The script runs
non-interactively, which is not a login shell, so `~/.profile` never runs and
`~/.local/bin` is absent from `PATH`. The empty string went into
`subprocess.run`.

`propose_cli` handled `FileNotFoundError`, which is the **wrong exception**: an
empty program name raises `PermissionError`, so the clean error path was never
taken. Both the script and the library now fail loudly instead. Log kept at
`results/attempt1_environmental_failure.log`.

## Attempt 2: the whole loop, no human

    === iteration 1 ===
    measure: clk_b=-18.957
    classify clk_b: FANOUT_DOMINATED (fanout share 0.9139) -> physical
      LEVER FORCED to rtl
      online proposal O1: fanout_replication_round_key_update (declared k=0)
      gate O1: G3=PASS G4=PROVEN
      G7 O1: SKIPPED (aes_key_mem has no clock crossings)
      APPLY O1 provisionally
    1 iterations, 456.1s

## Scorecard

| # | registered | outcome |
|---|---|---|
| C1 | valid JSON first attempt | **CONFIRMED**, despite two warnings and a failing hook message in the captured text |
| C2 | reaches a G4 verdict with no human in it | **CONFIRMED. PROVEN.** |
| C4 | logic restructuring, not retiming or FSM | **CONFIRMED** |
| **C3** | no material `clk_b` improvement | **WRONG. +1.414 ns**, and the registered *mechanism* was wrong too |

## C3, the one that mattered

I predicted no improvement and gave the reason in advance: the duplicated
control nets are pure aliases (`assign round_key_update_km = round_key_update;`)
and `opt_clean` merges equivalent nets, so nothing would survive synthesis.

**It survived.** The cone duplication is not an alias; the two gated `if` blocks
are genuinely separate logic and the mapper keeps them.

| clock | baseline | variant | delta |
|---|---|---|---|
| clk_a | −13.167 | −11.200 | **+1.967** |
| clk_b | −18.957 | −17.543 | **+1.414** |
| clk_e | −25.957 | −24.543 | **+1.414** |

**No group paid.** It is the only batch-3 transform that improved every group,
and it carries the strongest proof of the three (EQY over all outputs, against
two partial proofs).

### What it did to REPORT section 1

The claim *"no RTL rewrite shortens a net's load delay"* was **falsified**, and
by more than this transform: `fsm_output_coded_state_assignment` bought
**+3.185 ns** on the same path. Two of three RTL transforms improved a group the
classifier scored **91.4% fanout-attributable**.

What survives is a ratio rather than an impossibility: best RTL gain **+3.185**
on a **−18.957** violation is **16.8%**, against `repair_design`'s **+55.805**.
About one sixth. The two-lever design is better supported by a ratio than by an
absolute one counterexample breaks.

### The model out-reasoned this session on the same input

Given the same timing report and the same module, this session hand-wrote a
retiming of the write decoder, which **cost 4.616 ns**. The model went at the
300-load net the classifier had just flagged, and gained. Its own rationale
named the mechanism:

> The single-bit reg `round_key_update` gates one combined if-block that drives
> ~384 bit-positions [...] matching the reported 300-fanout nor4 on the critical
> path.

That is the clearest evidence in this project that the generative half
contributes something a competent engineer with the same report did not. It is
also **N = 1**: one design, one sample of a nondeterministic generator, one run.

## Limits

- **N = 1.** The claim is that the automation path works, not that it works
  reliably.
- `--force-lever rtl` was required, as in every RTL run on this benchmark, and
  is logged as `lever_forced`.
- `--max-iters 1` stopped the run after the provisional apply, so the loop's own
  confirm-or-revert never ran; the timing above was measured separately with
  `tools/remeasure.py` across all three groups.
- The prompt is `tools/proposer_prompt_v2.md`. v1 is untouched and stays
  attached to `experiments/online_proposer/`.
