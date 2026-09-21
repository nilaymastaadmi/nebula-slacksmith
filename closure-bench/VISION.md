# Vision: ClosureDuel, LLM agents against a classical optimizer on RTL timing closure

Phase 0. Written 2026-09-21.

**Disclosure on ordering.** The build prompt ordered Phase 0 before Phase 1 so
that the vision could not be retro-fitted to whatever the prior-art search
returned. That ordering was inverted: Phase 1 ran first, because it is the
gate that can end the project and the prompt also says a project killed at
four hours is a win. So this document was written with `PRIOR_ART.md` already
visible, and question 3 below is the *narrowed* claim the partially-covered
verdict required, not a blind one. Anyone reading this should treat question 3
as shaped by the survey rather than independent of it. No prediction is
registered here; predictions belong to Phase 5 and are still sealed.

---

## Decision, 2026-09-21: from a benchmark to a head-to-head

**This project stops being a benchmark and becomes the missing arm.** It is an
open-stack, reproducible, properly powered head-to-head of LLM agents against a
design-class-aware classical optimizer on RTL timing closure, run at the trial
count CLOSER-Bench deferred.

**Why.** `PRIOR_ART.md` returned "partially covered", and read honestly its own
table makes "a new benchmark" indefensible. CLOSER-Bench (arXiv:2607.16632)
runs on the same open stack, already lists run-to-run variance in its metric
set, already has a run-status taxonomy, and already has an unconstrained-path
audit equivalent to our G0 gate. The Noise Floor Audit (arXiv:2608.22331)
pre-empts the methodological novelty claim. What the same table shows nobody
has done:

1. **CLOSER-Bench's central experiment is unrun.** Its text: unequal trial
   counts, "diagnostic rather than a model ranking", 3 trials per cell planned,
   bootstrap intervals deferred until the oracle and the repeated-trial matrix
   are frozen.
2. **None of the three open-stack works has an LLM-free classical arm.**
   Checked against full texts on 2026-09-21, not abstracts: CLOSER-Bench has
   zero hits for any classical, heuristic, Bayesian or `repair_design`
   baseline; PostEDA-Bench's only optimizer arm is ORFS-Agent, Bayesian
   optimization whose search space an LLM chooses; PDAgent-Bench benchmarks
   agents only. SynAct does compare against a classical tuner (CBTune) and wins,
   27.03% against 66.67% of bootstrap WNS violation, but on the commercial
   AltiSyn, so nobody can reproduce or contest it.
3. **We hold a classical optimizer nobody else has characterised.** From the
   Dr. RTL transfer study, corrected grouping: the combined lever's median gain
   is 3.623 ns on FANOUT against 0.581 ns on DEPTH (6.2x); buffer-only gains
   +3.282 on FANOUT and closes 4 of 5, and does nothing for DEPTH (median
   0.000, 3 of 7 worse); sizing-only helps both, FANOUT 4x more (+2.495 against
   +0.621).

It is also about a third of the work of a platform, it uses CLOSER-Bench and
PostEDA-Bench as infrastructure rather than competing with them, and either
outcome is a result: if the classical arm beats every agent at matched budget
on an open stack, that contradicts SynAct's commercial-tool result, and if it
does not, SynAct's result gains its first open reproduction.

**This reverses an earlier call, and is recorded as such.** Earlier on
2026-09-21 the owner chose "full v1.0 platform as written" over a narrower
scope. The continuation brief the owner supplied the same day recommended this
narrowing, and it is adopted here as the owner's decision.

**Two corrections to that brief, made rather than absorbed:**

- **Its lever numbers were pre-correction.** "DEPTH -0.019, net harmful on 5
  of 8" and "sizing 5x" are superseded by the re-scored table in
  `experiments/drrtl_transfer/NOTES.md` (quoted above). "Net harmful on depth
  paths" does not survive and is withdrawn everywhere in this directory.
- **Its power analysis rested on a false premise.** It asked for the trial
  count to be computed from the classical arms' run-to-run spread. The
  classical arms are deterministic: two container runs of the null flow were
  byte-identical (`docker/VERIFIED.md`), and the transfer study's scored run 4
  reproduced run 1 byte for byte. Their within-cell spread is zero, so it
  cannot size anything. What it establishes instead is that each classical
  cell needs exactly one trial and the whole repetition budget belongs to the
  stochastic arms. The trial count is a function of the agents' spread, which
  no one has measured; it is computed as a table over that spread, anchored by
  the random arm's measured across-seed spread. Determinism is asserted per
  arm by running it twice, not assumed from the null flow.

