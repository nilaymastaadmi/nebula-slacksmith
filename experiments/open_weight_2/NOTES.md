# Open-weight run 2: a code-specialised model, and the same wall

Registered in `PREREGISTRATION.md` (`b135ef6`), scripts in `9f5e808`, both
before the model was invoked. **Qwen2.5-Coder-7B-Instruct, Apache-2.0, Ollama
0.34.0, localhost only, no API key.** Same machine as run 1: Intel Iris Xe
integrated graphics, 16 GB RAM, CPU inference.

## Run 1, no JSON mode, matching the first experiment exactly

```
shim: request O1, 18554 chars -> qwen2.5-coder:7b
shim: qwen2.5-coder:7b replied in 1334.8 s, 5756 chars
  online proposer returned nothing usable: reply is not valid JSON:
  Invalid control character at: line 9 column 43 (char 536)
```

**22 minutes, and the identical failure to Qwen2.5-7B-Instruct**: literal
newlines inside a JSON string value, at line 9 both times. Code tuning did not
change the failure mode at all.

## Run 2, `format: json`, the follow-up registered in advance as R84

```
shim: model qwen2.5-coder:7b, json_mode=True
shim: qwen2.5-coder:7b replied in 160.5 s, 916 chars
  online proposal O1: aes_key_mem_retime (declared k=0)
  gate O1: G1=FAIL
no proposal passed the gate.
```

**Valid JSON, in 160 seconds instead of 1,335, and the content still fails at
parse.** The reply declares `obligation_branch: "5 (retiming, sequential
miter)"` with `latency_delta_k: 0`, then emits `module aes_key_mem;` with **no
port list at all**, an `always @(posedge clk or posedge rst_n)` block that
resets on the *rising* edge of an active-low reset, no declaration of `clk`, and
`key_mem` promoted from internal memory to a 256-bit output. `round_key`,
`sboxw`, `round` and `new_sboxw` are gone.

## Scorecard

**R73. WRONG.** Run 1's reply is not valid JSON. The prior was "better than
even" because code-tuned models are drilled against exactly this; it made no
difference.

**R74. WRONG.** No G4 verdict of any kind was reached. **G1 = FAIL**: the
variant does not parse. This is the outcome R44's post-hoc reading of the first
experiment pointed at, now measured rather than inferred.

**R75. VOID.** Nothing was applied and nothing was timed, so "does not improve
`clk_b` by more than 0.436 ns" is true and untested. A prediction that cannot
fail is not evidence, and it is recorded as void rather than banked as a hit.

**R84. CONFIRMED.** The declared follow-up said JSON mode would fix the envelope
and **not** change R74's outcome. It produced valid JSON on the first attempt
and the proposal still died at G1. Registering that in advance is the only
reason it is a result rather than a rescue.

**1 confirmed, 2 wrong, 1 void.**

## What two models and three runs establish

**Correction, 2026-09-14: both runs saw 40% of their request.** Both `META_O1.json` files record
`prompt_eval_count` 2,050 for an 18,554-character request. Sent again to the same model,
Ollama's default options evaluate 2,050 tokens and `num_ctx` 16384 evaluates 5,113
(`experiments/open_weight_3/context_check/`). The scores below stand, because they
score what happened; every reading that the model could not do the task is
withdrawn, because it was never given the whole task. The replay is
`experiments/open_weight_3/`, arm B.

**Withdrawn, see the correction above.** The wall is the engineering, not the envelope. That was the open question
after run 1 of `experiments/open_weight/`, where a failure to emit valid JSON
hid whatever the model had actually designed. Constraining decoding answers it:
the envelope closes in 160 seconds and the content still cannot hold a module
interface or stay inside one HDL.

Across **Qwen2.5-7B-Instruct and Qwen2.5-Coder-7B**, three runs, the same task:
**no proposal has reached the formal gate**. The verification apparatus this
project is built on was never exercised by either model, because nothing got
far enough to be checked.

## What this does not establish

Two models, one size, one sample each, one design, one machine, CPU-only, with a
prompt written and tuned against Claude Opus 5. **7B is small for this task** and
that is the most likely single explanation. A 32B or 70B open-weight model
served over an API is a different experiment and this result does not speak for
it. The claim is: **on this machine, at this size, on this prompt, an
open-weight model did not produce a gateable proposal.**
