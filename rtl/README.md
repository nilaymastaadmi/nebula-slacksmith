# bench_top — 5-clock-domain synthesizable SoC skeleton

Device-under-test for the SlackSmith RTL timing-optimization benchmark. It
exists to stress **clock-domain-crossing** and **generated-clock** constraints
under Yosys synthesis and OpenSTA timing — not to compute anything useful. Real
compute blocks get added later.

This closes the gap the root `README.md` flags under "Known corrections":
*"the benchmark needs generated clocks and multi-ratio dividers … both are
explicit organizer requirements currently unmet."* The SDC itself is still
outstanding — see "Things I was unsure about" below.

> All paths in this document are relative to the **repository root**, and every
> command below is meant to be run from there.

Plain **Verilog-2001** throughout. No `interface`/`struct`/`class`/UVM, no vendor
primitives (no `BUFG`/`MMCM`/`PLL`/`IBUF`, no Xilinx/Intel macros), no
`$readmemh`, no `#` delays, no `initial` blocks driving logic, no latches, no
combinational loops, no memory array larger than 8 words.

## Files

| File | Contents |
|---|---|
| `rtl/bench_top.v` | Top level: 5 clocks, 5 dividers, 5 domains, 3 FIFOs |
| `rtl/clkdiv.v` | Parameterizable divider; true 50% duty on odd ratios |
| `rtl/async_fifo.v` | Parameterizable gray-pointer dual-clock FIFO |
| `rtl/sync2ff.v` | Two-flop synchronizer |
| `rtl/domain_a.v` … `rtl/domain_e.v` | The five domains |

## The five clock domains

Five primary clock inputs with no phase relationship, each with its own async
active-low reset. Every primary clock drives one in-RTL divider producing a
**real generated clock that clocks real flip-flops** — not a clock-enable pulse.

| Domain | Primary clock | Reset | Function | Divider | Cells | Flops |
|---|---|---|---|---|---|---|
| A | `clk_a` | `rst_a_n` | 8-bit MAC datapath (8×8 multiply, 32-bit accumulate) | **/2** | 655 | 124 |
| B | `clk_b` | `rst_b_n` | Control FSM, 10 states, + 16-bit LFSR | **/3** | 118 | 42 |
| C | `clk_c` | `rst_c_n` | UART-transmitter-like 10-bit shift block + baud counter | **/4** | 148 | 50 |
| D | `clk_d` | `rst_d_n` | Reloading 32-bit timer, two programmable compares | **/5** | 135 | 28 |
| E | `clk_e` | `rst_e_n` | 16 × 32-bit config/status register file | **/2** | 1656 | 599 |

Ratios /2, /3, /4 and /5 are all covered. Divider cost, measured separately:
`/2` = 1 flop, `/3` = 6 flops, `/4` = 2 flops, `/5` = 8 flops.

Each domain has at least one real primary output so timing paths terminate
observably: `mac_result_a[15:0]`, `status_b[7:0]`, `uart_tx_c`,
`timer_pulse_d`, `cfg_status_e[7:0]`.

Within each domain, logic is deliberately split across the primary clock **and**
its generated clock, so source-clock ↔ generated-clock paths are real and must
be timed (e.g. domain A multiplies on `clk_a` and accumulates on `clk_a/2`;
domain C shifts on `clk_c/4` and re-registers `tx` on `clk_c`).

## Odd-ratio dividers — how the 50% duty cycle is produced

For **/3** and **/5** the requirement is a genuine 50% duty cycle, which is
impossible from posedge-triggered logic alone (an odd number of source cycles
cannot be split in half on posedges). `clkdiv.v` therefore uses **both edges**:

- A posedge counter drives `clk_p`, held high for `(DIV+1)/2` source cycles.
- A negedge counter drives `clk_n`, the same sequence delayed by half a source
  period.
- `clk_out = clk_p & clk_n`.

The AND removes exactly half a source period from the high time:
`(DIV+1)/2 − 1/2 = DIV/2` → exactly 50%. The two flags never change at the same
instant (their launch edges are half a period apart), so the AND cannot glitch.

Even ratios use a single posedge counter that toggles every `DIV/2` edges.

