# Pre-registration: the same loop, driven by an open-weight model

Registered 2026-09-12, before any open-weight model was invoked against this
repository. Scored in `NOTES.md` here. Predictions R41 to R46.

## Why this experiment exists

The organisers asked entrants to use open source API keys for their models.
`SUBMISSION_PACK.md` §5d answers that with a capability rather than a
demonstration: it says the proposer is portable, that `--proposer handoff`
takes a prompt file and a JSON reply, and that swapping in an open-weight model
is "a flag and a binary, not a port". Every committed proposal in this
repository came from Claude Opus 5.

A claim about portability that has never been exercised is the same class of
claim this project has retracted twice already: the page count measured by a
proxy, and "everything reproduces from the repository" asserted while every
script began `cd /mnt/c/Users/toshn/...`. So the claim gets run.

## What is run

**Model: Qwen2.5-7B-Instruct, Apache-2.0, running locally under Ollama
0.34.0.** No API key of any kind, no hosted endpoint, no network call. That is
a stronger form of the organisers' request than an open source API key: there
is no key and no vendor in the path.

**The task is the one Claude Opus 5 already did**, so this is a head-to-head
with the request held fixed: SDC v3, `clk_b`, `--force-lever rtl`,
`--max-online 1`, `--max-iters 1`, `--g5 total`, the same flags
`experiments/cli_backend/run.sh` used, with the same three qualifiers REPORT
§7.7 attaches to that run. The comparison is the model, not the harness.

**No file under `tools/` is modified.** The shim that carries the prompt to
Ollama and the reply back lives in this directory, because the claim being
tested is that the existing handoff backend is enough.

## Predictions

**R41.** The run completes end to end with **zero changes to any file under
`tools/`**. If `proposer.py` has to be touched, §5d's "no code change" is
wrong and the pack gets corrected rather than the claim defended.

**R42.** Qwen2.5-7B returns text from which `_extract_json` recovers a valid
proposal object on the **first attempt**. Registered as genuinely uncertain:
small instruct models commonly wrap JSON in prose, emit trailing commas, or
answer with a plan instead of the schema.

**R43.** The open-weight proposal does **not** reach a PROVEN and
timing-positive result. Opus 5's own unattended run on this same path needed a
forced lever and produced +1.414 ns only when measured outside the loop; a 7B
model is being asked to rewrite a 434-line AES key memory under a formal gate.

**R44.** If it fails, it fails at **G1, G2 or G3**, not as a G4 REFUTED. A
model that cannot hold the module interface stable never reaches the solver.
This one distinguishes "the model cannot write legal Verilog for this module"
from "the model wrote something plausible and wrong", and those are different
findings about open-weight models in this workflow.

**R45.** The proposal step takes **under 600 s** on this machine.

**R46.** The same request answered by Qwen2.5-**3B** produces a **different
transform type** from the 7B, extending §5d's nondeterminism finding across
model sizes. Scored only if both produce parseable proposals.

## Void conditions

- Ollama not running, or the model absent: report **VOID**. Do not substitute a
  hosted model and call it open-weight.
- If the loop's request differs materially from `experiments/cli_backend/results/run1/REQUEST_O1.md`,
  the head-to-head framing is withdrawn and this is reported as a fresh run
  rather than a comparison. The diff is committed either way.

## What this does not establish

One model, one design, one path, one sample per model. A negative result here
is evidence that this workflow needs a strong model, not evidence that no
open-weight model can do it. The prompt was written and tuned against Claude
Opus 5, which is itself a confound and is not controlled for.
