# What the gate rejected, and why. Input to batch 3, arm B only.

You are proposing typed RTL transforms for a path that three formally proven
transforms have already failed to improve. Below is every rejection this
project's gate has produced, with the mechanism. Each one is a real result
from a real solver on this design; none is hypothetical.

## Refuted at the formal gate (G4)

### P4, `mux_priority_to_parallel` on `rv32i_core`, declared k=0

Rewrote the ALU `case` as one-hot decode of `funct3` OR-ing masked arms, and
folded the two shift arms into a single conditional:

    wire [31:0] r_shr = alt ? ($signed(a) >>> shamt) : (a >> shamt);

Parses, elaborates, passes preconditions, saves 208 cells, **and is wrong**.
A conditional operator's result signedness is derived from *both* branches.
Pairing a signed branch with an unsigned one makes the whole expression
unsigned, that context propagates back into the operands, and `>>>`
silently degrades to a logical shift. SRA/SRAI is wrong for every negative
operand.

EQY counterexample, 46 seconds, partition `alu_out`:
`a = ae19f605`, `shamt = 7`, `retire_insn = 40005073` (SRAI),
gold `alu_out = ff5c33ec` (arithmetic), gate gives `015c33ec` (logical).

Two simulation testbenches, including the design's own shipped firmware,
**missed this**. `rtl/rv32i_core.v` carries a six-line comment warning about
exactly this, ten lines above the code P4 changed. The proposer had that file
as input and made the documented mistake anyway.

### P5, `pipeline_cut_rigid` on `rv32i_core`, declared k=1

Registered `alu_out` one cycle later. Refuted in 1 second, failing on
`eq_dmem_addr`. `alu_out` feeds the register file and the PC, so delaying it
does not shift the output stream by one cycle, it changes the machine. A
feedback path cannot be given a fixed-offset obligation.

### A3, `read_port_register` on `aes_key_mem`, declared k=1

Registered the `round_key` read port. Refuted in 0 seconds on `eq_ready`.
It delayed *one* output; `ready` and `sboxw` still responded in the same
cycle. A declared k=1 rigid transform is a claim about the whole interface,
not about one port.

## Rejected at precondition (G3)

### A6, `key_mem_parity_split` on `aes_key_mem`, declared k=0

Split a 15-entry array into two 8-entry arrays. That is 16 words of storage
where the design had 15. Declared k=0, flop count moved by +256, rejected
before any solver ran. A transform that silently changes the amount of state
would otherwise have been handed a combinational obligation, which is the
wrong obligation.

## Not a defect, but do not learn the wrong lesson from it

### A2, `decode_duplication` on `aes_key_mem`, declared k=0

Reported UNRESOLVED. Splitting the key array into four 32-bit arrays is
equivalent by inspection; the equivalence checker ran out of depth on one
partition and found no counterexample. Simulation had gold and gate agreeing
on all 16 values of `round`. Treat A2 as unknown, not as wrong.

## Proven correct and still reverted (G5), which is the harder lesson

All measured on the exact target you are given: post-buffering `clk_a` under
SDC v3, baseline **-1.716 ns**.

| proposal | transform | G4 | clk_a after | change |
|---|---|---|---|---|
| P1 | `operator_sharing_addsub` | PROVEN | -2.026 | **worse** by 0.310 |
| P2 | `operator_sharing_shifter` | PROVEN | -2.201 | **worse** by 0.485 |
| P3 | `operator_sharing_comparator` | PROVEN | -2.02 | **worse** by 0.304 |

All three share ALU operators to save area. All three are correct. All three
make the target path slower. P2 is the one transform that *improved* this
group in the **unbuffered** context (+0.485); in the buffered context the
same transform is -0.485. **Operator sharing in the ALU cone does not help
this path once the physical lever has run.**

## What the classified report is telling you

The path is **DEPTH_DOMINATED, fanout share 0.000, 17.13 ns over 33 cells**.
No single net is the problem; the delay is spread across a long chain. The
single largest cell (6.762 ns, `and2_1`) is in **`rv32_load`**, the wrapper,
not in the core. The path crosses the wrapper's async-read data memory and
the core's ALU cone. Batches 1 and 2 never touched the wrapper.

## What is being measured about you

Beyond correctness and timing, every proposal in this batch is audited by
reading for the P4 defect class: a signed and an unsigned expression as the
two branches of one conditional, or any construct whose result signedness is
derived from mixed operands. Avoiding it is the point.
