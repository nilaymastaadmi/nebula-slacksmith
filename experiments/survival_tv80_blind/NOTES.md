# Survival on tv80, blind: the same model with every tool removed

Registered in `PREREGISTRATION.md` (`446bd57`) after `experiments/survival_tv80/` was
scored and before any run here, with one amendment (`2073382`) committed after runs 1
to 6 and before any rerun. The proposer is `claude_blind.sh`: the same CLI, in an empty
temporary directory, every built-in tool disallowed.

## The runs

Same flags as `experiments/survival_tv80/run.sh`. "Output tokens" and "tool calls" come
from each session's transcript (`results/blind_sessions.txt`).

| run | start UTC | reached the model | transform | G4 | G5 | output tokens | tool calls |
|---|---|---|---|---|---|---|---|
| 1 | 08:52 | yes | none: **reply over the output cap**, no JSON the loop could read | | | 64,000, stop `max_tokens` | 0 |
| 2 | 09:03 | yes | `flatten_layered_mcycle_epilogue_override` | **PROVEN** | REVERT, −0.894 → −1.649 | 60,777 | 0 |
| 3 | 09:11 | **no**: account session limit | | | | 0 | 0 |
| 4 | 09:11 | **no**: account session limit | | | | 0 | 0 |
| 5 | 09:11 | **no**: account session limit | | | | 0 | 0 |
| 6 | 09:12 | **no**: account session limit | | | | 0 | 0 |
| rerun 3 | 10:37 | yes | none: **reply over the output cap** again | | | 64,000, stop `max_tokens` | 0 |
| rerun 4 | 10:50 | yes | `parallel_case_opcode_decoder` | **PROVEN** | REVERT, −0.894 → −0.894 | 59,041 | 0 |
| rerun 5 | 10:58 | yes | `parallel_case_hint_mcode_decoder` | **REFUTED**, 31 of 56 partitions | | 37,115 | 2, see disclosure 5 |
| rerun 6 | 11:05 | yes | `parallel_case_opcode_decode` | **PROVEN** | REVERT, −0.894 → −0.894 | 44,535 | 0 |

Runs 3 to 6 each ended within 10 s with the 54-byte reply "You've hit your session
limit · resets 10:30am (UTC)"; they are kept unchanged in `results/session_limit/`.
Amendment 1 reran each once. None hit the limit again, so **six runs reached the model**: 1, 2 and reruns 3 to 6.
Gate times 513, 496, 370 and 333 s.

## Scorecard

**R113. CONFIRMED.** Every run routed to RTL unforced at fanout share **0.1602**: the six
that reached the model, and the four stopped by the limit, which route before proposing.

**R114. CONFIRMED.** **3 of the 6** runs that reached the model returned a transform the
gate reads PROVEN (runs 2, rerun 4, rerun 6). One more was REFUTED and two returned
nothing the loop could read.

**R115, the primary. WRONG.** No PROVEN transform beats gold after `repair_design` by
more than 0.750 ns. The best is run 2 at **+0.444**.

**R116. CONFIRMED as written, and not claimed.** Run 2's +0.444 clears one floor (0.375).
It is the null control's shape, below.

**Three confirmed, one wrong**, and the one that was wrong is the one that mattered.

## The survival table

`experiments/depth_tv80/measure.sh`, unchanged, on every PROVEN transform after its run:
`results/survival.tsv` and `results/survival_reruns.tsv`. Slack in ns.

| variant | A unbuffered | B ABC lever | C before repair | **C after repair** | area before / after | cells |
|---|---|---|---|---|---|---|
| gold | −0.894 | −0.296 | −6.072 | **−2.021** | 29,173 / 35,159 | 3,447 |
| `ctrl_flip` (the floor) | −1.046 | −0.269 | −6.276 | **−1.646** | 29,100 / 35,259 | 3,429 |
| run 2 `flatten_layered_mcycle_epilogue_override` | **−1.649** | **−0.720** | **−6.501** | **−1.577** | 29,078 / 35,290 | 3,435 |
| rerun 4 `parallel_case_opcode_decoder` | −0.894 | −0.296 | −6.072 | **−2.021** | 29,173 / 35,159 | 3,447 |
| rerun 6 `parallel_case_opcode_decode` | −0.894 | −0.296 | −6.072 | **−2.021** | 29,173 / 35,159 | 3,447 |

