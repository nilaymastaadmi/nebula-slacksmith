# G7, the CDC gate: results and scoring

Registered in `PREREGISTRATION.md` before `tools/cdc_check.py` existed. Two
amendments, both dated, both before the result they could have affected.

## Scorecard: 3 confirmed, 1 wrong, 2 right for the wrong reason

| # | registered | outcome |
|---|---|---|
| **C1** | depth check flags CDC-1/gate.v, passes gold.v | **CONFIRMED** |
| **C2** | Hamming refutes CDC-2/gate.v with a counterexample, proves gold.v | **CONFIRMED** |
| **C3** | all 6 `async_fifo` gray-pointer crossings prove Hamming safe | **CONFIRMED**, by a stronger route |
| **C4** | zero `DEPTH_n` violations on `bench_top` | **WRONG. There are 6.** |
| **C5** | 1 to 5 `UNCLASSIFIED` on `bench_top` | count right (2), **reason wrong** |
| **C6** | at least one false positive | direction right, **mechanism wrong** |

## What the gate does that nothing else here could

`REPORT.md` §10 said, before this existed: *"Neither CDC case is detected as a
CDC defect by anything here, our own checker included."* Both now are.

| case | every checker in §7.4 | G7 |
|---|---|---|
| CDC-1 gold | `cec`/`dsec` cannot build a miter at all | SAFE, depth 2 |
| CDC-1 gate | reads as a latency change, not a defect | **DEPTH_1** |
| CDC-2 gold | correctly ACCEPT | SAFE, proven to depth 16 |
| CDC-2 gate | correctly ACCEPT, **and the bug is still there** | **REFUTED** |

CDC-2 is the sharper one. Every functional checker is *right*: the pair is
equivalent, because moving a combinational encoder across a register does not
change the function. The counterexample G7 returns is not about function:

    step  bin   prev  diff  popcount
       4  0001  0000  0001      1
       5  0010  0001  0011      2     <-- ASSERT FAILS HERE

The bus that physically crosses goes `0001` to `0010`, two bits in one cycle.
A receiver in another domain sampling mid-transition can latch `0000` or
`0011`, neither the old value nor the new one.

**The gate checks the property, not the encoding.** Gold's crossing net is a
combinational wire, not a register, and it passes because its value changes one
bit at a time, not because anything pattern-matched a gray encoder. A design
that achieves the property another way passes; one that gray-codes on the wrong
side of the boundary fails.

## C3, confirmed by a better route than registered

The registration said all 6 `async_fifo` gray-pointer crossings in `bench_top`
would prove safe. The structural pass finds exactly those 6, all correctly
identified as `u_fifo_{a2b,c2d,e2a}.{w,r}gray_r`.

They were **not** checked as 6 flattened instances. After `flatten` the
pointers carry hierarchical names like `u_fifo_a2b.rgray_r`, which cannot be
written as identifiers by an assertion injected into a module. Instead the
property was proven on `async_fifo` itself, both pointers, to depth 16, each in
its own domain (`wgray_r`/`wclk`/`wrst_n` and `rgray_r`/`rclk`/`rrst_n`).

That is the stronger claim: it holds for every instantiation, the three in
`bench_top` and any future one, rather than for six particular copies.

## C4 is wrong, and the reason is worth more than the prediction

Six `DEPTH_1` findings on `bench_top`, where zero were registered. All six have
one shape:

| source | destination | what it is |
|---|---|---|
| `clk_a` | `clk_a_div2` | a clock and its own /2 |
| `clk_b_div3` | `clk_b` | a clock and its own /3 |
| `clk_c_div4` | `clk_c` | a clock and its own /4 |
| `clk_d_div5` | `clk_d` | a clock and its own /5 |
| `clk_e_div2` | `clk_e` | a clock and its own /2 |

**Every one is a crossing between a clock and its own in-RTL divided version.**
Those are synchronously related. No synchronizer is required, none is present,
and the design is correct. The gate keys on clock *nets* and has no notion of
clock *relationships*, so it flags all five divider pairs plus one more.

This is a real limitation with a real name: commercial CDC tools require clock
group declarations precisely so a derived clock is not treated as a foreign
domain. G7 has no such input. **Six of its sixteen findings on a correct design
are noise**, and a user would have to know the design to know that.

