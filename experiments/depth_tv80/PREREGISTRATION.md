# Pre-registration: the depth cell, on an instrument that can show it

Registered 2026-09-12. **The floor was measured first and is quoted below; the
predictions were written after seeing it and before any proposal ran**, which is
the order this block requires and the opposite of the usual order for a reason:
a prediction about "a gain above the floor" is meaningless until the floor is a
number. Predictions **R76 to R81**.

## Why tv80 and not `i2c`

`experiments/depth_i2c/` ran the loop end to end, unforced, on external IP and
every decision was right. The gain was **0.000**, so the depth-dominated cell of
the survival table is empty. It could not have been otherwise: `i2c` is 560
cells and a null edit moved its unbuffered slack by **0.424 ns**, so there was
no room for a real effect to show above the noise.

`tv80s` from `hutch31/tv80` (MIT-style licence), 3,447 cells, is the second
attempt. **The physical lever does not close it**, which is the case where RTL
should matter: unbuffered **−0.894**, after the ABC lever **−0.296**, after
`repair_design` **−2.021**.

## The floor, measured before these predictions were written

Three null controls, all functionally identical to gold by construction:

| control | what it changes | A unbuffered | B ABC lever | C after repair | cells |
|---|---|---|---|---|---|
| gold | — | −0.894 | −0.296 | −2.021 | 3,447 |
| `ctrl_rename` | module name and its instantiation | −0.894 | −0.296 | −2.021 | 3,447 |
| `ctrl_reorder` | that module's position in the file | −0.894 | −0.296 | −2.021 | 3,447 |
| **`ctrl_flip`** | one ternary rewritten as its complement | **−1.046** | −0.269 | **−1.646** | 3,429 |

**Two of the three controls turned out to be no-ops and that is recorded, not
hidden.** `ctrl_reorder` produces a netlist **byte-identical** to gold: Yosys
elaborates by hierarchy, not by file position, so moving a module's text is not
a perturbation at all. `ctrl_rename` produces a different netlist, because
module names propagate into instance names, and identical timing to three
decimals. Neither changes structure, so neither can tell you whether the
instrument resolves a structural effect. `ctrl_flip` was added for that and is
the only one of the three that measures anything.

**Floor, from `ctrl_flip`:** **0.152 ns unbuffered**, 0.027 after the ABC lever,
**0.375 ns after `repair_design`**.

**Usability test, declared by this block before the floor was known:** unusable
if the largest excursion exceeds 5% of the period. The period is 8.044 ns, so
the bar is **0.402 ns**. The largest excursion is **0.375 ns**. **tv80 passes,
and it passes narrowly**, by 0.027 ns on the post-repair column. The unbuffered
column, where the RTL gain is first seen, has far more room at 1.9% of period.

`gold_run2` reproduces gold exactly, so the OpenROAD flow is deterministic here
as it was on the benchmark (R47).

## Predictions

**R76.** The classifier routes to **RTL unforced in 3 of 3 runs**. *Prior:
strong. The transfer study scored this design DEPTH with a fanout share of
0.000, and the router sends depth-dominated paths to RTL.*

**R77.** **At least 1 of 3** proposals reaches **PROVEN inside the loop**.
*Prior: moderate. On `i2c` one of three did.*

**R78.** A proven proposal's unbuffered gain exceeds **3x the floor, 0.456 ns**.
*Prior: weak, and this is the one the block exists to answer. `i2c` returned
0.000 and the composed benchmark work returned gains that did not survive.*

**R79, the survival cell.** The gain after the ABC lever retains **at least 50%**
of the unbuffered gain. *Prior: weak. On the benchmark's fanout-dominated paths
the retained fraction was 0%.*

**R80.** The gain after `repair_design` exceeds the control's post-repair
excursion of **0.375 ns**. *Prior: weak. Nothing in this project has yet beaten
a post-repair floor.*

**R81.** The in-loop G5 **confirms rather than reverts**. *Prior: moderate.*

## Declared fallback, on the quantity and not the gate

If **no proposal produces a positive unbuffered gain above 0.152 ns** for any
reason at all, including none proposed, refused, refuted, undecidable, or proven
and null, then **one handoff-tier proposal is written and run through the same
gate, labelled as handoff tier**, and the depth cell is reported at that
provenance. The fallback is declared now so that using it later is a disclosed
step rather than a rescue.

## What would void this

- Editing anything under `tools/` while the three runs are in flight. A repair
  waits until run 3 exits, is registered as an amendment, and every sample is
  replayed through the repaired tool.
- A proposal whose artifacts are not copied out of scratch in the same turn is
  **not counted**, whatever its verdict. `experiments/depth_i2c/` lost a PROVEN
  to a wiped scratch directory and reported it as absent.
