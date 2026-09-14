# Batch 2: AES key-memory transforms, 6 of 6 results

Run 2026-08-31. Protocol fixed in advance in `PREREGISTRATION.md` (commit
`dbcd7d3`); proposals frozen before any gate ran (commit `004695c`). Git
proves that ordering:

    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/llm_proposer_aes/PREREGISTRATION.md \
      experiments/llm_proposer_aes/proposals/

Registered separately from batch 1 as batch 1's own terms require. **Trial
count after this batch: 16** (4 prior + 6 batch 1 + 6 batch 2).

Target: `rtl/aes/aes_key_mem.v`, which holds the worst path on both `clk_b`
and `clk_e` (-4.957 ns each under the frozen v2 SDC). `u_aes_b` and `u_aes_e`
are two instances of the same module, so one edit is measured twice in two
clock groups. That replicate is used rather than assumed.

Proposer: Claude Opus 5 via the Claude Code session driving this project.
Disclosed, not disguised; the proposer has project context, which is a
limitation of both batches.

## Results, all 6, as registered

| | transform | declared | G1 | G2 | G3 | G4 | G5 clk_b | G5 clk_e | G5 clk_a |
|---|---|---|---|---|---|---|---|---|---|
| A1 | mux_bank_split | k=0 | PASS | PASS | PASS | **PROVEN** | +2.020 | +2.020 | +0.454 |
| A2 | decode_duplication | k=0 | PASS | PASS | PASS | **UNRESOLVED** | n/a | n/a | n/a |
| A3 | read_port_register | k=1 | PASS | PASS | PASS | **REFUTED** | n/a | n/a | n/a |
| A4 | onehot_read_select | k=0 | PASS | PASS | PASS | **PROVEN** | **+4.925** | **+4.925** | +0.987 |
| A5 | reset_unroll (control) | k=0 | PASS | PASS | PASS | **PROVEN** | +0.436 | +0.436 | +0.000 |
| A6 | key_mem_parity_split | k=0 | PASS | PASS | **FAIL** | n/a | n/a | n/a | n/a |

Cells (gold 7,975): A1 8,229, A2 8,034, A3 8,079, A4 8,149, A5 7,988,
A6 8,661. Flops (gold 4,386): unchanged except A3 and A6, both +256.

**3 of 6 formally proven. 1 of 6 formally refuted. 1 of 6 unresolved.
1 of 6 rejected at precondition. 3 of 6 improved the touched groups.**

A2's row says UNRESOLVED because of a bug in our own gate that this batch
exposed. It is written up in full below, because it is the most important
thing batch 2 found and it is a defect in the tool rather than in a proposal.

**Registered primary bar: MET.** A4 passes every gate and takes `clk_b` from
-4.957 to **-0.032**, a 99.4% reduction in the violation, without adding
storage.

## A6: the precondition gate fires for the first time in this project

Batch 1 registered that at least one proposal would be rejected at G3, and
**none was**. Batch 1 reported that as its most useful miss: the precondition
layer as implemented was a type check, not a legality check, and the formal
gate was doing all the work.

Batch 2 is the follow-up, and G3 fired. A6 splits `key_mem [0:14]` into an
even array and an odd array of **8 entries each**. That is 16 words of
storage where the design had 15. A6 declared k=0, the flop count moved by
+256, and G3 rejected it before any solver ran:

    G3: FAIL(declared k=0 but flop count changed by +256)

This is the case the check exists for. A transform that silently changes the
amount of state would, if trusted, have had a **combinational** equivalence
obligation generated for it, which is the wrong obligation. G3 is what stops
the wrong obligation being emitted and then passed.

One batch is not a rate. But batch 1's finding was "G3 screens nothing", and
that is now false as stated.

## A3: a partial latency change is not a k=1 transform

A3 registers the `round_key` read port, declares k=1, and is refuted in
0 seconds by BMC and 1 second by PDR, failing on **`eq_ready`**.

Correct, and the reason is worth stating. The k-padded obligation delays
*every* gold output by k and compares. A3 delayed `round_key` only; `ready`
and `sboxw` still respond in the same cycle. So the design is neither the
original interface nor a uniformly-delayed one, and no fixed-offset
obligation can hold. A declared k=1 rigid transform is a claim about the
whole interface, not about one port.

This is the same shape as batch 1's P5 and the earlier
`pipeline_cut_domain_a`, from a different direction: P5 delayed a signal
inside a feedback machine, A3 delayed one output out of three.

## A2: our gate reported a timeout as a refutation

This is the finding of batch 2, and it is a bug in SlackSmith, not in a
proposal.

A2 splits `key_mem` into four 32-bit arrays, writes them at the same index,
and reads them back concatenated. It is equivalent by inspection. The gate
reported **REFUTED**, isolating one failing partition out of 573:
`aes_key_mem_gold.round_key`. That looked like a second P4.

It is not. Three things did not add up.

