# repair_design on the flat netlist

Registered in `PREREGISTRATION.md` (commit `b621c73`) before OpenROAD saw a
flat netlist. Run 2026-09-03, `run.sh`, logs and repaired netlists in
`results/`, scored by `score.py`.

**These numbers carry placement parasitics.** The flatten-control and
closed-loop numbers do not. Only before-versus-after within one arm below
is a valid comparison, and no sentence here crosses that line.

## OR-C, flat netlist, no ABC buffering

| group | before repair | after repair | delta |
|---|---|---|---|
| clk_a | +7.539 | **+10.087** | +2.548 |
| clk_b | −28.855 | **+5.489** | +34.344 |
| clk_e | −41.943 | **−2.243** | +39.700 |

Area 263,069 to 312,337 u^2, **+18.7%**.

## OR-E, flat netlist, ABC buffer + upsize + dnsize already applied

| group | before repair | after repair | delta |
|---|---|---|---|
| clk_a | +10.443 | +10.175 | **−0.268** |
| clk_b | +0.980 | +5.225 | +4.245 |
| clk_e | −5.465 | **−0.952** | +4.513 |

Area 267,879 to 325,919 u^2, +21.7%.

## Scored

- **P34 correct.** OR-C improves all three groups.
- **P35 wrong.** After repair, the same `a21o_4` cell driving **65 loads**
  sits on all three worst paths. `repair_design` repairs against the
  library's own max-fanout and max-capacitance limits, and the frozen SDC
  sets no `set_max_fanout`, so 65 loads is not a violation for it to fix.
  The mechanism claim ("the tool that reaches flop outputs is this one")
  holds for the 136-load flop output, which is gone; the claim as
  registered, that nothing above 32 remains, does not.
- **P36 wrong.** clk_e ends at −2.243, still violating. It closed all three
  under SDC v2; v3 is tighter and it does not.
- **P37 correct.** +18.7% against the hierarchical run's +20.2%.
- **P38 correct.** OR-E's post-repair clk_e (−0.952) beats OR-C's
  (−2.243), so ABC's buffering and sizing still help in a flow that has
  `repair_design`. They are not redundant.

3 of 5. Across the three experiments that share this numbering (flatten
control 19 to 28, flat loop 29 to 33, this one 34 to 38): 12 correct of 20.
The transfer study and the earlier closed-loop registrations use their own
numbering and are scored in their own files.

## What this says

**The two physical levers compose.** The best result on this benchmark is
ABC buffering and sizing on a flat netlist, then `repair_design`: clk_a
+10.175, clk_b +5.225, clk_e −0.952 with parasitics. Doing only one of them
is worse on the group that binds.

**The residual is one net, again.** Three separate levers have now each
left the clk_e group violating by less than a nanosecond with a single
high-fanout net on its path: 59 loads after hierarchical buffering, 136
after flat buffering, 65 after `repair_design`. Each lever fixes the net
the previous one left and creates or leaves another.

**The obvious next step is not taken here, deliberately.** `set_max_fanout`
in the SDC would give `repair_design` a limit to repair against and would
very likely close clk_e. The SDC is frozen by registration
(`experiments/llm_proposer/PREREGISTRATION.md`), and changing a constraint
to make a number look better is exactly what freezing it is for. It is
stated as the next experiment, with its own registration, and not run
inside this one.

**Equivalence is still unproven** for every `repair_design` output, after
four recorded attempts. The physical lever remains a flow step, never a
proven transform.
