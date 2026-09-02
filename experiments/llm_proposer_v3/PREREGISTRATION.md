# Pre-registration, batch 3: does the gate's own output make the next batch better?

Written 2026-09-01, **before any batch-3 proposal exists**. Registered
separately from batches 1 and 2 as their terms require. Git must show this
file and everything in `inputs/` in an earlier commit than every file in
`proposals/`:

    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/llm_proposer_v3/PREREGISTRATION.md \
      experiments/llm_proposer_v3/inputs/ \
      experiments/llm_proposer_v3/proposals/

**Trial count after this batch: 4 prior + 6 + 6 + 12 = 28.**

## Why this batch, stated plainly

Every LLM result in this project so far is negative. Batch 1: 4 of 6 proven,
3 of those made timing worse. Batch 2: the best gain was +4.925 against
+55.805 from a pass that changes no RTL. The closed loop under SDC v3 proved
P1, P2 and P3 correct and reverted all three for making `clk_a` worse.

A judge will ask whether the model ever helps. This batch is the first
attempt at a yes, designed so that a no is equally reportable.

Two things were never given to the proposer in batches 1 and 2:

1. **The classified path.** It got a raw OpenSTA dump. `tools/classify_path.py`
   now says *why* a path is slow and *which module* owns the delay. Whether
   that is actionable for a model, not only for a person, has not been tested.
2. **The gate's refutations.** P4's counterexample (`a=ae19f605, shamt=7`,
   gold `alu_out=ff5c33ec`), P5's and A3's latency failures, A6's silent
   storage change, and the three G5 reverts. No other team has formal
   counterexamples to feed back, because no other team has the gate that
   produces them. If they make the next batch better, the loop closes
   *scientifically*, which is the entire argument for a formal oracle in it.

## The target

The post-buffering `clk_a` path under `sdc/bench_top_v3.sdc`, slack **-1.716**,
which the closed loop classified **DEPTH_DOMINATED at fanout share 0.000,
17.13 ns over 33 cells**. It is the one place on this benchmark where an RTL
transform has something to bite on, and where three proven transforms have
already failed. The path crosses `rv32_load` (wrapper, holds the 6.762 ns top
cell) and `rv32i_core`. Both files are in scope for proposals.

`inputs/` holds the exact netlist, the full path report, and the classifier's
JSON. Those are the proposer's input and they are frozen with this file.

## Two arms, because otherwise nothing can be attributed

| arm | proposer receives | N |
|---|---|---|
| **A** classified | `inputs/path_report_clk_a.txt`, `inputs/classify_clk_a.json`, `rtl/rv32i_core.v`, `rtl/rv32_load.v`, the typed transform schema | 6 |
| **B** classified + feedback | everything in A, plus `inputs/refutation_dossier.md` | 6 |

A alone tests whether the classified report helps. B minus A tests what the
counterexamples add. Without A, an improvement in B could be either.

## Protocol, fixed in advance

1. Arm A is generated and frozen before the proposer is shown the dossier.
   Arm B is generated after. Both are committed before any gate runs.
2. **Proposer isolation, and its limit.** The proposer for batches 1 and 2 was
   this Claude Code session, which has full project context and cannot
   un-know the refutations. For a fair A/B, each arm should be a fresh model
   instance that has seen only its own inputs. Which of the two was used is
   recorded here before generation:

   PROPOSER: __to be filled before proposals/ is created__

   If it is this session, arm A is contaminated by knowledge of the
   refutations and the A/B contrast is weakened; that is disclosed, not hidden.
3. **Anti-tuning rule, unchanged.** No proposal edited, replaced or withdrawn
   after any gate result. All 12 reported.
4. **Gates G1 to G4** via `tools/gate_proposal.py`, same order, none skipped.
   `tools/verdict_regression.sh` is run first: P4 must read REFUTED and A2
   must read UNRESOLVED, or the gate is not trusted for this batch.
5. **G5 is measured in the buffered v3 context**, because
   `docs/closed-loop.md` showed the same transform flips sign between the
   unbuffered and buffered contexts (P2: +0.485 to -0.485). Baseline is
   **-1.716** on `clk_a`. Improvement means strictly greater than -1.716 plus
   the attribution floor below.
6. **Attribution floor.** Batch 2 measured +0.436 of same-module remapping on
   a functionally identical edit to `aes_key_mem`. No such control exists for
   `rv32i_core`. One is run before G5: a functionally identical, no-logic
   change edit to `rv32i_core.v` (reset-style restructure), measured in the
   same context. Its |delta| is the floor. A proposal counts as improving
   only if it beats the floor.
7. **Four-checker column** on every G4 refutation, as before.
8. **Signedness audit.** Every proposal is checked, by reading, for the P4
   defect class (signed and unsigned branches of one conditional). Recorded
   per proposal regardless of gate outcome, because a proposal can avoid the
   bug and still be refuted for another reason.

## The bar, fixed in advance

**Primary:** at least 1 of 6 in arm B passes G1 to G4 and improves `clk_a`
beyond the attribution floor at G5.

**Reported regardless:** all 12 rows, both arms side by side, the floor, the
signedness audit, and the four-checker column.

## Predictions, recorded so the misses are visible

1. ≥10 of 12 parse and elaborate. High.
2. **Arm B has no more G4 refutations than arm A.** Medium. This is the
   "counterexamples improve correctness" prediction.
3. **≥1 of 6 in arm B improves `clk_a` beyond the floor.** Confidence:
   **LOW to MEDIUM, and this is the one most likely to be wrong.** Three
   proven transforms have already failed here. Registered at low confidence
   so that a miss is a finding rather than an embarrassment.
4. **Zero proposals in arm B contain the P4 signedness defect.** High. Direct
   test of learning from a counterexample. No prediction is made for arm A.
5. **≥1 proposal in each arm targets `rv32_load`** rather than `rv32i_core`,
   because the classified report puts the top cell there. Medium. Tests
   whether the proposer reads the classifier at all.
6. Arm A's G5 outcomes resemble batch 1's (most proven proposals make timing
   worse). Medium. Classified input alone does not fix relevance.

## What would make this batch void

- Any proposal edited after any gate result.
- Arm B generated before arm A was frozen, when the same proposer is used.
- The PROPOSER line above left unfilled when `proposals/` is created.
- `tools/verdict_regression.sh` failing before the gates run.
- Reporting a subset of the 12, or one arm without the other.
- The git ordering check at the top failing.
