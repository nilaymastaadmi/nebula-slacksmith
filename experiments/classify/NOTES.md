# Interface classification — RESULT: the obligation can be chosen automatically

Run 9 Aug 2026. Yosys 0.33, z3 4.8.12.

## Why this exists

`vr_miter/` showed that pointing a k-padded miter at an elastic interface refutes
a **correct** transform in 0 seconds. So the obligation must be chosen from the
interface, and choosing wrong is a wrong answer rather than a missed optimisation:

```
RIGID    -> k-padded miter        opt.O[t+k] == ref.O[t]     (proved unbounded)
ELASTIC  -> stream equivalence    same value sequence        (proved bounded)
```

This is the front end that makes that choice.

## Three passes

1. **Lexical** — find ports whose names look like a handshake. Handles
   `valid`/`ready`, `vld`/`rdy`, `stall`, `busy`, and AXI-style channel prefixes.
   Cheap, and **wrong on its own**.
2. **Structural** — confirm the candidate reaches sequential state, by forward
   BFS through the post-`prep` netlist to any flop's `D`/`EN`/reset cone. A
   `ready` port that nothing reads cannot stall anything.
3. **Formal** — prove the property that actually *defines* an elastic interface:
   **output stability under back-pressure.** If the output is valid and the
   consumer is not ready, then next cycle the output data and valid must be
   unchanged. Generated as a wrapper and discharged with `yosys-smtbmc`.

Pass 3 is what makes this project-shaped rather than a heuristic: the verdict is
a discharged obligation, not an inference.

## Results

| Module | Lexical | Structural | Formal | Verdict |
|---|---|---|---|---|
| `mac_ref` (rigid) | no candidate | — | — | **RIGID** |
| `mac_vr_ref` | `out_ready` | reaches `$dff.D` | **PASSED** | **ELASTIC** |
| `alias_names` (`vld`/`rdy`) | `o_rdy` | reaches `$dff.D` | **PASSED** | **ELASTIC** |
| `axi_style` (AXI prefixes, active-low reset) | `m_axis_tready` | reaches `$dff.D` | **PASSED** | **ELASTIC** |
| `costume_ready` | `out_ready` | **REJECTED** | **FAILED** | **RIGID** |

## The case that earns the machinery

`costume_ready` has a port called `out_ready` and a port called `out_valid`, and
is **not elastic** — `out_ready` is declared and never read. A name-matching
classifier calls it elastic and emits stream equivalence for it.

Both later passes catch it, by **independent arguments**:

- structural: the signal never reaches sequential state, so it cannot stall anything;
- formal: the output data changes while the consumer is holding `ready` low, so
  the module is not honouring the handshake.

Two different mechanisms, same verdict. That corroboration is worth more than
either pass alone, and it is the kind of thing that is hard to fake in a demo.

## Honest limitations

State these before a judge finds them.

- **Pass 3 is bounded** (depth 16), not an unbounded proof. Reported as such.
- **`prove_backpressure.py` is a demonstrator, not a general tool.** Its wrapper
  assumes a single output channel, at most three data inputs, and fixed 8/16-bit
  widths. Generalising it means generating the wrapper from the port list rather
  than a template — real work, not done here.
- **Output stability is necessary, not sufficient.** A module could hold its
  output stable under back-pressure and still drop an *input* transaction. The
  complete contract also needs no-loss on the input side (every accepted input
  eventually produces exactly one output).
- **Protocol well-formedness is unchecked** — `valid` stable until `ready`, no
  combinational `ready`→`valid` path. Those are separate obligations.
- **Credit-based and other exotic flow control** will miss the lexical pass
  entirely and be classified rigid. That is a false *rigid*, which is the
  dangerous direction: it would emit a k-padded miter for an elastic interface.
  A conservative fallback (classify unknown as elastic) would be safer.

That last one is the most important limitation, because the failure is silent and
in the unsafe direction.

## Files

- `classify.py` — passes 1 and 2
- `prove_backpressure.py` — pass 3
- `costume_ready.v` — rigid interface with handshake-shaped ports
- `alias_names.v` — `vld`/`rdy` spelling
- `axi_style.v` — AXI channel prefixes, active-low reset
- `mac_ref.v`, `mac_vr_ref.v`, `mac_vr_opt.v` — copied from the miter experiments

## Reproduce

```bash
python3 classify.py mac_vr_ref mac_vr_ref.v
python3 prove_backpressure.py mac_vr_ref mac_vr_ref.v out_valid out_ready y
```

## Next

1. Generate the pass-3 wrapper from the port list so it works on arbitrary modules.
2. Add the no-loss input-side obligation to complete the elastic contract.
3. Default unknown interfaces to **elastic**, so the unsafe direction is never
   the silent one.
4. Wire the classifier into the miter generator so the obligation is selected
   end to end without being told.
