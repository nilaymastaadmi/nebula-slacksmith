# open_weight_3: results

Registered in `PREREGISTRATION.md` (`2b8e5e9`) before either arm ran.

## Arm A: hosted Gemma 4 31B, VOID

Run 2026-09-14, 05:49 to 05:52 UTC. `google/gemma-4-31b-it:free` was listed by
the endpoint, the key file was present, the loop built the identical 18,554-character
request, and **all three transport attempts returned HTTP 429**: the model was
"temporarily rate-limited upstream", `limit_source` `upstream_provider_shared_pool`,
provider Google AI Studio (`results_hosted/META_O1.json`, `shim.log`). The model
never replied, so no sample exists. The loop's "no JSON object in the reply" is the
transport error the shim writes where a reply would go, not a model output.

The registered void condition, three transport failures, applies. No other model
was substituted.

**R100. VOID.** No reply.
**R101. VOID.** No proposal.
**R102. VOID.** No proposal.
**R103. VOID.** No proposal.
**R104. VOID.** Its trigger, an invalid-JSON reply, never occurred.

**Five void, none decided.**

## Still to do

**A hosted open-weight run is an open item, decided by the author on 2026-09-14.**
Any second attempt is a new arm with its own registration, because the free pool's
limit is outside this experiment's control and a different model or a paid route
changes what is being measured. Options recorded at the time: a paid
`qwen/qwen-2.5-coder-32b-instruct` route (Apache-2.0, the same family as the 7B
runs), a wider retry on the free Gemma pool, or the free Nemotron 3 Super
120B-A12B pool.

## Arm B: local Qwen2.5-Coder-7B with the whole request, VOID

Run 2026-09-14, 07:11 to 08:02 UTC, after the demo video was assembled and with
no other run from this project in progress (only document edits and an `ffprobe` read). Same task and flags as
`experiments/open_weight_2/run_jsonmode.sh`, plus `num_ctx` 16384.

**The loop's unchanged 1,800 s handoff wait expired** (`results_local/decisions.jsonl`:
"handoff timed out after 1800s with no response"). The model replied **3,025.3 s**
after the request, 11,808 characters (`results_local/META_O1.json`, `shim.log`).
The registered void condition applies, and the registration forbids lengthening the
wait after the fact, so **the late reply is committed unread by the gate and is not
scored**: `results_local/RAW_O1.txt`.

**R105. VOID.** The arm is void. Recorded as an observation, not a score: the reply's
`prompt_eval_count` is **5,113**, so this time the model did see the whole request.
**R106. VOID.** Not gated.
**R107. VOID.** Not gated.
**R108. VOID.** Not gated.

**Four void, none decided.** Also recorded, not scored: `eval_count` 3,376 output
tokens; prompt evaluation alone took 706 s at this context in `context_check/`, so
generation ran at roughly 1.5 tokens a second on this CPU.

## What the experiment establishes

**Nothing about capability, in either direction.** Arm A never got a reply; arm B
got one too slowly for the loop to use. What it does establish is the correction
above: all three earlier local runs were given 40% of their request, and the claim
built on them is withdrawn. On this machine a 7B model given the whole request
needs about 50 minutes to answer, longer than the loop waits; a test of whether it
can answer well needs faster hardware, a registered longer wait, or the hosted run
still listed as to do.
