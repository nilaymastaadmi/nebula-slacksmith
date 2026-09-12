# Block 3: what Nilay does, start to finish

About 45 minutes. You need a stopwatch (phone is fine) and a text editor.
Everything is written down so you do not have to decide anything mid-task.

## Before you start: three files you must NOT open

Opening any of these voids that transform's measurement. They are the answers.

```
experiments/pipeline_cut_domain_a/miter_pipeline_domain_a.sv
experiments/pipeline_cut_domain_a/miter.sby
experiments/fsm_reencode/miter_mapped.sv
experiments/fsm_reencode/miter.sby
```

Also do not open `tools/gate_proposal.py` (it contains the generator that writes
these), and do not open any `prop.eqy` or `miter_prop.sv` under `experiments/`.

If you open one by accident, say so. That transform gets reported as void and
the other two still count. **That is a normal outcome, not a failure.**

## The three tasks

Write each one into `experiments/speedup_step/hand/`, which you create. Time
each separately. **Stop the clock when you believe it is right, not when it
runs.** Whether it runs first time is recorded separately and is the point of
R72.

### Task 1, branch 1: an EQY config. Expect this to be the quick one.

Prove `rtl/rv32i_core.v` equivalent to P2's variant. P2 is described in
`experiments/llm_proposer/proposals/P2.json`; the variant file it names is in
that directory.

Write `hand/p2.eqy`: the `[gold]`, `[gate]`, `[collect]` and `[strategy]`
sections you think EQY needs to prove these two modules equivalent.

Record: **minutes**, and whether you had to look anything up.

### Task 2, branch 2: a k-padded miter, k = 1.

`experiments/pipeline_cut_domain_a/domain_a_clamped_comb.v` is the gold and
`domain_a_clamped_pipelined.v` is the variant. The variant adds **one cycle** of
latency on the interface.

Write `hand/pipeline.sv` and `hand/pipeline.sby`: a SymbiYosys miter that proves
the two agree **with the gold's outputs delayed by one cycle**, plus whatever
reset alignment you think it needs, and a depth you choose.

Record: **minutes**.

### Task 3, branch 4: a mapped-state miter, k = 0.

`experiments/fsm_reencode/domain_b.v` is the gold and `domain_b_onehot.v` is the
variant. The state register is **re-encoded**, so the two designs have no flop
correspondence.

Write `hand/fsm.sv` and `hand/fsm.sby`: a miter that proves the outputs agree
cycle by cycle without assuming any correspondence between the two state
registers.

Record: **minutes**.

## After the three times are recorded

Now you may run them. For each one, note **ran first time: yes or no**, and if
no, one line on what was wrong. Do not fix them beyond that; the fix time is not
being measured and a second attempt does not change the recorded time.

```bash
cd ~/Projects/slacksmith-benchmark && . tools/env.sh && eqy -f experiments/speedup_step/hand/p2.eqy
```

```bash
cd ~/Projects/slacksmith-benchmark && . tools/env.sh && sby -f experiments/speedup_step/hand/pipeline.sby
```

```bash
cd ~/Projects/slacksmith-benchmark && . tools/env.sh && sby -f experiments/speedup_step/hand/fsm.sby
```

## What to hand back

Six numbers and three yes/no answers. Paste this filled in:

```
branch 1 (EQY, P2):              __ min   ran first time: __
branch 2 (k-padded, domain_a):   __ min   ran first time: __
branch 4 (mapped-state, domain_b): __ min ran first time: __
anything you looked up:
anything you opened that you should not have:
```

I score R70 to R72 against `PREREGISTRATION.md`, write the sentence into
REPORT §1.1, and commit your `hand/` files as the artifact.

## Why your times being fast is fine

You wrote these transforms and you know this codebase, so your times are a
**floor** on what a person needs and therefore a **ceiling** on the ratio. The
report sentence says exactly that. A fast time makes the claim smaller and more
defensible, so do not slow down to help the number.
