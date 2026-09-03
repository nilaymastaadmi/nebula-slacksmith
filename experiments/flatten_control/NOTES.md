# Flatten before ABC: results

Registered in `PREREGISTRATION.md` (commit `f523c44`) before any arm was
synthesized. Run 2026-09-03, `run.py`, 5 arms, 5 min 48 s wall, log in
`results/run.log`, per-arm reports with OpenSTA's fanout column in
`results/`. Scored by `score.py`.

## The table

| arm | flatten | ABC | cells | clk_a | clk_b | clk_e |
|---|---|---|---|---|---|---|
| A | no | default | 28,844 | −13.167 | −18.957 | −25.957 |
| B | no | buffer-only | 30,264 | +1.75 | +5.556 | −1.444 |
| C | **yes** | default | 25,920 | **+9.279** | −4.065 | −15.762 |
| D | **yes** | buffer-only | 26,958 | **+10.362** | **+5.665** | **−0.613** |
| E | **yes** | buffer + size | 26,958 | **+11.158** | +5.665 | **−0.319** |

A and B reproduce the closed-loop record to the decimal (prediction 19).

Worst path after each arm, from the fanout column:

| arm | clk_a top cell | clk_e top cell |
|---|---|---|
| B | and2_2, 3.747 ns, **387 loads** | a21oi_1, 1.952 ns, **59 loads** |
| C | nor3b_1, 1.824 ns, 32 loads | nor4_1, 17.567 ns, 256 loads |
| D | dlygate4sd3_1, 0.619 ns, 5 loads (max on path 22) | dfrtp_1, 1.897 ns, **136 loads** |
| E | dfrtp_1, 0.502 ns, 22 loads | dfrtp_1, 1.888 ns, **136 loads** |

## Scored

- **P19 correct.** A and B reproduce exactly.
- **P20 correct.** D clk_e −0.613 against B's −1.444.
- **P21 correct.** D clk_a +10.362 against B's +1.75.
- **P22 wrong.** D's clk_e path carries a flop output with 136 loads. The
  387-load and 59-load nets are gone, but `buffer -N 16` left a flop's Q net
  untouched: flops are mapped by `dfflibmap` before `abc` runs, so ABC sees
  the Q net as a combinational input, and its `buffer` command does not
  buffer combinational inputs by default. That is the next lever, registered
  as amendment 1 below rather than run on the spot.
- **P23 wrong.** clk_e does not close: −0.613 under D, −0.319 under E.
- **P24 wrong, and by a lot.** Flattening alone (C, no buffering) moves
  clk_a by **+22.446 ns**, clk_b by +14.892 and clk_e by +10.195, and drops
  the cell count from 28,844 to 25,920. The registered mechanism was
  "buffering across the boundary"; the measured one is bigger: across the
  boundary ABC also sees that `rv32_load` ties 20 of `u_core`'s instruction
  bits to one net and 6 to constants, and collapses the decode logic that
  hierarchical synthesis had to keep. The 387-load net does not get
  buffered under C; it stops existing (max fanout on the C clk_a path is
  32). On this benchmark the hierarchical flow was the largest single
  source of the violations we spent two weeks routing around.
- **P25 wrong.** E's clk_a is above D's (+11.158 against +10.362), and E is
  better on clk_e too (−0.319 against −0.613). The "dnsize gives back
  clk_a" mechanism from closed-loop run 3 was one observation in the
  hierarchical flow and does not transfer to the flat one. It is withdrawn
  as a general statement; run 3's numbers stand as run 3's numbers.

3 of 7 correct. The direction of the primary hypothesis held (flat buffering
beats hierarchical buffering on both residual groups, by 8.6 and 0.8 ns);
the mechanism registered for it was too narrow, and both secondary
hypotheses (closure, and sizing hurting clk_a) were wrong.

## What this changes, stated plainly

1. **Every v3 physical number reported before this experiment is a
   hierarchical-flow number** and is labelled so in the report. They are
   not wrong; they are numbers for a flow that could not see across module
   ports.
2. The v3 targets were set at 0.9x the hierarchical buffered requirement
   (`sdc/make_v3.py`). Under the flat flow two of three groups clear them
   by 5 to 11 ns, and the one that does not (clk_e) is 0.3 ns short with a
   136-load flop output on its path. The benchmark under SDC v3 is, in the
   flat flow, a one-net problem.
3. The closed loop should run flat. `--flatten` is added to
   `tools/slacksmith.py` (default off, so every earlier log reproduces) and
   run 6 is registered in `experiments/closed_loop/PREREGISTRATION_flat.md`.
   The RTL lever's module filter uses module ownership that a flat netlist
   does not carry; on a flat netlist the RTL lever cannot select a
   proposal, and that is stated in the registration rather than patched
   around before it matters.

## Amendment 1, 2026-09-03, after arms A to E: arms F and G, buffer the flop outputs

Written after reading the table above and before arm F or G is
synthesized. ABC's `buffer` takes `-p`, "toggle buffering primary inputs"
(`yosys-abc -c "buffer -h"`; a first draft of this amendment named `-c`,
which is the wire-load toggle, corrected before anything ran). Flop Q nets
are primary inputs from ABC's point of view, so `-p` is the switch that
reaches the 136-load net. Arm F = flat, `buffer -N 16 -p`. Arm G = flat,
`buffer -N 16 -p; upsize; dnsize`.

Prediction 26: F's clk_e is above D's −0.613 and no flop output with more
than 32 loads is on F's worst clk_e path. Medium. Prediction 27: F does not
close clk_e. Low-medium; registered so that a close is a scored surprise
and not a claim written after the fact. Prediction 28: G's clk_e is above
F's, as E's was above D's. Medium.