**The holdout stays sealed.** The brief's Phase 4 said "each of the 15
in-scope designs"; five of those are the sealed holdout, and the harness
refuses them by design. Every run before the final one uses the 10
development designs.

**What this supersedes below.** Question 3 and question 4 are rewritten for
the head-to-head. Question 1's first user (a researcher plugging an agent into
a leaderboard) and question 6's leaderboard and "how to add an agent" guide are
dropped; question 6's date stands, because the calendar and not the work sets
it. A general-purpose benchmark platform and a public leaderboard are added to
the out-of-scope list.

### The name, and why it changed three times

| Name | When | Why not |
|---|---|---|
| SlackBench | the original build prompt | already public in this repository for a different, pre-registered benchmark (the verification-checker exam) |
| closure-bench | working name, 2026-09-21 | one character from CLOSER-Bench, the nearest competitor |
| RepairFirst | proposed by the continuation brief | names the expected outcome, when either outcome is to be reported; and "repair" means bug repair in this literature (CLOSER-Bench's "RTL repair", FormalRTL, AutoVeriFix+, Veri-Sure) |
| **ClosureDuel** | **chosen by the owner, 2026-09-21** | names the design, a head-to-head, not a result; 0 GitHub repos, 0 arXiv hits (probe verified against a control), 0 hits on the owner's disk |

---

## 1. Who uses this, and what do they do in their first 10 minutes?

**A researcher benchmarking a new RTL agent.** They arrive from a paper's
related-work section. Minute 0-2: `docker pull`, one command. Minute 2-6: the
container runs two small designs against the null and classical baselines and
prints a table that matches the one in the README, so they know their machine
agrees with ours. Minute 6-10: they open `agents/` and read the 30-line
adapter for the classical baseline, because what they actually need to know is
how much work it is to plug in their own agent. They leave knowing the answer
is "one function and one registry line".

**An EDA engineer deciding whether an LLM in the loop beats `repair_design`.**
They do not care about the leaderboard. Minute 0-3: they go straight to
`RESULTS.md` and look for the classical baseline column. Minute 3-10: they
look for whether the error bars overlap. If our table shows a 0.4 ns median
advantage with a 1.2 ns run-to-run spread, they have their answer and they
close the tab, and that is a successful visit. This is the user the project
exists for.

**A hiring manager reading the repo.** Minute 0-1: README first screenful,
which must carry a number. Minute 1-4: they check whether the numbers are
reproducible or asserted, which means they look for a command. Minute 4-10:
they skim `RESULTS.md` for the wrong-predictions section, because a benchmark
that lists what its author got wrong reads differently from one that does not.

## 2. What is the single number?

**Closure rate at fixed budget**: the fraction of designs whose worst negative
slack reaches >= 0 within the budget, subject to passing combinational
equivalence checking against the original and not increasing cell area by more
than 20%.

It is the right primary because it is the only metric that is *not* gameable
by partial progress: WNS improvement rewards moving a path from -9 ns to -6 ns,
which is worth nothing to anyone shipping a chip, whereas closure is the actual
engineering event. It is also binary per design, which makes the reliability
half expressible - a closure rate has a well-defined variance across seeds,
where a median-of-medians does not.

Every other metric is secondary and reported alongside, never as a headline:
median and IQR of WNS improvement, total negative slack improvement (reported
alongside per-group, because these two disagreed in our own prior runs), area
and flop-count delta, USD and tokens per design, wall-clock per design, and
run-to-run standard deviation across seeds.

## 3. What claim becomes checkable that was not checkable before?

> On an open stack (Yosys, OpenSTA, OpenROAD, sky130hd) at matched budget, no
> LLM agent configuration beats the classifier-routed classical lever on
> closure rate by more than the agent's own run-to-run spread, measured at the
> trial count a power analysis says is needed to see an effect of the size
> SynAct reports.

This is the claim under test, not the expected answer. Either outcome is
reported under the same name, which is why the name does not encode one.

Someone can disagree with it, and SynAct's authors would: they report a 5-run
mean with their agent at 27.03% of bootstrap WNS violation against 66.67% for
a classical tuner, a gap wide enough that it plausibly survives its spread.
They do not publish the spread, and their tool is commercial, so neither they
nor anyone else can currently check.

*Superseded versions, kept so the history reads straight.* The build prompt's
candidate ("agents do not beat `repair_design`") was dropped in Phase 1
because it was already contested. The first narrowed version ("run-to-run SD
exceeds the median advantage over a random baseline") survives as a secondary
comparison: the random arm is one of the six classical arms.

## 4. The README's first screenful

> **ClosureDuel** - LLM agents against a classical optimizer on RTL timing
> closure, on an open stack, at a trial count that can actually tell them apart.
>
> Six classical arms (including one that picks buffering or sizing per design
> from the critical path's shape, and one that picks transforms at random) and
> K LLM agent configurations, on N designs, same budget, Yosys + OpenSTA +
> OpenROAD + sky130hd, one command.
>
> ```
> docker run --rm ghcr.io/<owner>/closureduel:v1 reproduce
> ```
>
> Result: [classical arm] closed X of N; the best agent closed Y of N at
> matched budget, with a run-to-run spread of Z across K trials. The trial
> count came from a power analysis published before any agent ran.
>
> Every submission must synthesise, pass combinational equivalence checking
> against the original, keep the module interface, and stay within 20% area.
> Every result row carries the harness commit that produced it. Five of the
> designs are a sealed holdout whose SHA256 hashes were published before any
> arm ran.

## 5. Explicitly out of scope for v1.0

1. **RTL generation from a natural-language specification.** VerilogEval and
   RTLLM own this and it is a different task.
2. **Place and route, and everything past synthesis plus STA.** CLOSER-Bench
   and PDAgent-Bench both reach into PnR; competing there means competing on
   compute we do not have.
3. **A web UI or a hosted leaderboard service.** The leaderboard is a Markdown
   table with a stated submission process.
4. **Fine-tuning any model.**
5. **A VS Code extension, or any editor integration.**
6. **Commercial EDA tool support.** The whole reproducibility argument dies the
   moment a result needs a licence to re-derive.
7. **Sequential equivalence checking as a gate.** CEC plus an unchanged
   interface is the legal-submission bar for v1.0. SEC is strictly better and
   is what Dr. RTL uses, but it would gate the harness on prover time we cannot
   bound. Stated as a known limit, not hidden.
8. **A general-purpose benchmark platform or a public leaderboard.** Added by
   the 2026-09-21 decision. CLOSER-Bench and PostEDA-Bench are the platforms;
   this is one properly powered comparison that runs on the same stack.

## 6. What does v1.0 release day look like?

**Target: 2026-11-22.**

That date is set against a calendar, not against the work. The 60-hour build
estimate is not the binding constraint; the binding constraint is that between
today and 23 October there is Yuva Yodha to its 4 Oct cutoff, the Nebula
presentation on the 25th, Paytm R1 and Ken R2 the same day, the Amazon ML
72-hour window 25-27 Sept, the RAAM deck on the 27th, Ken's finale on 10 Oct,
and RAAM rounds 2 and 3 on the 11th and 18th, ending with the in-person RAAM
finale in Hyderabad on the 23rd. The first genuinely open stretch is the last
week of October. Four weeks from there, at the rate this kind of work actually
moves, lands on 22 November.

Artifacts due that day:

- [ ] Public repo, permissive licence, `git log` checked for co-author
      trailers before the first push.
- [ ] Container image on GHCR, pull-and-run in one command.
- [ ] README whose first screenful is section 4 above, with the placeholders
      replaced by measured numbers.
- [ ] `RESULTS.md`: leaderboard table, held-out results reported separately
      from development results in the same table, and a section listing every
      Phase 5 prediction that turned out wrong.
- [ ] Data card: provenance and licence for every design.
- [ ] `CONTRIBUTING.md`: how to add an agent.
- [ ] Reproduction receipt: one command that regenerates the headline table.
- [ ] 90-second demo video.
- [ ] arXiv preprint, 4 to 8 pages.
- [ ] One LinkedIn post, numbers first.

---

## The gate, answered

Question 3 is falsifiable and is not answered by anything in `PRIOR_ART.md`.
The gate passes. It passes narrowly: three of the six things this project
originally claimed as novel are already published, and the honest version of
this benchmark is a reliability critique with a harness attached rather than
the field's first timing-closure benchmark.
