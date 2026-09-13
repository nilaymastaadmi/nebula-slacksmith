# Invariant-carrying obligations: results

Registered in `PREREGISTRATION.md` (`42bab91`, amendments `c4478d2` and the one
committed with `fa3bc6e`), every prediction written before the step it scores.

## Scorecard

| id | prediction | result |
|---|---|---|
| R86 | derived `aes_key_mem` ports equal the trusted table | **CONFIRMED**, every field |
| R87 | regression surface unchanged after both repairs | **CONFIRMED**: verdict regression passes, `aes_key_mem` O2 via derived ports returns its committed verdict in every field, demo_check 15 of 15 |
| R88 | tv80 run 1 through the repaired gate is not PROVEN | **CONFIRMED**: FAIL on `eq_Inc_PC`, 4 s |
| R89 | i2c run 1 through the repaired gate is not PROVEN | **CONFIRMED**: FAIL on `eq_dout`, 0 s |
| R90 | the invariant proves on gold `tv80_core` by k-induction | **CONFIRMED**, both the two-bit exclusion and `$onehot` |
| R91 | the child is PROVEN under that invariant | **CONFIRMED** |
| R92 | a broken child is still REFUTED under the same invariant | **CONFIRMED**, so R91 stands |
| R93 | the proven transform gains more than 0.456 ns unbuffered | **WRONG**: it is **0.421 ns worse** |
| R94 | run 3 is PROVEN at the instantiated `Mode = 1` | **CONFIRMED** |
| R95 | run 1 at `Mode = 1` with no invariant is not PROVEN | **CONFIRMED**: FAIL on `eq_TStates` |
| R96 | the invariant also proves with the transform in place | **CONFIRMED**, both properties |

**Ten confirmed, one wrong.**

## What was proven, end to end

1. **Parent guarantee.** On `tv80s` at `Mode = 1`, from reset, `mcycle` is always
   one-hot, and in particular bits 5 and 6 are never set together. Proven by
   k-induction with undefined values as free choices, so `number_to_bitvec`'s
   `7'bx` default is not assumed away.
2. **Child obligation.** Gold and transformed `tv80_mcode`, both at `Mode = 1`,
   are equivalent on every input satisfying `!(MCycle[5] && MCycle[6])`.
3. **The link.** `tv80_core` drives `tv80_mcode.MCycle` directly from `mcycle`.
4. **The feedback loop closed by measurement, not argument (R96).** The decoder's
   outputs feed `mcycle`'s next state through `last_mcycle`, so the invariant was
   re-proven on the design with the transform in place. It holds.
5. **The assumption is not vacuous (R92).** A variant with one assignment wrong
   is still caught under it.

**The counterexamples are the argument in miniature.** With no invariant, the
solver's only distinguishing input was `MCycle = 7'b1100000`: bits 6 and 5 both
set, which is exactly what step 1 proves unreachable and exactly what the model
named in its rationale. Under the invariant, the broken variant was caught at
`MCycle = 7'b0101001`, an input the assumption permits.

**This is a new obligation class for this project**: a transform whose correctness
depends on a reachable-state property of the surrounding design, discharged by
proving the property on the parent and assuming it at the child. Before this
block the gate could not express it, and the proposal that needed it was reported
UNRESOLVED without ever being checked.

## And then it made timing worse

`experiments/depth_tv80/`'s survival harness, same run, every earlier row
reproduced to three decimals:

| variant | A unbuffered | B ABC lever | C before repair | C after repair | cells |
|---|---|---|---|---|---|
| gold | −0.894 | −0.296 | −6.072 | −2.021 | 3,447 |
| `ctrl_flip` (the floor) | −1.046 | −0.269 | −6.276 | −1.646 | 3,429 |
| **run 1, proven under the invariant** | **−1.315** | **−0.447** | **−6.710** | −1.783 | 3,422 |

**Unbuffered it is 0.421 ns worse**, 2.8x the 0.152 ns floor, so this is a real
regression rather than noise. It is worse after the ABC lever and before repair.
After `repair_design` it lands +0.238 against gold, inside the 0.375 ns
post-repair floor and the same shape the null control produces, so that column is
not claimed.

**R93 is wrong, and the depth cell is empty for a third proposal**, this time the
most principled one: formally proven, aimed at the path's actual depth, and
requiring an obligation class the project did not have yesterday.

## Why, as a hypothesis and not a finding

The model's reasoning was that bits 5 and 6 are mutually exclusive, so two
sequential `if` blocks can collapse into one parallel `case`. **The prover was
told the invariant. The synthesiser was not.** Yosys sees a `case` on two bits
with an empty `default`, has no reason to treat `2'b11` as unreachable, and builds
a full decode. The transform's intended saving lives entirely in the don't-care
that only the formal tool knows about.

**Not measured.** The test is cheap and specific: hand synthesis the same fact,
with `(* full_case, parallel_case *)` on the `case` or an explicit don't-care on
`2'b11`, and time it again. If that recovers a gain, the finding becomes
**"a transform that is correct only under an invariant can be optimised only by a
tool that is also given the invariant"**, which is a statement about the gap
between verification and synthesis in every LLM RTL flow, not about this model.
It is stated here as a hypothesis because it has not been run.

## What changes in the submission

- **Corrected:** both depth experiments' run 1 was never gated, not UNRESOLVED.
- **Corrected:** three gate defects, found and repaired or scoped, none changing a
  previously published verdict (R87).
- **Added:** the invariant-carrying obligation, demonstrated once, end to end,
  with its null control.
- **Unchanged:** no RTL transform on a depth-dominated design has yet produced a
  timing gain. Four proven transforms across two designs: 0.000, 0.000, −0.268,
  and now −0.421.
