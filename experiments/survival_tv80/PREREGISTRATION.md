# Pre-registration: does an unforced, proven RTL transform survive `repair_design`?

Registered 2026-09-15, before the gate change below and before any run. Scored in
`NOTES.md` here. Predictions **R109 to R112**.

## The question

Every proven LLM RTL transform in this repository has either bought nothing that
survived the physical flow or made timing worse (REPORT §7.8): on `bench_top` the
composition lands at −0.237 ns after `repair_design` inside a 0.24 ns floor, and on
the two depth-dominated external designs four proven transforms bought 0.000,
0.000, −0.268 and −0.421 ns unbuffered. Deliverables 2 and 4 are partial for that
reason. This experiment asks once more, with a fixed sample and a bar set before
running: **does an RTL transform that the router chose unaided, that the
engine proposed unattended, and that the gate proved, improve timing after
`repair_design` by more than the design's own noise?**

## Design and why it was chosen

**`tv80s`**, 3,447 cells, the harness of `experiments/depth_tv80/`, unchanged:
`run.sh`'s flags (`--proposer cli`, **no `--force-lever`**, `--max-online 1`,
`--max-iters 2`, `--g5 total`, `tv80.sdc`, clock `clk`) and `measure.sh`'s columns
(A unbuffered, B the ABC lever, C OpenROAD placement before and after
`repair_design`). Chosen because its harness and its floors already exist, which
is the only way this fits in one day, not because of any result.

**Disclosed before predicting:** `depth_tv80` run 3 reached **+0.382 ns** after
repair against a **0.375 ns** post-repair floor, scored void (R80). That near-miss is
known now, so it is **not** evidence for this experiment, and it is why the primary
bar below is twice the floor rather than the floor.

**Floors, from `experiments/depth_tv80/results/survival.tsv`, measured before this
registration:** gold after repair **−2.021 ns**; the one-assignment control
`ctrl_flip` **−1.646**, so a do-nothing-class edit moves post-repair slack by
**0.375 ns**. Unbuffered floor 0.152 ns.

## The one tool change, made before any run

`tools/gate_proposal.py` refuses (`CANNOT`) any module the design instantiates with a
parameter override, and every earlier tv80 proposal targeted `tv80_mcode`, which
Yosys derives with `Mode = 1`. So a new run would return CANNOT for every such
proposal. The change: an explicit `--param NAME=VALUE`, applied to both sides of
the obligation (EQY `chparam`, and the miter's instances), which lifts the refusal
only when supplied; and `tools/slacksmith.py --gate-param` to pass it. **Checked
before any run:** `depth_tv80` run 3's transform must read **PROVEN** with
`--param Mode=1`, as R94 found by hand, and `tools/param_guard_regression.sh` must
still refuse `tv80_mcode` without it.

## Protocol

- **N = 6** new unattended runs, sequential, same flags as `depth_tv80/run.sh`, plus
  `--gate-param Mode=1`. Every run is reported. No run is added or dropped.
- **Every transform the gate reads PROVEN** goes through `measure.sh`, whether or not
  the loop kept it on G5.
- **Stop rule:** no run starts after **19:30 IST**; a run unfinished at **20:30 IST**
  is reported as not completed; results freeze at **21:00 IST** 2026-09-15.
- **Decision declared now:** if R111 holds, the report's deliverables 2 and 4 are
  stated as met with this result as the evidence. If it does not, they are relabelled
  "delivered, with the measured limit" by the author's decision of 2026-09-15, and
  this experiment is reported as a further negative with its N.

## Predictions

**R109.** At least **4 of 6** runs route to RTL with no `--force-lever`. *Prior:
strong; 3 of 3 in `depth_tv80`.*

**R110.** At least **1 of 6** runs produces a transform the gate reads **PROVEN**.
*Prior: moderate; 2 of 3 in `depth_tv80` plus one needing an invariant.*

**R111, the primary.** At least one PROVEN transform's `clk` slack after
`repair_design` beats gold's −2.021 by **more than 0.750 ns** (twice the post-repair
floor), so better than **−1.271**. *Prior: weak. Zero of 23 proven transforms in this
repository have produced a gain that survived the physical flow.*

**R112.** At least one PROVEN transform beats gold after repair by more than **0.375
ns** (one floor), so better than **−1.646**. *Prior: weak.* A result between one and
two floors is **reported and not claimed** as a surviving gain: across the three
earlier tv80 runs and these six, nine samples make one floor too low a bar.