The two genuine asynchronous control crossings, `b2c_ctrl` and `d2e_ctrl`,
cross real clock-group boundaries and are correctly **SAFE at depth 3**.

## C5 and C6: right answers, wrong reasons, recorded as such

**C5** registered 1 to 5 `UNCLASSIFIED` crossings, "most likely around the
`clkdiv`-generated clocks and reset synchronization". There are **2**, so the
count is inside the registered band. The reason is not the one registered:
both are wide buses, `u_domain_a.ctrl_r` at 73 bits and
`u_domain_e.addr_r`/`wdata_r` at 512 bits, that hit the backward-traversal
bound. Nothing to do with `clkdiv`.

**C6** registered at least one false positive, "safe because of a handshake
protocol rather than its encoding". There are six false positives and **none of
them is a handshake**. They are the derived-clock findings above. The
prediction that the gate would produce false positives was right; the mechanism
named was wrong.

Both are scored as written. A prediction that lands on the number for a reason
that turns out to be false is not a hit, and calling it one would make the
whole registration decorative.

## Six tool bugs, all mine, and one theme

1. **A wrapper reaching in as `dut.<net>` does not work.** Yosys treats the
   hierarchical reference as an implicitly declared wire, and `.*` needs every
   port redeclared. Replaced by instrumenting the source, which is what
   commercial CDC tools do; the instrumented file is written into the work
   directory so the property that ran can be read rather than trusted.
2. **A literal backspace byte, `0x08`, in the module-name regex** instead of
   the two characters `\b`, written by a shell heredoc that interpreted the
   escape. Every Hamming check returned "could not find module to instrument".
3. **The arbitrary initial state.** The first working Hamming run refuted
   *both* gold and gate at step 0, because a BMC engine starts anywhere and the
   comparison register began as garbage. Same trap `experiments/fsm_reencode`
   hit with PDR a month earlier, same fix: a boot counter that holds reset for
   two cycles and arms the assertion only after the design settles.
4. **No `flatten`, so the gate saw 0 flops in an 8,092-bit design** and printed
   `crossings: 0`, exit 0. A clean sheet on a design it could not see.
5. **A global `--ham-clock` applied to every crossing in a run.** On
   `async_fifo` it checked `rgray_r` against `wclk` and returned **REFUTED on a
   correct design**. Clock and reset, including reset polarity, are now derived
   per crossing from the flop that drives it.
6. **A flattened alias used as an identifier.** After `flatten`, `wclk` is also
   named `u_sync_r2w.clk`; the model kept whichever it saw first and injected
   `posedge u_sync_r2w.clk` into `async_fifo`, where that is not an identifier.
   The property silently meant nothing and returned REFUTED. The model now
   prefers the name written at this level, and the gate refuses to instrument
   with a dotted name at all.

**Bugs 4, 5 and 6 share a signature: the gate produced a confident wrong
verdict rather than an error.** Bug 4 said a design was clean; bugs 5 and 6
said a correct design was broken. None of them raised anything. That is the
same failure this project built SlackBench to measure, found in the project's
own new checker, and two of the three were caught only because gold was run
through every check alongside gate. **A checker exercised only on the case
expected to fail is indistinguishable from one that always fails.**

Bug 4 was caught in one glance because the registration already said, in
advance: *"A CDC checker that reports a clean sheet on a 55K-cell design with
five domains is far more likely to be broken than to be right."* Writing that
down before the run is what made a zero legible as a bug instead of a result.

## Limits, restated with what is now known

- **No clock-group input**, which is the direct cause of six false positives.
  This is the first thing to fix and it is not a small fix: it needs a
  constraint format and a way to state that one clock is derived from another.
- **The traversal bound is a real ceiling.** Two crossings on wide buses were
  not classified, and `UNCLASSIFIED` is reported separately rather than folded
  into either answer.
- **Bounded, not unbounded.** Hamming safety is discharged by BMC to depth 16.
  Nothing here proves the property holds forever, only that no counterexample
  exists within 16 cycles.
- **Structural and temporal, not physical.** Nothing here says anything about
  metastability probability or MTBF, and depth 2 is the convention this design
  uses rather than a proof that 2 is enough.
- **One design plus two purpose-built cases.** These are outcomes, not rates.