**1. Simulation says the designs agree.** Gold and gate driven in lockstep,
all 16 values of `round` after a real key expansion:

| checker | verdict |
|---|---|
| EQY (formal), depth 5 | reported REFUTED |
| simulation, gold vs gate in lockstep, all 16 values of `round` | **MATCH on all 16** |

**2. Every partition feeding the failing one had passed.** `round_key` is
driven by `assign round_key = tmp_round_key;`. EQY proved **128 of 128**
`tmp_round_key` partitions equivalent and failed **0**. An output that is a
plain alias of 128 proven-equivalent bits cannot be inequivalent.

**3. The partition's own log never mentions a counterexample.** It ends:

    Reached maximum number of time steps -> proof failed.
    Dumping SAT model to VCD file trace.vcd

That is **bound exhaustion**, not refutation. The `round_key` partition
carries the whole 1,920-flop `key_mem` array as state, and `depth 5` is not
enough to relate it.

Re-running the whole batch-2 obligation at **depth 40** does not fix it: every
other partition proves in about a second, and `round_key` alone runs past a
**1,800 s** wall without a verdict. So A2 is not "nearly proved"; the
obligation as EQY partitions it is expensive in a way more depth does not
solve, and a better obligation is needed rather than a bigger budget.

**The bug.** EQY prints `Failed to prove equivalence` for both outcomes, and
`tools/gate_proposal.py` matched on that string and called it REFUTED:

    f = re.search(r"Failed to prove equivalence for (\d+)/(\d+) partitions", out)
    ...
    elif f: res["G4"] = "REFUTED (...)"

So the gate reported an **unresolved** obligation as a **refuted** one. That
is the precise error this project has been most careful about, committed by
the project's own tool. Fixed: the gate now reads each failing partition's
strategy log and separates `Assert failed` / `model found` (a real
counterexample) from `Reached maximum number of time steps` (a bound), and
reports UNRESOLVED for the latter.

**Does the correction cascade to batch 1? No, and that was checked rather
than assumed.** P4's partition log ends

    SAT temporal induction proof finished - model found for base case: FAIL!

with a concrete trace: `a = ae19f605` (negative), `shamt = 7`, gold
`alu_out = ff5c33ec`, which is the arithmetic shift. A logical shift gives
`015c33ec`. That is the documented SRA/SRL signedness defect, and it was
independently confirmed by a directed simulation before any of this
(`gold ffffffff` vs `gate 0fffffff`). **P4 stands as REFUTED.**

**Two hypotheses tested and both wrong, recorded because they were wrong.**
Before reading the partition log we guessed the disagreement lived at
`round=15`, an out-of-range read of a `[0:14]` array that simulation resolves
to `x` on both sides. Two experiments refuted that:

1. Wrapping both designs so `round` is clamped to 0..14 (`a2eqy`): still
   failed. EQY proves each partition with its inputs as **free variables**, so
   an external clamp never reaches the partition's cone. The experiment did
   not test what it was built to test.
2. Clamping the read index *inside* both designs, an identical edit to gold
   and gate (`a2inner`): still failed. So `round=15` was not the cause at all.

Only then did reading the log give the actual answer. Both dead ends are
recorded because the first one is a trap worth knowing about: **a constraint
applied outside an EQY partition does not constrain that partition.**

**What this does to the batch 1 / batch 2 pairing.** The intended story was
"formal catches what simulation misses (P4), and formal also rejects things
simulation accepts (A2)". Only the first half survives. The second half is
now a different and more useful lesson: **an equivalence tool's failure
output is not a verdict until you read which kind of failure it was**, and a
gate that does not distinguish them will manufacture refutations.

## A5, the control, is not zero

A5 replaces a reset `for` loop with 15 explicit assignments. It is
functionally identical and touches nothing on the read path. It measures
**+0.436 ns on `clk_b` and `clk_e`, and exactly +0.000 on `clk_a`**.

So +0.436 is this module's same-module remapping floor, not a transform
effect. Read against it:

| | raw clk_b gain | above the A5 control |
|---|---|---|
| A1 | +2.020 | +1.584 |
| A4 | +4.925 | **+4.489** |

This is why the control was registered. Reporting A4 as +4.925 without it
would attribute 0.436 ns of ABC remapping to the transform. The `clk_a`
+0.000 also re-confirms `docs/measurement-methodology.md` finding 2: the
flow itself contributes no noise, and the +0.436 is a real, deterministic,
non-local consequence of editing the module.

## H2 confirmed: not one proposal reduced fanout

Registered prediction 4 said no proposal would cut max fanout by more than
20%, because synthesis re-merges duplicated cones. It was registered at
medium confidence and flagged as the one most likely to be wrong.

Max fanout on any net inside `aes_key_mem`:

| netlist | max fanout | 2nd | nets >= 32 |
|---|---|---|---|
| baseline (gold) | **2193** | 2193 | 46 |
| A1 variant | **2193** | 2193 | 44 |
| A4 variant | **2193** | 2193 | 44 |
| A5 variant | **2193** | 2193 | 47 |

