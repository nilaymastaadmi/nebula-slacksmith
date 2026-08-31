# Gate outcomes, all 6, matched-baseline G5

| id | def_id | k | G1 | G2 | G3 | G4 | cells | G5 clk_a |
|---|---|---|---|---|---|---|---|---|
| P1 | operator_sharing_addsub | 0 | PASS | PASS | PASS | PROVEN | 8362 | -2.471 |
| P2 | operator_sharing_shifter | 0 | PASS | PASS | PASS | PROVEN | 7918 | +0.829 |
| P3 | operator_sharing_comparator | 0 | PASS | PASS | PASS | PROVEN | 8409 | -2.051 |
| P4 | mux_priority_to_parallel | 0 | PASS | PASS | PASS | REFUTED (1/447: alu_out) | 8061 | n/a |
| P5 | pipeline_cut_rigid | 1 | PASS | PASS | PASS | REFUTED (eq_dmem_addr) | 8358 | n/a |
| P6 | operator_sharing_branch_comparator | 0 | PASS | PASS | PASS | PROVEN | 8380 | -3.400 |

gold: 8269 cells, 2048 flops. Baseline clk_a slack -25.287.
Primary bar MET by P2. 4 proven, 2 refuted, 1 improved timing.

## P4 four-checker column
EQY formal            CAUGHT (46s, partition alu_out)
sim, real firmware    MISSED (400 cycles; the shipped loop has no shift insn)
sim, 20k random insn  MISSED
sim, directed SRAI    CAUGHT (gold ffffffff, gate 0fffffff)
