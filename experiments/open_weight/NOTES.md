# Open-weight run: results

Registered in `PREREGISTRATION.md` (commit `621e810`), scripts in `5332895`,
both before the model was invoked. Model: **Qwen2.5-7B-Instruct, Apache-2.0,
Ollama 0.34.0, localhost only, no API key of any kind.**

## What happened

```
measure: clk_b=-18.957
classify clk_b: FANOUT_DOMINATED (fanout share 0.9139) -> physical
  LEVER FORCED to rtl: the router chose physical. Disclosed per amendment 1.
ONLINE PROPOSER, handoff backend. The loop is waiting.
shim: request O1, 18554 chars -> qwen2.5:7b-instruct
shim: qwen2.5:7b-instruct replied in 1172.2 s, 9899 chars
  online proposer returned nothing usable: reply is not valid JSON:
  Invalid control character at: line 9 column 43 (char 434)
```

**19.5 minutes of local inference, 9,899 characters back, nothing the loop could
use.** The machine is an Intel Iris Xe integrated GPU with 16 GB of system RAM,
so this ran on CPU.

## Scorecard

**R41. CONFIRMED.** The run completed end to end with **zero changes to any file
under `tools/`**. The adapter is 90 lines in `experiments/open_weight/shim.py`.
Pack §5d's "a flag and a binary, not a port" is now exercised rather than
asserted, and it held.

**R42. WRONG.** The reply is not valid JSON. The model emitted the Verilog with
**literal newlines inside a JSON string value** instead of `\n` escapes, which
is what "invalid control character at line 9 column 43" is. The envelope failed,
not a solver.

**R43. CONFIRMED.** It did not reach a PROVEN, timing-positive result. It did not
reach the gate at all.

**R44. WRONG.** The prediction said that if it failed, it would fail at G1, G2 or
G3. It failed **before G1**, at the schema, so the distinction the prediction was
built to test never got tested by the loop.

*Post-hoc, and labelled as post-hoc because it changes no verdict:* reading the
raw reply, the content would also have failed G1. It emits `module aes_key_mem
(...) is`, which is VHDL, not Verilog. It renames `reset_n` to `rst_n`, exposes
the internal `key_mem` array as an output port, drops the `round_key`, `sboxw`,
`keylen`, `round` and `new_sboxw` ports entirely, and assigns to its own inputs.
The interface is not preserved in any sense. The direction R44 was pointing at is
right; the prediction as written is still wrong, and it is scored wrong.

**R45. WRONG.** The proposal step took **1,172.2 s**, not under 600. Nearly
double, on CPU.

**R46. VOID by its own condition.** It was to be scored only if both model sizes
produced parseable proposals. The 7B did not, so the 3B comparison cannot answer
the question it was registered for.

**2 confirmed, 3 wrong, 1 void.**

## What this actually establishes

The organisers asked entrants to use open source API keys for their models. This
answers with something stronger and worse: a genuinely open-weight model, no key
and no vendor, run against the identical task, the identical SDC and the identical
flags as the Claude Opus 5 run, with the qualifiers REPORT §7.7 already attaches.

**It did not work, and the way it did not work is the useful part.** The failure
was not "the model proposed something and our gate refuted it". It was "the model
could not produce the machine-readable envelope, and separately could not hold a
module interface or stay in one hardware description language". A pipeline like
this one needs a model that can do both before any of the verification apparatus
is even reached.

## What this does not establish

One model, one size, one design, one sample, one machine, on CPU. The prompt was
written and tuned against Claude Opus 5, which is an uncontrolled confound and
plausibly a large one. A coder-specialised open-weight model of the same size, or
a 70B served over an API, is a different experiment and this result does not
speak for it. **The claim is "this model, this prompt, this machine, this task",
and nothing wider.**
