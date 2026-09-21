# Prior art: agentic RTL timing closure with reliability reporting

Phase 1 kill test. Run 2026-09-21. Searched via `agent-reach` (Exa with a
personal key, arXiv direct fetch, GitHub search API).

**Verdict: PARTIALLY COVERED, close to the covered boundary.**

The build prompt's "Open" verdict required that *no existing benchmark treats
timing closure as an agent task with reliability reporting*. That statement is
false as of September 2026. Three benchmarks and one agent paper occupy this
space, two of them published within the last three months.

---

## Zeroth finding: the name is already taken, by us

`SlackBench` already exists, publicly, under this author's own account:
`experiments/slackbench/` in `github.com/nilaymastaadmi/nebula-slacksmith`.
It is a **different benchmark** - it grades verification *checkers* (8 Tier B
cases across LATENCY/STIMULUS/CDC/CONTROL, confusion-matrix scoring, a
committed pre-registration, a Tier A archival column). It is not a variant of
the proposed timing-closure benchmark; the two grade different objects.

Shipping a second public SlackBench with an incompatible definition would mean
one author holding two public meanings for one benchmark name. The name must
change, or the new work must be positioned as a component of the existing one.

This was not found by any literature search. It was found by listing a
directory before writing code.

---

## The table

| Work | Date | What it measures | Task | What it does NOT cover | Subsumes this? |
|---|---|---|---|---|---|
| **CLOSER-Bench** (arXiv:2607.16632) | Jul 2026 | Budgeted cross-stage design closure for hardware agents. Final quality, anytime progress (AUC over budget), tool cost, cross-stage recovery. Counts every simulator/synthesis/STA/PnR call, wall-clock, tokens, edit layer. | Stage-paired: spec→RTL, RTL→GDS, spec→GDS. Task B starts from a functionally correct but physically weak implementation that intentionally misses physical targets. | Still a **pilot report**. "Unequal trial counts and is therefore diagnostic rather than a model ranking." Central experiment is 3 trials per cell and is **unrun**. Bootstrap CIs explicitly deferred "until the final signoff oracle and repeated-trial matrix are frozen". No non-LLM classical baseline arm. | **Nearly.** Same open stack (Yosys, OpenROAD, Sky130, Verilator, KLayout). Already lists *run-to-run variance* in its metric set. Already has a run-status taxonomy (agent failure / timeout-with-patch / verifier failure / infrastructure failure), LEC against logic-changing edits, and an **unconstrained-path audit to prevent timing evasion** - which is the same idea as our G0 SDC-integrity gate. This is the landmine. |
| **PostEDA-Bench** (arXiv:2605.06936, `pengjas/posteda-bench`) | May→Jul 2026 | Success rate on PPA convergence and DRC fixing. Machine-checkable evaluation. | 145 tasks across DRC-Essential, DRC-Reasoning, PPA-Mono, PPA-Multi. 8 commercial and open LLMs under multiple agent scaffolds. | Success rate only; no variance reporting found. PPA-Multi is a trade-off task, not specifically WNS closure. No classical-optimizer baseline. | No, but it owns "LLM agents on post-synthesis PPA convergence, benchmarked, with public code". |
| **PDAgent-Bench** (arXiv:2606.17253) | Jun→Aug 2026 | Task-level and workflow-level agent performance across the physical-design stack. | 353 curated problems, conceptual questions plus real workflow execution. LLM **and** VLM agents. | Physical design, so mostly past synthesis. | No, but it occupies "standardized benchmark for agentic EDA workflows". |
| **SynAct** (arXiv:2608.12751) | Aug 2026 | **WNS as the primary objective**, TNS/area/power secondary. Reduces average WNS to 27.03% of bootstrap synthesis. | Closed-loop LLM reasoning-acting agent issuing synthesis commands, reading live reports. 14 OpenCores designs. | Uses a **commercial** synthesis tool (AltiSyn), so not reproducible on an open stack. **Reports 5-run averages, not spread** - variance is absorbed, not published. Not a benchmark; an agent. | No, but it is the strongest evidence that the headline question is already being answered. Baselines are ChatLS (LLM) and **CBTune (classical BO tuner)**: SynAct beats the classical baseline 27.03% vs 66.67%. |
| **Dr. RTL** (arXiv:2604.14989) | 2026 | RTL PPA optimization via closed-loop EDA interaction, distilling trajectories into a reusable skill library. 86% mean SEC pass. | Agentic RTL optimization on 20 human-written designs. | Publishes no failure-mode case studies. No reliability/variance reporting. Uses DC (commercial) + SEC. | No. It is the **design source** for this proposal, not a competitor benchmark. |
| RTLRewriter, SymRTLo, RTL-OPT, POET, CODMAS | 2024-2026 | LLM-based RTL optimization for PPA. Mapped in Dr. RTL's Table 1. | Module-level rewriting, mostly manually-degraded RTL. | Small designs (8-1275 LoC). Most rely on CEC, which cannot verify sequential change. | No. |
| VerilogEval, RTLLM, VeriGen, MetRex, ChipNeMo | 2023-2025 | Functional correctness of **generated** RTL; PPA only weakly considered. | RTL generation from natural language. | Not optimization, not closure, not agentic. | No. Out of scope by construction. |
| **Noise Floor Audit for Agent Benchmarks** (arXiv:2608.22331) | Aug 2026 | Measurement variability of agent benchmarks. At temp 0, rerun ever-flip fractions 0.7%/2.0%/2.7%; **prompt-perturbation SDs 11x to 58x larger than rerun SDs**. | Tool-calling (BFCL), not EDA. | Not hardware. | No - but it **pre-empts the methodological novelty claim**. "Nobody reports run-to-run variance" is not true of the agent-benchmark literature generally. |
| Stochasticity in Agentic Evaluations (arXiv:2512.06710); Repeated-Run Reliability (arXiv:2606.00920); How Consistent Are LLM Agents (arXiv:2605.28840) | 2025-2026 | ICC-based inconsistency quantification; repeated-run reliability on deterministic programming tasks; behavioural reproducibility in multi-step tool-calling. | General agents. | Not EDA. | No, same caveat as above. |

