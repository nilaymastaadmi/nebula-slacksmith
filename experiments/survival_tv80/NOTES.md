# Survival on tv80: one proven transform beats `repair_design`, found by an agent

Registered in `PREREGISTRATION.md` (`657797d`) before the gate change and before any
run. The gate change (`2094112`) was checked before any run:
`results/gate_param_check.txt`. Six runs, sequential, 06:40 to 08:34 UTC.

## The six runs

No `--force-lever`, one online proposal each, two iterations, `--gate-param Mode=1`.
"Agent tool calls" is the count in that run's Claude Code session transcript (see
"The proposer was an agent" below).

| run | start UTC | transform | G1 to G3 | G4 | gate time | G5 | agent tool calls |
|---|---|---|---|---|---|---|---|
| 1 | 06:40 | none: **CLI timed out after 1,800 s** | | | | | 95 |
| 2 | 07:10 | `parallel_case_decode_hint` | PASS | **PROVEN** | 856 s | REVERT, −0.894 → −0.894 | 23 |
| 3 | 07:24 | none: **reply is not valid JSON** | | | | | 1 |
| 4 | 07:37 | `coalesce_split_bus_field_assigns` | PASS | **PROVEN** | 698 s | REVERT, −0.894 → −1.023 | 2 |
| 5 | 07:49 | `hoist_ld_hl_n_and_collapse_addr_to_double_write` | PASS | **PROVEN** | 1,448 s | REVERT, −0.894 → −1.581 | 48 |
| 6 | 08:13 | `isolate_incdec16_into_dedicated_process` | PASS | **PROVEN** | 1,233 s | **KEPT**, −0.894 → **−0.504** | 61 |

G7 reads `SKIPPED, module not in the file list` on all four gated runs, the lookup
limitation `experiments/depth_tv80/NOTES.md` already discloses; `tv80s` has one clock.

## Scorecard

**R109. CONFIRMED.** **6 of 6** routed to RTL unforced, fanout share **0.1602**.
`results/routing.txt` has 7 lines because run 6 reached its second iteration and
classified again (0.1608, RTL) before the one-proposal cap stopped it.

**R110. CONFIRMED.** **4 of 6** reached PROVEN. The other two never reached the gate.

**R111, the primary. CONFIRMED.** Run 6 lands at **−1.175 ns after `repair_design`
against gold's −2.021**, a gain of **+0.846 ns** against a bar of 0.750 (two floors).

**R112. CONFIRMED.** The same transform clears one floor, 0.375 ns.

**Four of four confirmed.** Read the next two sections before quoting any of them.

## The survival table

Every PROVEN transform, measured by `experiments/depth_tv80/measure.sh` after all six
runs had finished: `results/survival.tsv`, logs `results/or_surv_*.log`. Slack in ns;
area in u² before and after `repair_design`.

| variant | A unbuffered | B ABC lever | C before repair | **C after repair** | area before / after | cells |
|---|---|---|---|---|---|---|
| gold | −0.894 | −0.296 | −6.072 | **−2.021** | 29,173 / 35,159 | 3,447 |
| `ctrl_flip` (the floor) | −1.046 | −0.269 | −6.276 | **−1.646** | 29,100 / 35,259 | 3,429 |
| run 2 `parallel_case_decode_hint` | −0.894 | −0.296 | −6.072 | **−2.021** | 29,173 / 35,159 | 3,447 |
| run 4 `coalesce_split_bus_field_assigns` | −1.023 | −0.324 | −5.940 | **−1.723** | 29,007 / 34,861 | 3,421 |
| run 5 `hoist_ld_hl_n_...` | −1.581 | −0.588 | −7.309 | **−2.098** | 29,062 / 35,105 | 3,437 |
| **run 6 `isolate_incdec16_...`** | **−0.504** | **+0.190** | **−5.387** | **−1.175** | **28,904 / 34,842** | **3,406** |

Gold re-measured in the same pass reproduces **−6.072 / −2.021** exactly.

**Why run 6 is claimed and `depth_tv80` run 3's +0.382 was not.** That near-miss beat
one floor by 0.007 ns, was worse in three of four columns, and the loop reverted it.
Run 6 is **better in all four columns**: +0.390 unbuffered (**2.6 times** the 0.152 ns
unbuffered floor), +0.486 after the ABC lever, where it **meets the constraint
(+0.190) and gold does not**, +0.685 before repair and **+0.846 after (2.26 times
the 0.375 ns floor)**. It is also smaller: 269 u² less before repair, 317 u² less
after, 41 fewer cells. And the loop's own G5 kept it.

**What the number is not.** The floor comes from one control, so there is no spread
and 2.26 is a ratio, not an interval. It is one transform on one design. Run 4 has
the control's shape (worse unbuffered, better after repair) at +0.298, under one
floor, and is not claimed. Run 2 is byte-identical to gold in every column: the third
time a model's `parallel_case` hint turned out to be something Yosys already infers
(`depth_i2c` run 2, `depth_tv80` run 2).

