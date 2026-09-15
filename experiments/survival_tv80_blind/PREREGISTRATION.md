# Pre-registration: the survival experiment again, with a blind proposer

Registered 2026-09-15, after `experiments/survival_tv80/` was scored and before any
run here. Scored in `NOTES.md` here. Predictions **R113 to R116**.

## Why

In `experiments/survival_tv80/`, run 6's transform is PROVEN by the gate and beats gold
after `repair_design` by **+0.846 ns** (R111 confirmed). The session transcripts then
showed what the unattended backend actually is: `claude -p` is the Claude Code agent,
started in the repository with its built-in tools, and **it used them**. Run 6's
session made 61 tool calls: it read earlier runs' results (12), ran synthesis (8),
timing (3) and equivalence checks (2) on its own candidates before replying. The run 3
and run 5 sessions read that experiment's registration. The earlier unattended
sessions of 11 and 12 September did the same. So those runs were neither blind nor
independent, and this project's description of the tier as "no context beyond the
prompt" was wrong.

That does not change what the gate proved or what `repair_design` measured, which the
agent could not reach. It changes what the result is evidence of: **a tool-using agent
with this project's toolchain**, not a model's single proposal. This experiment asks
the separate question: **does the same model, given only the prompt, do it?**

## The one change

The proposer is `experiments/survival_tv80_blind/claude_blind.sh`, passed as
`--claude-bin`: the same CLI, started in an **empty temporary directory** with every
built-in tool disallowed. **Checked before registering:** asked to run `ls` and print
the first line of `REPORT.md`, it replied `NO_TOOLS`, and its session transcript holds
**0 tool calls**. Everything else is `experiments/survival_tv80/run.sh` unchanged:
`tv80s`, no `--force-lever`, `--gate-param Mode=1`, `--max-online 1`, `--max-iters 2`,
`--g5 total`, the loop's 1,800 s CLI timeout, and `experiments/depth_tv80/measure.sh`
for every PROVEN transform.

## Protocol

- **N = 6** runs, sequential, every one reported, none added or dropped.
- **Bars, unchanged from `survival_tv80`:** gold after repair **−2.021 ns**; floor
  **0.375 ns**; primary bar **−1.271** (two floors), secondary **−1.646** (one floor).
- **Stop rule:** no run starts after **19:30 IST**; results freeze at **21:00 IST**.
- **What this cannot change:** run 6's measured result. The report states it with the
  agent's access in the same sentence, whatever these runs show.

## Predictions

**R113.** At least **4 of 6** runs route to RTL with no `--force-lever`. *Prior: strong.
The router does not depend on the proposer.*

**R114.** At least **1 of 6** runs returns a reply the gate reads **PROVEN**. *Prior:
weak. A blind reply must carry the whole rewritten `tv80_mcode`, about 100 KB, as JSON,
with no way to check it; the tool-using sessions wrote files and checked them first.*

**R115, the primary.** At least one PROVEN transform beats gold after `repair_design`
by more than **0.750 ns**. *Prior: weak.*

**R116.** At least one PROVEN transform beats gold after repair by more than **0.375 ns**.
*Prior: weak.*