GitHub search API (`gh search repos`, control query verified returning rows)
found **no** dedicated open harness under "LLM agent EDA benchmark" or
"timing closure benchmark agent". `pengjas/posteda-bench` is the only public
repo in the adjacent space.

---

## What survives as genuinely uncovered

Three things, and they are narrow:

1. **Variance published as a headline, not averaged away.** SynAct runs each
   experiment 5 times and reports the mean. CLOSER-Bench names run-to-run
   variance as a metric and defers it. Nobody in EDA has published a
   closure-rate table with error bars next to the claimed gap and asked
   whether the gap survives the spread. The Noise Floor Audit does exactly
   this, for tool-calling, not hardware.

2. **A null baseline and a random-transform baseline at matched budget.**
   Neither CLOSER-Bench, PostEDA-Bench, PDAgent-Bench nor SynAct includes a
   random-selection arm. SynAct's two baselines (ChatLS, CBTune) are both
   "smart". A random arm at matched budget is the single cheapest way an LLM
   advantage evaporates, and its absence across the whole field is real.

3. **Synthesis + STA only, fully open stack.** SynAct is commercial-tool-bound.
   CLOSER-Bench and PDAgent-Bench both reach into place-and-route, which this
   project's own anti-scope list excludes. The cheap, fully-reproducible
   synthesis-and-STA slice is unoccupied - partly because it is the least
   impressive slice.

## What does not survive

- "Timing closure as an agent task" - covered by SynAct, CLOSER-Bench, Dr. RTL.
- "With reliability reporting" - claimed by CLOSER-Bench, delivered generally
  by the Noise Floor Audit line of work.
- "Failure taxonomy, previously unreported in RTL agent work" - CLOSER-Bench
  already defines run-status provenance across four states plus an explicit
  invalid-run manifest.
- "Sealed holdout" - CLOSER-Bench's public/private conditions are disjoint by
  construction.
- "CEC gate on submissions" - CLOSER-Bench runs LEC for the same purpose;
  Dr. RTL runs the stronger SEC.
- "Constraint-tampering defence" - CLOSER-Bench's unconstrained-path audit.

Every individual component of the proposed harness exists in at least one
published system. The combination does not exist as one artifact, but a
combination is a weaker claim than the build prompt assumed.

---

## Rewritten Phase 0 question 3, per the "partially covered" rule

The original candidate claim was:

> LLM agents do not beat a classical `repair_design` baseline on timing
> closure for designs above N gates, and their run-to-run variance exceeds
> the gap they claim.

The first clause is contested and currently points the other way: SynAct beats
CBTune, a classical tuner, on 14 designs. The claim has to narrow to the
surviving slice:

> On open-source synthesis and STA, at matched budget, the run-to-run standard
> deviation of an LLM agent's WNS improvement exceeds its median advantage
> over a random-transform baseline on a majority of designs - so the published
> single-run and mean-of-5 rankings in this literature are not reproducible
> orderings.

That is falsifiable, it is not answered by anything above, and it is the one
sentence this project could own. It is also a **critique paper with a harness
attached**, not a platform benchmark - which is a smaller, more defensible
thing than what the build prompt set out to build.

---

## Honest assessment of the remaining opportunity

The three uncovered items are real but thin, and two well-resourced groups
(CLOSER-Bench, PostEDA-Bench) are already moving through this territory with
more compute and more authors. CLOSER-Bench in particular has publicly
committed to running the exact repeated-trial matrix that item 1 depends on;
when they do, item 1 closes.

The asset that is not replicable by them is the measured classical-baseline
work already on disk in `slacksmith-final`: the FANOUT/DEPTH stratification
(median gain 3.623 ns vs 0.481 ns, 7.5x), the buffer-vs-sizing split
(buffer-only FANOUT +3.282, DEPTH -0.019, net harmful on 5 of 8 depth designs;
sizing helps 7 of 8), and repair_design equivalence proven at 5,832 compare
points in 38.10 s. That is a classical baseline characterised more finely than
any of the works above characterise theirs.
