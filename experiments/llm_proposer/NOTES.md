# LLM-proposed transforms through the SlackSmith gate: 6 of 6 results

Run 2026-08-31. Protocol fixed in advance in `PREREGISTRATION.md` (commit
`04fa59c`); proposals frozen before any gate ran (commit `115fc03`). Git
proves that ordering:

    git log --diff-filter=A --format='%ad %h %s' --date=short -- \
      experiments/llm_proposer/PREREGISTRATION.md \
      experiments/llm_proposer/proposals/

Proposer: Claude Opus 5, via the Claude Code session driving this project,
given the OpenSTA critical-path report on the v2 benchmark, `rtl/rv32i_core.v`
and the typed transform schema. Disclosed, not disguised. No proposal was
parsed, elaborated, checked or timed before all 6 were committed.

## Results, all 6, as registered

| | transform | declared | G1 parse | G2 elab | G3 precond | G4 formal | G5 clk_a slack |
|---|---|---|---|---|---|---|---|
| P1 | operator_sharing_addsub | k=0 | PASS | PASS | PASS | **PROVEN** | -1.555 |
| P2 | operator_sharing_shifter | k=0 | PASS | PASS | PASS | **PROVEN** | **+0.485** |
| P3 | operator_sharing_comparator | k=0 | PASS | PASS | PASS | **PROVEN** | -2.102 |
| P4 | mux_priority_to_parallel | k=0 | PASS | PASS | PASS | **REFUTED** | n/a |
| P5 | pipeline_cut_rigid | k=1 | PASS | PASS | PASS | **REFUTED** | n/a |
| P6 | operator_sharing_branch_comparator | k=0 | PASS | PASS | PASS | **PROVEN** | -1.615 |

Cells (gold 8,269): P1 8,362, P2 **7,918**, P3 8,409, P4 8,061, P6 8,380.

**Registered primary bar: MET.** P2 passes every gate and improves the
touched path group. It is also the only proposal that is both smaller
(-351 cells, -4.2%) and faster.

**4 of 6 formally proven. 2 of 6 formally refuted. 1 of 6 improved timing.**

## The result that matters: P4

P4 applied `mux_priority_to_parallel` to the ALU case statement, one-hot
decoding `funct3` and OR-ing masked arms. It parses, elaborates, passes the
precondition check, reduces cell count by 208, and is **wrong**.

EQY refuted it in 46 seconds, isolating exactly one failing partition out of
447: `rv32i_core_gold.alu_out`.

The mechanism. P4 folded the shift arms into a ternary:

    wire [31:0] r_shr = alt ? ($signed(a) >>> shamt) : (a >> shamt);

A conditional operator's result signedness is derived from **both** branches.
Pairing a signed branch with an unsigned one makes the whole expression
unsigned, that context propagates back into the operands, and `>>>` silently
degrades to a logical shift. SRA/SRAI is then wrong for every negative
operand.

The part worth stating plainly: `rtl/rv32i_core.v` carries a six-line comment
warning about **exactly this**, ten lines above the code being transformed,
explaining why SRA and SRL are written as separate assignments rather than as
two branches of one ternary. The proposer had that file as input and made the
documented mistake anyway.

## Four-checker column on P4 (registered as a primary output)

Would a testbench have caught it? Both cores driven in lockstep, all eleven
architectural outputs compared.

| checker | verdict |
|---|---|
| EQY (formal) | **CAUGHT**, 46s, partition `alu_out` |
| simulation, the real firmware loop shipped in `rv32_load.v`, 400 cycles | **MISSED** |
| simulation, 20,000 random instruction words | **MISSED** |
| simulation, directed SRAI on a negative operand | CAUGHT (gold `ffffffff`, gate `0fffffff`) |

The null results were verified rather than assumed: the directed test proves
the bug is fully visible to simulation, so the two misses are stimulus
weakness, not a phantom defect. The shipped firmware loop contains no shift
instruction at all, so it can never reach the bug. 20,000 random instruction
words miss because a random 32-bit word is rarely a valid SRAI whose source
register happens to hold a negative value.

This extends the project's day-one `sim_check` finding from a hand-built
mutant to a real LLM proposal: **the verdict tracks stimulus quality, not bug
severity.**

## P5: the k-padded obligation refuting a latency change on a feedback machine

P5 declared k=1 and registered `alu_out`. The k-padded miter refuted it in
1 second (BMC) and 3 seconds (PDR), failing on `eq_dmem_addr`. Correct, and
for the same reason as `pipeline_cut_domain_a`: `alu_out` feeds the register
file and the PC, so delaying it does not shift the output stream by one
cycle, it changes the machine. A fixed-offset obligation is the right
obligation to emit for a declared k=1 rigid transform, and the right answer
here is refutation.

