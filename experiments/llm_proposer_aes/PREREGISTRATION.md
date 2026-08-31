# Pre-registration, batch 2: AES key-memory transforms, and the fanout hypothesis

Written 2026-08-31, **before any batch-2 proposal exists and before the
buffering control has been read**. Registered separately from batch 1 as
that registration requires ("If a second batch is generated, it is
registered separately, its N is added to the trial count, and both batches
are reported").

Git must show this file in an earlier commit than every file in
`experiments/llm_proposer_aes/proposals/`:

    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/llm_proposer_aes/PREREGISTRATION.md \
      experiments/llm_proposer_aes/proposals/

## What is already known at the time of writing, stated so it cannot be backfilled

Known:

- Under SDC v2, artifact-free, `clk_b` and `clk_e` are both at **-4.957 ns**
  and are the two worst groups. `clk_a` is **+1.333 MET**.
- The `clk_b` worst path starts and ends inside `u_aes_b/u_core/keymem/`,
  and **27.045 ns of its 30.6 ns arrival sits in two cells**: 21.029 ns in
  one `nor4_1` and 6.016 ns in one `nor2_1`.
- `rtl/aes/aes_key_mem.v` declares `reg [127:0] key_mem [0:14]` (1,920
  flops), writes it as `key_mem[round_ctr_reg] <= key_mem_new`, and reads it
  **combinationally** as `tmp_round_key = key_mem[round]`, a 15-to-1
  128-bit-wide mux whose select is a 4-bit decode. A decode output therefore
  drives on the order of 128 loads with no buffer-insertion pass in this
  flow.
- `u_aes_b` and `u_aes_e` are two instances of the same module, so one edit
  to `aes_key_mem.v` is measured twice, in two clock groups, at the same
  registered target. This is a built-in replicate and is used as one.

Not known at the time of writing, and deliberately not read before this file
and `proposals/` are committed:

- The result of the buffering control described below. It is running while
  this is being written and its output has not been opened.

## The question, which is different from batch 1's

Batch 1 asked what fraction of LLM proposals survive the gate. It found
4 of 6 proven, 1 of 6 improving timing, and it found that the four proven
transforms mostly made timing **worse**.

Batch 2 asks **why**, with a specific mechanism on trial.

**Hypothesis H (fanout).** The binding constraint on this benchmark is
single-net fanout, not logic depth. If H holds, then:

- (H1) A non-RTL buffering pass should beat every RTL transform in this
  batch on the same path group, because it addresses the actual constraint.
- (H2) An RTL transform that duplicates logic in order to split fanout will
  **not** reduce max fanout, because synthesis (`dch`, `&fraig`, structural
  hashing) re-merges functionally identical cones. If this holds, it is a
  structural reason why LLM RTL rewriting cannot fix this class of path,
  rather than an observation that it happened not to.

H2 is the part worth registering. It predicts a specific null result with a
named mechanism, and it is cheap to refute: if max fanout drops, H2 is
wrong.

## Protocol, fixed in advance

1. **Target.** `rtl/aes/aes_key_mem.v`, the module holding the worst path on
   `clk_b` and `clk_e`.
2. **Proposer.** Claude Opus 5 via this Claude Code session, given the
   OpenSTA `clk_b` critical-path report, `aes_key_mem.v`, and the typed
   transform schema. Same disclosure as batch 1: the proposer has project
   context, and that is a limitation of both batches, stated rather than
   hidden.
3. **N = 6 proposals**, one batch, frozen before any gate runs. **Trial
   count after this batch: 4 prior + 6 batch 1 + 6 batch 2 = 16.**
4. **The anti-tuning rule carries over unchanged.** No proposal is edited,
   replaced or withdrawn after any gate result is seen. Failures are
   reported as failures.
5. **Gates G1 to G5 exactly as batch 1**, same order, same tools, no gate
   skipped for a proposal that reached it.
6. **The four-checker column** on every G4 refutation, as batch 1.
7. **G5 is measured on both `clk_b` and `clk_e`**, and both are reported.
   Per `docs/measurement-methodology.md`, movement in untouched groups is
   reported separately as global-remapping side effect and never folded into
   a transform's claimed benefit.
8. **The buffering control.** `bench_top` is synthesized twice from
   identical RTL and timed under identical SDC, differing only in the ABC
   script: default `-liberty` script versus the same script with
   `buffer -N 16; upsize; dnsize` appended. This is a **non-RTL** change and
   is never reported as a transform result. It is the yardstick H1 is
   measured against, and max fanout is recorded for both.

## The bar, fixed in advance

**Primary:** at least 1 of 6 proposals passes G1 to G4 and improves slack on
`clk_b`.

**Reported regardless:** the full 6-row matrix, both clock groups, and the
buffering control, including the case where the control beats all six. A
batch in which no RTL transform helps and a buffering pass fixes it is a
**more** useful result than a batch with a winner, and will be reported as
the headline rather than buried.

## Predictions, recorded so the misses are visible

1. **≥5 of 6 parse and elaborate.** Confidence: high. Batch 1 got 6 of 6.
2. **≥1 of 6 formally REFUTED at G4.** Confidence: medium-high. Batch 1 got
   2 of 6, but this batch contains more k=0 structural rewrites, which are
   easier to get right than latency changes.
3. **H1: the buffering control improves `clk_b` by more than the best RTL
   proposal in this batch.** Confidence: medium-high. This is the central
   prediction.
4. **H2: no proposal reduces max fanout by more than 20% relative to
   baseline**, including the one written specifically to try, because ABC
   re-merges duplicated cones. Confidence: medium. **This is the prediction
   most likely to be wrong and is registered at medium precisely so that
   being wrong about it is visible.** The plausible alternative is that
   `opt_clean -purge` plus separate always blocks defeat re-merging and
   fanout genuinely drops.
5. **≤2 of 6 improve `clk_b`.** Confidence: medium. Batch 1 got 1 of 6.
6. **The `clk_b` and `clk_e` deltas for the same proposal agree in sign for
   ≥5 of 6 proposals.** Confidence: medium. Same module, same registered
   target, so the local effect should replicate; global remapping is the
   reason it might not.

## What would make this batch void

- Any proposal edited after a gate result is seen.
- The buffering control reported as a transform result, or its RTL treated
  as a proposal.
- Reporting a subset of the 6, or only one of the two clock groups.
- The git ordering check at the top failing.
- Reading the buffering control's output before this file and `proposals/`
  are committed.