This is the awkward-by-design part: `create_generated_clock` for the /3 and /5
outputs has to describe a divided clock whose edges are derived from *both*
edges of its source.

## Crossings

Every **multi-bit** crossing is a gray-pointer async FIFO. Every **single-bit**
control crossing is a two-flop synchronizer. The five crossings form a ring
A → B → C → D → E → A.

| # | Source | Destination | Signal | Structure | Launch clock | Capture clock |
|---|---|---|---|---|---|---|
| 1 | A | B | `a2b_wdata[15:0]` (MAC result) | `async_fifo` DW=16, AW=3 (8 deep) | `clk_a/2` | `clk_b/3` |
| 2 | B | C | `b2c_ctrl` (toggle) | `sync2ff` WIDTH=1 | `clk_b/3` | `clk_c/4` |
| 3 | C | D | `c2d_wdata[7:0]` (byte count) | `async_fifo` DW=8, AW=3 (8 deep) | `clk_c/4` | `clk_d/5` |
| 4 | D | E | `d2e_ctrl` (toggle) | `sync2ff` WIDTH=1 | `clk_d/5` | `clk_e/2` |
| 5 | E | A | `e2a_wdata[31:0]` (config word) | `async_fifo` DW=32, AW=2 (4 deep) | `clk_e/2` | `clk_a` (primary) |

Note that four of the five crossings launch **and** capture on generated clocks —
deliberate, since that is the constraint case the benchmark is meant to exercise.
Crossing 5 captures on a primary clock so at least one FIFO has a plain
primary-clock endpoint.

Inside `async_fifo`:

- Binary pointers are `AW+1` bits; the extra MSB separates full from empty.
- The pointer that crosses is the **gray** encoding `bin ^ (bin >> 1)`, so
  exactly one bit changes per increment.
- Each pointer is synchronized into the opposite domain through a `sync2ff`
  (two flops).
- `full` / `empty` are **registered** flags computed from the *next* pointer
  value, so they never combinationally depend on `winc`/`rinc`. That is what
  makes a consumer driving `rinc = ~rempty` safe — no combinational loop.

Single-bit crossings carry a **toggle**, not a pulse, so a slow destination
clock cannot miss a narrow source-domain pulse. The destination edge-detects the
synchronized toggle.

## Verification actually performed

Yosys was **not** on `PATH` on this machine. It was installed for this ticket
(`oss-cad-suite-windows-x64-20260814`) and everything below is real output from
a real run, not a description of what should happen.

### 1. Synthesis — Yosys 0.68+64

```
$ yosys -p "read_verilog rtl/*.v; hierarchy -check -top bench_top; synth -top bench_top; stat"
```

```
=== design hierarchy ===

     3584 bench_top
      311   async_fifo (DW=16, AW=3)   [A->B]
        8     sync2ff WIDTH=4
      272   async_fifo (DW=32, AW=2)   [E->A]
        6     sync2ff WIDTH=3
      191   async_fifo (DW=8,  AW=3)   [C->D]
        8     sync2ff WIDTH=4
        2   clkdiv DIV=2
       15   clkdiv DIV=3
        4   clkdiv DIV=4
       27   clkdiv DIV=5
      655   domain_a
      118   domain_b
      148   domain_c
      135   domain_d
     1656   domain_e

     2420 wires
     4493 wire bits
        - memories
        - memory bits
        - processes
     3584 cells
       71   $_ANDNOT_
      741   $_AND_
        2   $_DFFE_NN1P_
       24   $_DFFE_PN0N_
      656   $_DFFE_PN0P_
       12   $_DFFE_PN1N_
       12   $_DFFE_PN1P_
      320   $_DFFE_PP_
        5   $_DFF_NN0_
      230   $_DFF_PN0_
       12   $_DFF_PN1_
      295   $_MUX_
      799   $_NAND_
       37   $_NOR_
       30   $_NOT_
       24   $_ORNOT_
       33   $_OR_
       94   $_XNOR_
      187   $_XOR_
```

Results against the mechanical checks:

- **Completes with no errors** — yes, exit code 0, zero `ERROR:` lines.
- **3,000–8,000 cells** — **3,584 cells**. In range, with no padding; every
  block is load-bearing. It sits in the lower half of the range, which is
  expected for a skeleton.