**Reruns 4 and 6 are identical to gold in every column**: a `parallel_case` hint that
Yosys already infers, the same no-op `depth_i2c`, `depth_tv80` and `survival_tv80` each
measured in their run 2. With rerun 5, three of the blind arm's four gated proposals
reached for that hint.

**Run 2 is the null control's shape, and it is not claimed.** It beats gold after repair
by **+0.444 ns**, over one floor (0.375) and under two (0.750), and it is **worse in the
other three columns**: −0.755 unbuffered, −0.424 after the ABC lever, −0.429 before
repair. `ctrl_flip`, a provably null edit, does the same (worse unbuffered, better after
repair), and so did `depth_tv80` run 3 (+0.382). `survival_tv80`'s registration set the
rule this experiment inherited: a result between one and two floors is reported and not
claimed. The loop's own G5 reverted it.

## What the blind arm could not do, measured

**The reply has to fit in one message.** The loop needs the whole rewritten `tv80_mcode`,
about 100 KB, as JSON in the CLI's printed output. Without tools the model reasons and
writes in a single assistant turn, and that turn has a **64,000-token output cap**.
Run 1 hit it (stop reason `max_tokens`, 105,810 characters of text across the capped turn
and its continuation), and `claude -p` printed only the last continuation, so the loop
found no JSON. Run 2 fit with 3,223 tokens to spare. The tool-using sessions of
`survival_tv80` never met the cap: their reasoning was spread over many turns, and the
final message carried only the JSON.

So the two arms differ in more than tools. **This experiment does not isolate what the
tools bought**; it measures what the same CLI produces with them removed, under the
same loop.

## What this says about `survival_tv80` run 6

**Given only the prompt, the same model did not repeat it.** Six blind runs that reached
the model produced no transform past two floors: one of the control's shape (+0.444),
two no-ops (0.000), one REFUTED and two unreadable. The tool-using arm produced one
(+0.846) in six.

That is **N = 1 against N = 0**, and the arms differ in two ways at once: tools, and the
single-message output cap that stopped two blind replies. So this does not show that
tool use found run 6's transform. It does show what the report must not say: that the
model alone, from the prompt, delivers a surviving gain. **D2 and D4 rest on
`survival_tv80` run 6, stated with its proposer's access**, as that experiment declared
before its runs.

One difference is visible without a claim about cause: the blind arm's four gated
proposals include **one REFUTED**, and the tool-using arm's four, whose sessions ran
equivalence checks before replying, include **none**.

## Disclosures

1. **Amendment 1 was written after runs 1 and 2 were seen** (run 1 unreadable, run 2
   PROVEN and reverted, not yet measured). It changes nothing about them; it reruns only
   runs that never reached the model, once each, with a stop on a repeat limit hit.
2. The limit that stopped runs 3 to 6 is the author's account limit, shared with the
   session that drove this project; it was hit after `survival_tv80`'s six runs and blind
   runs 1 and 2 on the same day.
3. The registration's "why" section first named the wrong earlier runs as having read a
   registration; corrected in place, dated, predictions untouched.
4. G7 reads `SKIPPED, module not in the file list` on every gated run, as disclosed in
   `experiments/depth_tv80/NOTES.md`.
5. **The deny list missed one tool.** Rerun 5's session called `ReportFindings`, a
   findings-reporting tool `claude_blind.sh` does not name, twice, each time with an empty
   list; each call returned "No findings reported". It reads no file and runs nothing, so
   the session still saw only the prompt, but the wrapper's "every built-in tool
   disallowed" is not exact. `results/blind_sessions.txt` has every session's counts.
6. Rerun 5's REFUTED verdict was not examined further; its gate record carries no
   control result.
