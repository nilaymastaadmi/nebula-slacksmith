# G7 in the loop: does the gate portfolio catch a CDC-breaking transform?

**Written 2026-09-11, before the variant RTL exists and before any gate runs.**
Git is the evidence for that ordering.

## The hole

`tools/slacksmith.py` ran G0 to G6. A transform that breaks a clock crossing
passes all of them, and the project's own benchmark proves it: SlackBench
**CDC-1 is functionally a latency change** and **CDC-2 is functionally
identical**, and both are defects. §7.4 records every checker in the suite
either being unable to express the question or being **correct and useless**.

So until today an LLM-proposed transform could have removed a synchronizer stage
or moved a gray encoder across a domain boundary, and the loop would have
accepted it with G4 PROVEN.

## What was built

G7 is now a **differential** gate in the loop, not a design-cleanliness check.
`bench_top` may carry pre-existing findings and a proposal is not responsible
for those, so the gate runs `tools/cdc_check.py` on the original module and on
the variant and rejects **a violation the original did not have**. It runs with
`--hamming`, because the structural pass alone cannot separate this class:
before and after, the crossing is a 4-bit MULTIBIT at depth 2.

`ERROR` is not a pass, on the same principle that `UNRESOLVED` is not a pass at
G4.

## The test

`rtl/async_fifo.v` is this benchmark's own dual-clock FIFO, instantiated three
times in `bench_top`. Its write pointer is gray-encoded **before** the
synchronizer:

    wgray_r  <= wbin_nxt ^ (wbin_nxt >> 1);     // gray, then cross
    sync2ff u_sync_w2r (.d(wgray_r), .q(wgray_sync));

The variant moves the encoder to the **far side** of the crossing, so the bus
that physically crosses is raw binary:

    sync2ff u_sync_w2r (.d(wbin_r), .q(wbin_sync));
    wire [AW:0] wgray_sync = wbin_sync ^ (wbin_sync >> 1);

This is CDC-2's defect applied to a real module rather than a purpose-built
case. It is **functionally equivalent**, because a gray encoder is combinational
and therefore commutes with the synchronizer's delay:
`gray(delay2(x)) == delay2(gray(x))`.

## Registered predictions

| # | prediction | confidence |
|---|---|---|
| **L1** | **G4 accepts the variant**, PROVEN or equivalent. The transform genuinely does not change the function. | high |
| **L2** | **G7 REJECTS it**, naming a `MULTIBIT_UNSAFE` violation the original does not have. | high |
| **L3** | The structural pass **alone** cannot tell them apart: both sides report a 4-bit MULTIBIT crossing at depth 2, and only the Hamming discharge separates them. | high |
| **L4** | G7 reports **SKIPPED** for `rv32i_core` and `aes_key_mem`, the modules every existing proposal targets, because neither has a clock crossing to break. So wiring G7 in changes **no** previously recorded verdict. | medium |

**L1 is the one that makes the result mean anything.** If G4 rejects the
variant then equivalence checking caught it after all, the hole is not real, and
G7 earns nothing here. The claim is only interesting if the transform is
genuinely equivalent and genuinely broken.

## What would void this

- Building the variant so that it is *not* functionally equivalent, then
  reporting G7's rejection as if it had caught a CDC-specific defect. L1 exists
  to detect exactly that, and a G4 rejection means the case is thrown out, not
  patched until it passes.
- Tuning `cdc_check.py` after seeing this run.

## Limits, stated before results

- **One transform, one module, one defect class.** An outcome, not a rate.
- **G7 only fires on modules that have crossings.** L4 says it will SKIP every
  module the current proposals target, so this closes a hole that the existing
  runs never walked into. That is a smaller claim than "the loop now catches CDC
  bugs in practice", and it is the claim being made.
- The variant is written by the same session that wrote the gate, which is the
  standing conflict disclosed in every registration here.