**0.0% change in all three.** H2 holds.

And this is where the result gets more interesting than the prediction. A4
improved `clk_b` by 4.925 ns **while leaving max fanout exactly unchanged**.
So an RTL transform can move a fanout-dominated path, and the mechanism is
not fanout reduction: it is restructuring what sits in series with the
high-fanout net. That refines the fanout story rather than contradicting it.
The buffering control still gained **3.6x more** on the same group
(+17.557 vs +4.925), which is what H1 predicted.

## Registered predictions, including the one that was wrong

1. ≥5 of 6 parse and elaborate. **CORRECT** (6 of 6).
2. ≥1 of 6 formally REFUTED. **CORRECT, but only just** (1 of 6, A3). It
   read as 2 of 6 until the A2 misclassification above was found, so this
   prediction was briefly being scored on a tool bug rather than on a result.
3. H1: the buffering control beats the best RTL proposal on `clk_b`.
   **CORRECT**, +17.557 vs +4.925.
4. H2: no proposal cuts max fanout by more than 20%. **CORRECT**, 0.0% for
   all three measured.
5. ≤2 of 6 improve `clk_b`. **WRONG. 3 of 6 did** (A1, A4, and the A5
   control). Registered at medium confidence and reported as a miss. The
   honest reading is that A5 improving anything is itself the finding: a
   transform that does nothing functional still moved the group by 0.436 ns.
6. `clk_b` and `clk_e` agree in sign for ≥5 of 6. **CORRECT**, and stronger
   than registered: all three measured proposals produced **identical**
   deltas in the two groups, which is the replicate behaving exactly as two
   instances of one module should.

## Three harness bugs, all ours, all found by running

A3 reported `UNRESOLVED` twice before it produced a verdict.

1. `run_proof.py` could not find `sby` on PATH. Reported as UNRESOLVED.
2. Fixed that, and our own generalization patch to `gate_proposal.py` had
   broken an f-string prefix, so `{max(k,1)}` was written into the generated
   miter as literal Verilog and Yosys reported ``Can't resolve function name
   `\max'``. Reported as UNRESOLVED again, with a different cause.

Both were harness failures, not verdicts, and neither was reported as a
transform result. Fixed and re-run, A3 is **REFUTED**.

3. The A2 misclassification above: the EQY branch reported a depth-exhausted
   proof as a refutation.

Bugs 1 and 2 are the safe direction. A real result was hidden behind
UNRESOLVED, and the standing rule that UNRESOLVED is never read as a verdict
is what forced them out. **Bug 3 is the dangerous direction**: it turned a
non-result into a confident REFUTED, and no rule caught it. What caught it
was noticing that a partition failed while all 128 partitions feeding it had
passed. The fix makes the tool distinguish the two cases; the lesson is that
the safeguard only ever pointed one way.

## Honest limits

- N=6, one batch, one target module, one proposer model. Outcomes, not rates
  with confidence intervals.
- G5 is reported for `clk_b` and `clk_e`, the groups the transform touches,
  plus `clk_a` for completeness. Per `docs/measurement-methodology.md`,
  movement in untouched groups is a global-remapping side effect and is not
  folded into any claimed benefit.
- A2 and A3 were not timed, per the registered protocol: timing a refuted
  transform measures nothing.
- The buffering control is a control. It changes no RTL and is never counted
  as a SlackSmith result. See `experiments/buffering_control/NOTES.md`.

## Files

`PREREGISTRATION.md`, `proposals/A1..A6.json` and the six full module
variants (frozen pre-gate), `fourchecker/tb_a2.v`,
`fourchecker/miter_a2_guarded.sv`.

---

## Annotation 2026-09-11: A3's refutation was re-checked and holds

A3's `REFUTED` was published on a sequential miter that, it turned out, also
**refutes `aes_key_mem` against itself**. `round_key = key_mem[round]`, Yosys
does not apply the module's async reset to a memory, and the two instances
start from independent arbitrary contents. Found while gating an unrelated
retiming proposal (`experiments/missing_classes/`, amendment 3).

That made A3's verdict **confounded**: its stated mechanism was plausible, but
the evidence could not distinguish it from the artifact.

It can now. `tools/gate_proposal.py` runs a null control before reporting any
refutation, and where the control fails it identifies *which* outputs the
harness cannot decide and decides the rest. Re-run unchanged:

| | result |
|---|---|
| null control | **REFUTES on `round_key`; PASSES on `ready`, `sboxw`** |
| A3 | **REFUTED (partial: 2 of 3 outputs)**, failing on `eq_ready` |

`ready` is an output the control proves, so A3 fails on a decidable output.
**The published verdict stands, for the published reason**: A3 declared k = 1
and delayed one of three outputs while the k-padded obligation delays all of
them. The table above and the "1 of 6 formally REFUTED" count are unchanged.

Nothing in this file was edited. This annotation is the record.
