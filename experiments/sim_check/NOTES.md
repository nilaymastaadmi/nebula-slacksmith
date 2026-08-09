# Simulation vs formal — the fourth checker, and the escaped-bug mechanism

Run 9 Aug 2026. Icarus Verilog 12.0, Yosys 0.33, z3. 20,000 random vectors per run,
fixed seed (`32'h0C0FFEE`), so every row reproduces exactly.

## Why this column matters most

`cec_check/` showed the three formal checkers all *reject* a correct latency
change. This is the opposite failure and the more dangerous one: simulation
**accepts** rewrites that are formally invalid. It is also what agentic RTL tools
actually gate on in practice — RTLScout's primary correctness gate is a Verilator
testbench, with `abc cec` only as a secondary, opt-in check.

## Setup

Four candidate transforms of `mac_ref`, each the kind of thing a model plausibly
emits when cutting `(a*b)+c` into two pipeline stages. Each is checked by:

- **SIM lazy** — `c` held constant, `a`/`b` random. Not a strawman: a directed
  test for a multiply-accumulate naturally fixes the accumulate operand and
  sweeps the multiplier operands. It is what a human writes, and what a model
  writes when you ask it for a testbench.
- **SIM aggressive** — `a`, `b`, `c` all fresh random every cycle.
- **FORMAL** — the k-padded miter from `toy_miter/`, K=1.

## Results

| Mutant | SIM lazy | SIM aggr | FORMAL | |
|---|---|---|---|---|
| `mut0_correct` | PASS | PASS | **PASSED** | control — everything accepts it ✅ |
| `mut1_stale_c` | **PASS** | FAIL | **FAILED** | **escaped the lazy testbench** |
| `mut2_rare` | **PASS** | **PASS** | **FAILED** | **escaped both testbenches** |
| `mut3_trunc` | FAIL | FAIL | **FAILED** | simulation did its job |

**Two of the three formally invalid transforms would have been accepted by a
realistic simulation gate.**

## What each row shows

**`mut1_stale_c` — stage 2 adds the current `c` to a product from the previous
cycle.** This is *the* classic pipelining bug and the most likely thing to go
wrong when cutting a datapath. It is caught by aggressive stimulus and completely
invisible to the lazy testbench, because with `c` held constant `c == c_q` always.

The lesson is not "write better testbenches." It is that **the verdict depends on
stimulus quality rather than on the severity of the bug.** The same rewrite is
correct or broken depending on who wrote the testbench, which makes any
simulation-gated error rate a measurement of the testbench, not of the model.

**`mut2_rare` — wrong on one input combination in ~10^6.** It survived 20,000
random vectors in both regimes. Formal refuted it immediately, because formal
searches the input space rather than sampling it. Expected hits in 20,000 vectors
is 0.019, so escape here is the *reliable* outcome, not luck.

**`mut3_trunc` — pipeline register one bit narrow.** Caught by everything.
Included deliberately: simulation is not useless, and a matrix where it never
works would be a rigged demo.

## The number this produces, and its honest limits

The headline metric for SlackSmith is **the rate at which a weaker checker would
have wrongly accepted a formally invalid rewrite**, with a counterexample for
every disagreement. This experiment demonstrates the mechanism end to end and
produces a first data point: **2 of 3**.

**That is not a statistic.** n=3, and the mutants were hand-picked by me to span
the failure modes rather than sampled from real model output. Reporting "67% of
invalid rewrites escape simulation" from this would be exactly the kind of
overclaim this project exists to catch.

The real number needs the design already written down in the research notes:
stratify by transform class, use Clopper–Pearson intervals rather than Wald
(which undercovers badly near 0 and 1), escalate difficulty until per-stratum
error crosses 50% so a signal is guaranteed by construction, and size the corpus
from a power calculation — roughly n≈100 per stratum for a ±10 point half-width.

What this experiment establishes is that **the mechanism works and the gap is
real.** The magnitude is future work.

## Reproduce

```bash
iverilog -g2012 -o sim.vvp mac_ref.v mut1_stale_c.v tb.sv
vvp sim.vvp +lazy      # PASS  -- bug invisible
vvp sim.vvp            # FAIL  -- same design, different stimulus
```

## Files

- `mut0_correct.v` … `mut3_trunc.v` — candidate transforms, all named `mac_opt`
  so they drop straight into the testbench and the miter
- `tb.sv` — self-checking testbench with the K=1 scoreboard offset and both
  stimulus regimes
- `mac_ref.v`, `miter.sv` — copied from `toy_miter/`

## Next

The four-checker matrix is now complete as a mechanism: simulation, `abc cec`,
EQY/`dsec`, and the padded miter, all runnable on the same transform. What is
missing is the **corpus** — real model-proposed rewrites rather than hand-written
mutants. That is the build, and it is what turns a demonstration into the paper.
