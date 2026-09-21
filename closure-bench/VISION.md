# Vision: an open benchmark for agentic RTL timing closure

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

**Working name.** This lives on the `feat/closure-bench` branch of the
SlackSmith repo and deliberately does **not** claim the name `SlackBench`,
which is already public in this same repository for the verification-checker
exam. Naming is settled after the Nebula outcome.

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

> On open-source synthesis and STA, at matched budget, the run-to-run standard
> deviation of an LLM agent's WNS improvement exceeds its median advantage over
> a random-transform baseline on a majority of designs - so the single-run and
> mean-of-five rankings published in this literature are not reproducible
> orderings.

Someone can disagree with this. SynAct's authors would: they report a 5-run
mean showing their agent at 27.03% of bootstrap WNS violation against 66.67%
for a classical tuner, which is a wide enough gap that it plausibly survives
its own spread. They do not publish the spread, so neither they nor anyone else
currently knows.

The original candidate claim - that LLM agents do not beat a classical
`repair_design` baseline - was dropped because `PRIOR_ART.md` found it is
already contested and currently points the other way.

## 4. The README's first screenful

> **closure-bench** - does the agent actually close timing, and does it do it
> twice?
>
> A containerised benchmark for LLM agents on RTL timing closure. N designs,
> five baselines, 10 seeds each, Yosys + OpenSTA + sky130hd, one command.
>
> ```
> docker run --rm ghcr.io/<owner>/closure-bench:v1 reproduce
> ```
>
> The headline is not which agent wins. It is that on W of N designs the
> run-to-run spread of the best agent exceeds its own margin over a random
> baseline at the same budget - which means the ordering you get depends on the
> seed you drew.
>
> Every submission must synthesise, pass combinational equivalence checking
> against the original, keep the module interface, and stay within 20% area.
> Every result row carries the harness commit that produced it. Five of the
> designs are a sealed holdout whose SHA256 hashes were published before any
> agent ran.

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