## Run 6, checked again after the runs

Sanity checks, not registered predictions: `results/run6_recheck.txt` and
`results/agent_tool_use.txt`.

1. **The committed transform, gated again** with the committed gate and `--param
   Mode=1`: **PROVEN**.
2. **Confined to the proven module.** The proposal file carries all five `tv80`
   modules; four (`tv80s`, `tv80_core`, `tv80_alu`, `tv80_reg`) are identical to gold
   after whitespace normalisation. `tv80_mcode` goes from 2,626 to 2,694 lines, 51
   removed and 119 added. The model's own description: every `IncDec_16` assignment
   moved, same values and priority, into its own `always` block with flattened guards.
3. **The proof is not vacuous.** One `IncDec_16` constant changed still read PROVEN at
   `Mode = 1`, so it was investigated rather than explained away: that constant sits
   under `if (Mode == 3 && MCycle[1])`, unreachable at `Mode = 1`. The same mutation
   gated at `Mode = 3` reads **REFUTED** (1 of 56 partitions), and changing the default
   `IncDec_16` at `Mode = 1` reads **REFUTED** (1 of 56). The gate sees the edit, and
   it sees the parameter.

## The proposer was an agent

Found after the runs, by reading the Claude Code session transcripts
(`results/agent_tool_use.txt`, counts only). **`claude -p` is not a bare model call.**
It is the Claude Code agent, started in the repository with its built-in tools, and
in four of the six runs it used them heavily:

| run | tool calls | read results | read a registration | synthesis | timing | equivalence |
|---|---|---|---|---|---|---|
| 1 | 95 | 8 | 0 | 21 | 15 | 5 |
| 2 | 23 | 3 | **1** | 5 | 0 | 0 |
| 3 | 1 | 0 | 0 | 0 | 0 | 0 |
| 4 | 2 | 0 | 0 | 0 | 0 | 0 |
| 5 | 48 | 13 | **1** | 8 | 9 | 3 |
| 6 | **61** | **12** | 0 | **8** | **3** | **2** |

Categories are pattern matches on each call's input, so one call can count in several.
The two registration reads are of this experiment's `PREREGISTRATION.md`.

**What this changes.**

- **Run 6's transform is what a tool-using agent produced**, after reading earlier
  runs' results and running synthesis, timing and equivalence checks on its own
  candidates. It is not evidence about a model's single, unaided proposal.
- **The runs are not independent.** Later sessions read earlier runs' output, so
  **1 of 6 is not a success rate**. N = 1 surviving transform.
- **Runs 2 and 5 could see the bar.**
- **The same was true earlier.** Of the 12 sessions the CLI backend started in the
  repository on 11 and 12 September, 10 made tool calls (1 to 45), 7 ran synthesis,
  5 touched results, notes or the report, and 2 touched a registration:
  `results/agent_tool_use_earlier.txt`. The report described that tier as having "no
  context beyond the prompt"; that was wrong for every session on record, and the
  report is corrected.

**What it does not change.**

- **The agent could not touch the verdict or the measurement.** Every write in the six
  sessions went to `.trace_scratch/` or `/tmp` (the three exceptions the pattern flags
  are an awk filter and a code comment, printed and checked). No session ran a git
  command that changes state. The tracked tree was clean afterwards, and `tools/` was
  last changed at `2094112`, before run 1.
- **The PROVEN verdict was reproduced after the runs** with the committed gate (check 1),
  and `measure.sh` ran after all six sessions had ended, outside any agent session.

## Decision, as declared

The registration declared that if R111 holds, deliverables 2 and 4 are stated as met
with this result as the evidence. They are, **with the proposer's access stated in
the same sentence**: an unattended tool-using agent found the transform; this
project's gate proved it; this project's flow measured it.

The question the agent finding opens is registered separately, before any run:
**does the same model, given only the prompt, do it?** `experiments/survival_tv80_blind/`
repeats this protocol with every tool removed and an empty working directory.

## Disclosures

1. **One launch was stopped before run 1.** The first launch used a 600 s tool timeout
   that would have killed run 1 mid-flight. It was stopped at 06:39:49 UTC, before any
   reply: only `REQUEST_O1.md` existed and its session made **0 tool calls**. Relaunched
   at 06:40:13 UTC. Nothing from the stopped launch was measured or counted.
2. **Runs 1 and 3 produced no transform**, for the reasons in the table; they count
   in the N of 6.
3. `experiments/survival_tv80_blind/PREREGISTRATION.md` first said runs **3** and 5
   read this registration. It was runs **2** and 5; the correction is dated in that file.
4. `.trace_scratch/`, the agents' scratch directory, is not committed.
