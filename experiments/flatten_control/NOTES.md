# Flatten before ABC: results

Registered in `PREREGISTRATION.md` (commit `4873dc7`) before any arm was
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

## Amendment 1 outcome: arms F and G

F is byte-identical to D and G to E, all three clocks, to the decimal
(F: +10.362 / +5.665 / −0.613; G: +11.158 / +5.665 / −0.319).
`buffer -N 16 -p` changed nothing: the 136-load flop output is still the
top cell of the clk_e path at 1.897 ns. In this flow ABC's buffer command
does not reach flop outputs even when told to buffer primary inputs, so the
switch that was supposed to be the next lever is a measured no-op. **P26
wrong, P27 correct, P28 correct** only because G equals E. Flatten control
total: 5 of 10 predictions correct.

The tool that does buffer that net is OpenROAD's `repair_design` (+55.805
on the hierarchical netlist, `experiments/openroad_repair/`); running it on
the flat netlist is the next physical step and is not done here.

## Runs 6 and 7: the closed loop on the flat flow

`experiments/closed_loop/PREREGISTRATION_flat.md`, logs `run_v3_flat.jsonl`
and `run_v3_flatpi.jsonl`, scorer `score_flat.py`.

    it1  MEASURE   clk_a=9.279    clk_b=-4.065   clk_e=-15.762   (= arm C)
    it1  CLASSIFY  clk_e: FANOUT_DOMINATED (0.9547) -> physical buffer (provisional)
    it2  MEASURE   clk_a=10.362   clk_b=5.665    clk_e=-0.613    (= arm D)  total -19.827 -> -0.613, CONFIRM buffer
    it2  CLASSIFY  clk_e: MIXED (0.3221) -> physical size (provisional)
    it3  MEASURE   clk_a=11.158   clk_b=5.665    clk_e=-0.319    (= arm E)  total -0.613 -> -0.319, CONFIRM size
    it3  CLASSIFY  clk_e: MIXED (0.3374) -> physical
    it3  STOP      physical_exhausted

Run 6: 3 iterations, 125 s, **P29 to P32 correct**; the sizing step is
confirmed here where run 5 reverted it, because on the flat netlist it
improves the total. Run 7 (`--buffer-pi`): identical measurement for
measurement, 124 s, **P33 wrong**. On the flat flow the loop closes two of
three groups by 5.665 and 11.158 ns and stops honestly on the third with
one 136-load flop output left, which is out of ABC's reach.