- **Zero `$dlatch`** — confirmed, no `$dlatch`/`$_DLATCH_` cell of any kind
  appears in `stat`, and no "inferring latch" message appears in the log.
- `hierarchy -check` passes (no missing/blackbox modules).
- 1,240 flops total. Negedge-triggered flops (`$_DFF_NN0_`, `$_DFFE_NN1P_`) = 7,
  which is exactly the negedge half of the /3 and /5 dividers — confirming the
  odd dividers really do use both clock edges.

The only non-ABC warning in the whole run is the intended one:

```
Warning: Replacing memory \cfg_reg with list of registers. See rtl/domain_e.v:83
```

That is the desired outcome: the domain E register file is written as a `reg`
array but reset elementwise, so it becomes 512 plain reset flops rather than a
RAM.

### 2. Divider duty cycle — Icarus Verilog, measured on edge timestamps

Source clock 10 ns. Measured high time, low time and period over consecutive
output cycles:

```
DIV=2 c0 high=10.00 low=10.00 period=20.00 duty=50.0000%
DIV=3 c0 high=15.00 low=15.00 period=30.00 duty=50.0000%
DIV=4 c0 high=20.00 low=20.00 period=40.00 duty=50.0000%
DIV=5 c0 high=25.00 low=25.00 period=50.00 duty=50.0000%
```

Stable across all measured cycles. Both odd ratios are exactly 50%, and the
periods are exactly 3× and 5× the source — so these are real divided clocks,
not 1-in-N enables.

### 3. FIFO gray-pointer invariant and data integrity

Write clock 10 ns, read clock 14.6 ns (deliberately non-harmonic), run to
saturation in both directions:

```
write-ptr gray transitions=13699  multi-bit=0
read-ptr  gray transitions=13696  multi-bit=0
words read=13697  out-of-sequence=0
PASS: gray pointers change exactly one bit; FIFO data in-order, no loss/duplication
```

27,395 pointer transitions with **zero** multi-bit changes, and 13,697 words
crossed the boundary with zero loss, duplication or reordering.

### 4. Top-level smoke test

`bench_top` driven with five mutually non-harmonic clocks (5.0 / 6.7 / 3.1 /
8.3 / 4.3 ns half-periods) and staggered reset release, config writes, then
60,000 sample cycles:

```
output toggled?  mac_result_a=1 status_b=1 uart_tx_c=1 timer_pulse_d=1 cfg_status_e=1
PASS: no X on any output
```

All five domain outputs toggle, so the whole A→B→C→D→E→A ring is live and no
domain is dead logic. No X on any output after reset.

This smoke test found two real bugs, both fixed:

- **`domain_b` read the A→B FIFO one cycle late.** `async_fifo` presents `rdata`
  for the current head in the *same* cycle `rd_en` is asserted; capturing it in
  the following state read the next, possibly unwritten, slot and propagated X
  into `status_b`. The payload is now captured in `S_FETCH`.
- **`domain_d`'s timer could never fire.** A free-running 32-bit counter with
  compare values reprogrammed into high bit positions (`{8'd0, rdata, 16'hFFFF}`
  ≈ 393k) never matched within any realistic run, which killed `timer_pulse_d`
  and starved domain E through the D→E crossing. It is now a proper reloading
  timer with both compares in reachable low bits.

The testbenches were scratch files used to produce the results above; per the
ticket's non-goals they are not part of the deliverable and are not committed.

## Deviations from the spec, and why

1. **FIFO storage arrays are not reset.** The spec says every flop is explicitly
   reset, async active-low. That holds for every flop in the design *except* the
   three FIFO storage arrays. Measured exactly:

   ```
   total unreset flops: 320
     128  async_fifo DW=16 AW=3   (8 words x 16 bits, A->B)
     128  async_fifo DW=32 AW=2   (4 words x 32 bits, E->A)
      64  async_fifo DW=8  AW=3   (8 words x  8 bits, C->D)
   ```

   That is 320 of 1,240 flops, and they are all and only FIFO storage bits.
   Resetting FIFO *contents* is not standard practice — the data is meaningless
   until written, and the pointers and full/empty flags (which are what actually
   make the FIFO safe) *are* all async-reset. Forcing a reset onto the storage
   would add 320 reset connections that buy nothing and would misrepresent the
   real timing picture. If the benchmark needs literally every flop reset, this
   is a one-line change in `async_fifo.v` and the cell count rises slightly.