## Registered predictions, including the two that were wrong

1. ≥5 of 6 parse and elaborate. **CORRECT** (6 of 6).
2. ≥1 of 6 rejected at G3 precondition. **WRONG. 0 of 6 were.** The
   precondition layer as implemented (declared-latency consistency plus
   latch-freedom) screened nothing; every rejection came from the formal
   gate. This is the most useful miss in the batch: it says the current
   precondition checks are type checks, not legality checks, and that the
   formal gate is doing all the real work. Reported prominently rather than
   quietly dropped.
3. ≥1 of 6 formally refuted. **CORRECT** (2 of 6), and P4 is the strongest
   single piece of evidence this project has produced.
4. ≤2 of 6 improve timing. **CORRECT** (1 of 6). Four transforms that are
   formally proven correct make the critical path worse.
5. The dominant failure mode will be latency semantics rather than width or
   truncation handling. **NOT CONFIRMED.** One of each: P5 latency, P4
   signedness context. Registered at LOW confidence precisely so this would
   stay visible.

## Two measurement errors caught during the run, both reported

**A wrong number that was nearly reported.** P2's first G5 measurement showed
+5.105 ns against a baseline built without `opt_clean -purge`. Rebuilding
both sides identically gave +0.829 ns at the time, and +0.485 ns after the
third correction below. The unmatched comparison overstated the win by 6x
against the same-day rebuild, and by 10.5x against the final figure. The rule that caught it is the one already in
`docs/measurement-methodology.md`: baseline and variant must be built by the
same flow, or the delta measures the flow.

**A Yosys-to-OpenSTA interoperability gap.** P2 was initially unmeasurable:
it is the only proposal using a Verilog `function`, and Yosys names function
temporaries `\rev32$func$/abs/path/rv32i_core_P2.v:101$4454.i`. OpenSTA's
Verilog reader rejects that escaped identifier with a syntax error, so a
netlist that synthesized cleanly could not be timed at all (1,386 such
names). `opt_clean -purge` removes them; it is now in `tools/remeasure.py`
permanently. Without that fix the single successful proposal in this batch
would have been recorded as unmeasurable.

## Honest limits

- N=6, one batch, one target module, one proposer model. These are outcomes,
  not rates with confidence intervals.
- G3 screened nothing (prediction 2), so this batch does not evidence the
  precondition layer's value; it evidences the formal gate's.
- G5 deltas are the `clk_a` group only, which is the group the transforms
  touch. Per `docs/measurement-methodology.md`, other groups move through
  global remapping and are not attributed here.
- The 4 proven transforms making timing worse is consistent with, not
  independent of, the earlier `pipeline_cut_domain_a` result.

## Files

`PREREGISTRATION.md`, `proposals/P1..P6.json` (frozen pre-gate),
`tools/gate_proposal.py`, `results/` (per-proposal gate output and logs),
`fourchecker/` (the P4 testbenches and their output).

## CORRECTION 2026-08-31 (third measurement error, found after first publication)

Every G5 number in the table above was re-measured and changed. The
`dont_use` exclusion introduced to remove the `lpflow` artifact
(`docs/measurement-methodology.md` finding 1) **was never actually in
effect**: the liberty writes `cell ("name")` with quotes and the regex
generating the flags expected `cell (name)` without, so it silently returned
zero flags. The netlists carried 203 `lpflow` cells and a 12.8 ns
single-cell artifact on the critical path.

Caught by seeing the banned cell reappear on a critical-path report it
should have been excluded from, not by a test.

| | G5 as first published (contaminated) | G5 corrected (artifact-free) |
|---|---|---|
| P1 | -2.471 | **-1.555** |
| P2 | **+0.829** | **+0.485** |
| P3 | -2.051 | **-2.102** |
| P6 | -3.400 | **-1.615** |
| baseline clk_a (v1 SDC) | -25.287 | **-20.667** |

The baseline carried **4.62 ns** of pure artifact. Magnitudes moved 40 to
50%. **The qualitative conclusion is unchanged**: P2 is the only proposal
that improves the touched path group, and the other three proven transforms
still make it worse. The registered primary bar is still met, by a smaller
margin.

A failed fix that silently does nothing is worse than no fix, because it is
reported as done. The lesson taken: a flag-generating function needs a test
asserting it returns a non-empty result, which is now how it is verified.