- Three runs is three runs. No fourth run because the first three were
  unflattering.

## Scope

One design, three samples, one model, one machine. tv80 is a different artifact
from the `cpu_pipe` the plan named and from the tv80 netlist the transfer study
measured: this is upstream source at 3,447 cells and 8.938 ns, against that
study's 4,023 cells and 9.797 ns, so its DEPTH verdict is re-derived here rather
than inherited.

---

## Amendment 1, 2026-09-12: a harness defect, registered before the tool is touched

All three runs exited before proposing. Every one of them classified correctly
and routed to RTL unforced, then stopped:

```
{"step": "classify", "verdict": "DEPTH_DOMINATED", "fanout_delay_share": 0.1602,
 "lever": "rtl", "routed_lever": "rtl", "lever_forced": false}
{"step": "stop", "reason": "module_not_in_file_list",
 "module": "$paramod$1a08092a55a4361642517ba6d8d0502484bd6d82\tv80_mcode"}
```

**This is our harness, not the model.** `tv80_mcode` is instantiated with
parameters, so Yosys renames it `$paramod$<hash>\tv80_mcode` in the netlist.
`tools/slacksmith.py` maps the binding module back to a source file by filename
and then, since the `i2c` repair, by searching for its `module` declaration.
Neither can match a mangled name, because no source file declares
`$paramod$<hash>\tv80_mcode`.

**It is the same defect class the `i2c` run found, one layer deeper.** That
repair taught the lookup that filename need not equal module name. This one
teaches it that the *netlist's* module name need not equal the *source's*.

### The repair, stated before it is written

Unmangle before looking up: split the netlist module name on backslashes, drop
any segment containing `=` (a parameter binding), and take the last remaining
segment as the source-level module name. `$paramod$<hash>\tv80_mcode` and
`$paramod\tv80_mcode\WIDTH=32` both resolve to `tv80_mcode`.

Nothing else changes. No gate, no classifier, no lever policy, no SDC.

### Rules this repair follows

- **All three samples had already exited** before `tools/` was touched. The
  repair waits for the last sample by design, and it did.
- **All three runs are replayed** through the repaired tool. A replay is not a
  new sample: the three replayed runs are runs 1 to 3, and R76 to R81 are scored
  on them. There is no fourth run.
- **The failed runs are kept**, logs and decision files, next to the replayed
  ones. `experiments/depth_i2c/` set that precedent and it is the reason this
  defect was recognisable in one line.

### Prediction on the repair itself

**R82.** After the repair, all three replayed runs reach the proposer, and the
binding module is reported as `tv80_mcode`. *Prior: strong, and if it misses the
defect was misdiagnosed, which is worth knowing before any proposal is judged.*

---

## Amendment 2, 2026-09-12: a second harness defect, same discipline

**R82. CONFIRMED.** All three replayed runs unmangled the module and found it:

```
unmangled parameterised module $paramod$1a08092a...\tv80_mcode -> tv80_mcode
binding module tv80_mcode found in tv80.v (filename does not match module name)
```

The diagnosis was right. The runs then died one step further on:

```
OSError: [Errno 7] Argument list too long: '/home/toshn/.local/bin/claude'
```

**Our harness again, and again a limit no earlier design reached.**
`tools/proposer.py`'s `cli` backend passes the whole prompt as a single argv
element. The prompt carries the target module's full source, and `tv80_mcode`
is a microcode decoder of roughly 2,600 lines, which puts one argument past
Linux's 128 KB per-argument ceiling. `aes_key_mem` at 434 lines and `i2c` at
25 KB were both comfortably under it.

### The repair, stated before it is written

Pass the prompt on **stdin** rather than as an argument: `claude -p` with the
text on standard input. The request file written beside it is unchanged, so the
committed artifact of what the model was asked stays byte-identical in form.

Nothing else changes. No gate, no classifier, no lever policy, no SDC, no
prompt text.

### Prediction

**R85.** After the repair, all three replayed runs reach a **G4 verdict of any
kind**. *Prior: strong. The two failures so far were both lookups and plumbing,
neither of which touched the model or the gate.*

### What this pair of defects is worth saying out loud

Two defects, both in our tooling, both found by pointing the loop at a design
larger and less regular than the benchmark it was built on, and **neither
touched a published result**. That is the same finding `experiments/unforced/`
reported on `i2c` and it is now reproduced on a third design: the router and the
gate are sound, and the plumbing around them had exactly one design's worth of
testing. Reported here rather than quietly fixed, because a tool that only works
on its author's benchmark is the thing this project keeps warning about.