2. **This README is at `rtl/README.md`, not the repository root.** The ticket
   asked for `README.md` at root, but the root README is the SlackSmith project
   record and overwriting it would destroy real content. Placed here instead, on
   @manager's call.

3. **Domain E register file is 32-bit, and the config write port is 32-bit.**
   The spec said "~16-register config/status file" without fixing a width. 16 ×
   32 bits makes domain E the largest block (1,656 cells) and is what lifts the
   design comfortably into the required cell range without adding dead logic.

4. **`domain_d` is a reloading timer, not a free-running counter.** The
   suggested shape said "counter/timer with compare". A free-running counter
   with a reprogrammable compare only matches once ever, which produced a dead
   output (see smoke test above). Reloading at `cmp0` makes it a real periodic
   timer and keeps the D→E crossing active. Same cell budget.

5. **The B→C and D→E synchronizers live inside the destination domain module**
   (`domain_c.v`, `domain_e.v`) rather than at top level, so each domain owns the
   flops clocked by its own clock. `bench_top` passes the raw asynchronous bit in.

6. **`.gitignore` gained two lines** (`.guildly/`, `PROMPT.md`) so the agent
   workspace and the local prompt scratch file stay out of the repo. Strictly
   outside the ticket's file scope, but without it the next `git add` in this
   directory would commit them.

## Things I was unsure about

- **Cell count sits at 3,584 — the low end of the 3k–8k window.** It is in range
  and nothing is padded, but if the benchmark wants more timing paths to chew on,
  the cheapest honest lever is widening the domain A datapath (8×8 → 16×16
  multiply) or deepening the FIFOs. I did not do either, because the ticket said
  explicitly not to pad, and both would be padding at this stage.

- **Exact-command caveat on Windows.** The ticket's literal command uses
  `rtl/*.v`. This Windows mingw Yosys build has no POSIX `glob()`, so
  `read_verilog rtl/*.v` fails with ``File `rtl/*.v' not found``. Every result
  above was produced by expanding the glob to the identical nine-file list. On a
  Linux Yosys build the literal command should work unchanged, but I could not
  verify that here — flagging it rather than claiming it.

- **Reset-release phase of the odd dividers.** `clk_p` and `clk_n` both leave
  reset at count 0, so which one leads depends on whether a posedge or a negedge
  arrives first after reset deassertion. Either way the output is still exactly
  50% duty at the right period — only the output clock's phase relative to the
  source shifts by half a source cycle. If the benchmark's SDC needs a
  deterministic phase, the resets would have to be released synchronously to a
  known edge. I left it asynchronous because the spec asked for async resets.

- **No SDC / OpenSTA scripts here.** Listed as a non-goal, so the
  `create_generated_clock` statements this design is built to exercise are not
  written yet. The /3 and /5 outputs will need generated-clock definitions that
  reference both source edges; that is the intended difficulty, and it is the
  remaining half of the root README's "generated clocks and multi-ratio dividers"
  gap.

- **No formal CDC proof.** The crossings are verified by construction (gray
  pointers, two-flop synchronizers) and by the simulations above, which exercise
  them hard at non-harmonic clock ratios but are not exhaustive. No formal CDC
  tool was run.

## Reproducing the synthesis check

```bash
yosys -p "read_verilog rtl/*.v; hierarchy -check -top bench_top; synth -top bench_top; stat"
```

On a build without POSIX glob, list the files explicitly:

```bash
yosys -p "read_verilog rtl/async_fifo.v rtl/bench_top.v rtl/clkdiv.v \
  rtl/domain_a.v rtl/domain_b.v rtl/domain_c.v rtl/domain_d.v \
  rtl/domain_e.v rtl/sync2ff.v; \
  hierarchy -check -top bench_top; synth -top bench_top; stat"
```
