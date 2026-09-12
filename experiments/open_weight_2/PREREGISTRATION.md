# Pre-registration: an open-weight model that might actually produce a proposal

Registered 2026-09-12, before this model was invoked against this repository.
Scored in `NOTES.md` here. Predictions **R73 to R75**, plus **R84** for the
declared follow-up.

## Why a second open-weight run

`experiments/open_weight/` ran Qwen2.5-**7B-Instruct** and it failed twice over:
the reply was not valid JSON (literal newlines inside a string value), and the
content was partly VHDL and did not preserve the module interface. Pack §5d
therefore reads "portability exercised, capability not demonstrated".

The organisers' recommendation will be read by a judge as a capability
requirement, not a portability one. So the question this run asks is narrow and
answerable: **does a code-specialised open-weight model of the same size clear
the bar the general-purpose one did not?**

## Model

**Qwen2.5-Coder-7B-Instruct, Apache-2.0, Ollama 0.34.0, localhost only, no API
key of any kind.** Same machine as the first run: Intel Iris Xe integrated
graphics, 16 GB system RAM, so CPU inference. The exact tag is recorded in
`NOTES.md` from `ollama list` at run time.

## The task

**Identical to `experiments/open_weight/`**, so the only variable is the model:
`aes_key_mem`, `sdc/bench_top_v3.sdc`, `clk_b`, `--force-lever rtl`,
`--max-online 1`, `--max-iters 1`, `--g5 total`, one sample, default sampling.
The same three qualifiers REPORT §7.7 attaches to the Claude `cli` run apply
here and are not repeated as if they were new.

**No file under `tools/` is modified.** The shim is a copy of
`experiments/open_weight/shim.py` with the model tag changed. The original stays
as the first experiment's artifact.

**Run 1 does not use Ollama's JSON mode**, because the first run did not, and
changing two things at once measures neither.

## Predictions

**R73.** Qwen2.5-Coder-7B returns text from which `_extract_json` recovers a
valid proposal object on the **first attempt**. *Prior: better than even. The
failure that killed the 7B-Instruct run was emitting raw newlines inside a JSON
string, which is a formatting habit code-tuned models are drilled against.*

**R74.** The proposal reaches a **G4 verdict of any kind** (PROVEN, REFUTED,
CANNOT or a partial), rather than dying at G1, G2 or G3. *Prior: weak. The
7B-Instruct's content emitted VHDL syntax and dropped half the port list;
interface preservation on a 434-line module is the harder half of this task and
code tuning does not obviously fix it.*

**R75.** The proposal does **not** improve `clk_b` by more than **0.436 ns**
zero-parasitic, which is the A5 do-nothing floor measured in
`experiments/llm_proposer_aes/`. *Prior: strong. Anything above that floor from
a 7B model on one sample would be the single most surprising result in this
project.*

**R84, the declared follow-up, registered now so it is not a post-hoc rescue.**
If R73 misses, a **second run with Ollama's `format: json`** is made and
labelled, and the prediction is that it produces valid JSON but still does not
change R74's outcome. This separates **envelope failure** from **engineering
failure**, which the first experiment could not do because it never got past the
envelope. The second run is reported as a second run, never merged into the
first, and R73 stays missed regardless of what it returns.

## Void conditions

- Ollama absent, or the model not pulled: **VOID**. Substituting a hosted model
  and calling it open-weight is the one outcome forbidden here, as in the first
  registration.
- If the loop's request differs materially from
  `experiments/open_weight/results/REQUEST_O1.md`, the head-to-head framing is
  withdrawn and this is reported as a fresh run. The diff is committed either
  way.

## Scope

One model, one size, one sample, one design, one machine, on CPU, with a prompt
written and tuned against Claude Opus 5. That last one is an uncontrolled
confound and is plausibly large. A negative result is evidence about **this
model on this prompt**, not about open-weight models.
