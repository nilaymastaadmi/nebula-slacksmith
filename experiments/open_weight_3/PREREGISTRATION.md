# Pre-registration: a hosted open-weight model, and the local runs' prompt length

Registered 2026-09-14, before any model is invoked for this experiment. Scored in
`NOTES.md` here. Predictions **R100 to R104**.

## Why a third open-weight experiment

The organisers asked for open-source API keys. `SUBMISSION_PACK.md` §5d states
that recommendation is **not met** for the primary result: every proposal that
reached the formal gate came from Claude Opus 5, and the two open-weight models
tried were 7B, on this machine's CPU, under Ollama. Review 6 asked what a larger
open-weight model does with the identical request, and nothing in the repository
answers that.

## Arm A: a hosted open-weight model

**Model:** `google/gemma-4-31b-it:free` on OpenRouter, an OpenAI-compatible
endpoint. 31B dense, weights published as `google/gemma-4-31B-it` under the
Gemma licence (open weights, **not** an OSI open-source licence; the pack will say
so). The endpoint's public `/api/v1/models` listed 22 zero-priced entries on
2026-09-14, so the run needs a free account and no payment. Chosen from them as
the dense instruct model closest to the 32B class review 6 named, and one that
accepts `response_format`, which R104's follow-up needs. Larger zero-priced
open-weight entries exist (Nemotron 3 Super 120B-A12B and Ultra 550B-A55B), but
they are mixture-of-experts with 12B and 55B active parameters and the Ultra
does not list `response_format`; that trade is stated rather than hidden. Context
262,144 tokens, maximum output 32,768.

**Key:** created by the author, stored in `~/.openrouter_key` outside the
repository, read only by `shim_hosted.py`, never printed or committed.

**The task is identical to `experiments/open_weight_2/`**: `aes_key_mem`,
`sdc/bench_top_v3.sdc`, `clk_b`, `--force-lever rtl`, `--max-online 1`,
`--max-iters 1`, `--g5 total`, `tools/proposer_prompt_v2.md`, one sample,
default sampling. **No file under `tools/` changes for this arm.** The request
is the same 18,554-character prompt the local runs were sent. The prompt was
tuned against Claude Opus 5, which is a stated disadvantage for any other model.

**Settings fixed now:** `max_tokens` 16384; no temperature, top_p or reasoning
setting sent; no JSON mode on run 1, because no earlier run 1 used one.

**Retries:** a reply with content is never retried. A transport failure (HTTP
429 or 5xx, or no connection) is retried at most twice, 60 s apart, and every
attempt is recorded in `META`.

**Void conditions, declared now:** the key file is missing; the model is not
listed by the endpoint at run time (no substitute model is run); three transport
attempts fail. A VOID arm is reported as VOID.

### Predictions, arm A

**R100.** The reply yields a valid proposal object through the loop's own
`_extract_json` on the first request. *Prior: better than even. A 31B instruct
model handles a JSON envelope far more reliably than the 7B models did.*

**R101.** The proposal reaches a **G4 verdict of any kind** (PROVEN, REFUTED,
CANNOT, UNRESOLVED), rather than dying at G1, G2 or G3. *Prior: even. Rewriting
a 434-line module while preserving its interface is the hard half, and no
open-weight model has cleared it in this repository.*

**R102.** If R101 holds, the G4 verdict is **PROVEN**. *Prior: weak.*

**R103.** The proposal does **not** improve `clk_b` by more than **0.436 ns**
zero-parasitic, the A5 do-nothing floor from `experiments/llm_proposer_aes/`.
*Prior: strong.* Scored VOID if the proposal never reaches G5.

**R104, the declared follow-up.** If R100 misses because the reply is not valid
JSON, one labelled second run is made with `response_format: json_object`, and
the prediction is that it produces valid JSON. It is reported as a second run and
never merged into R100 to R103.

**Manipulation check, arm A.** The endpoint's reported `usage.prompt_tokens` is
recorded. A count below 3,500 would mean the request was cut, as the local runs'
was (below), and makes arm A VOID rather than a result.

## What was found before this registration: the local runs never saw the whole request

Checking the request size for arm A, all three local runs' `META` files show
**`prompt_eval_count` 2,050** for an 18,554-character request. Measured
2026-09-14 by sending that identical request to the same local model with one
token of output (`context_check/`, `result.json`): **Ollama's default options
evaluate 2,050 tokens; `num_ctx` 16384 evaluates 5,113**, and the model's own
context length is 32,768. So `experiments/open_weight/` and both runs of
`experiments/open_weight_2/` gave the model **40% of the request**. Their scores
stand as written, because they score what happened; the reading drawn from them,
"the wall is the engineering, not the envelope", is withdrawn in `NOTES.md` of
both directories, `REPORT.md` §7.8 and `SUBMISSION_PACK.md` §5d in the same commit
as this registration. Which 40% Ollama kept is not measured here.

This check was run before these predictions were written, and it is a diagnosis
of the earlier runs, not a result of this experiment.

## Arm B: the best earlier local run, replayed with the whole request

**Identical to `experiments/open_weight_2/run_jsonmode.sh`** (Qwen2.5-Coder-7B,
Ollama JSON mode, same task and flags), **with one change: `num_ctx` 16384.**
Chosen because that run is the only local one whose envelope worked, so the
context window is the only variable left between it and a replay. No file under
`tools/` changes; `shim_local.py` is a copy of the earlier shim with a
`--num-ctx` option.

**Void conditions:** Ollama or the model unavailable; the loop's unchanged
1,800 s handoff wait expires before the reply, which on this CPU is possible
(prompt evaluation alone took 706 s at this context in the check above). A
timeout is reported with its times as VOID, and the wait is not lengthened after
the fact.

**Arm A and arm B run one after the other, never together**, so neither's timing
carries the other's CPU load.

### Predictions, arm B

**R105.** The reply's `prompt_eval_count` is **at least 5,000**, so the model saw
the whole request. *Prior: strong; this is the manipulation check, and if it
misses, R106 to R108 are VOID.*

**R106.** The proposal reaches a **G4 verdict of any kind**. *Prior: weak. The
earlier run died at G1 with no port list, which truncation could explain, but a
7B model rewriting a 434-line module is hard with or without it.*

**R107.** If R106 holds, the verdict is **PROVEN**. *Prior: weak.*

**R108.** No `clk_b` improvement beyond the 0.436 ns floor. *Prior: strong.*
Scored VOID if the proposal never reaches G5.
