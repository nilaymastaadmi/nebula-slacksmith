# open_weight_3: results

Registered in `PREREGISTRATION.md` (`490cb44`) before either arm ran.

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

## Arm B: not yet run

Scheduled by the author for after the demo video is assembled, so its CPU time
does not contend with the render. R105 to R108 are unscored until then.
