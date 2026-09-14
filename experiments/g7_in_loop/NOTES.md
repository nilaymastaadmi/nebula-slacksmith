# G7 in the loop: results

Registered in `PREREGISTRATION.md` before the variant RTL existed (`7d5c775`).

## Scorecard: 3 of 4, and the miss is the interesting one

| # | registered | outcome |
|---|---|---|
| **L1** | G4 **accepts** the variant | **WRONG.** EQY rejected it, 15 of 43 partitions |
| **L2** | G7 **rejects** it, naming a violation the original lacks | **CONFIRMED** |
| **L3** | the structural pass alone cannot separate them | **CONFIRMED** |
| **L4** | G7 SKIPs `rv32i_core` and `aes_key_mem` | **CONFIRMED**, 0 crossings, 1 clock domain each |

L2 and L3, measured:

| | original | variant |
|---|---|---|
| structural | `MULTIBIT`, 4 bits, depth 2, ×2 | `MULTIBIT`, 4 bits, depth 2, ×2 |
| Hamming | **PROVEN** to depth 16, both pointers | **REFUTED**, both pointers |
| exit | 0 | 1 |

Structurally the two are indistinguishable. Only discharging Hamming safety
separates them, which is why the gate runs with `--hamming` and why a purely
structural CDC lint would pass this transform.

## Why L1 failed, and why the answer changes the claim

The registration said a G4 rejection **throws the case out** rather than
licensing a patch. It is thrown out: **this run does not demonstrate "a
transform passes G4 and G7 catches it."**

But the reason matters, so it was measured rather than assumed. An
output-only bounded miter (`io_miter.sh`) drives both designs from identical
inputs, both clocks shared, and compares `wfull` and `rempty`:

    SBY DONE (PASS, rc=0)     depth 20

**The variant is I/O equivalent.** EQY did not reject it for a difference the
interface can see. EQY pairs internal nets by name and proves each partition,
and `u_sync_w2r.d` carries a gray code in one design and raw binary in the
other, so those partitions genuinely are not equivalent. The 15 failures are
`u_sync_w2r.d.*`, `u_sync_r2w.d.*`, `u_sync_r2w.q.*`, `wgray_sync`,
`rgray_sync` and `wfull_nxt`: the crossing nets and what they feed.

So **EQY gave the right answer for the wrong reason.** It detected that internal
nets changed meaning, which here coincides with the defect but is not caused by
it. A transform that broke the same crossing **without** re-purposing a named
internal net would separate the two gates cleanly, and this run does not
contain one.

That is the SlackBench thesis turning up inside this project's own gate, and it
is a weaker and more specific claim than the one registered:

> **What is shown:** G7 rejects a CDC-breaking transform that is I/O equivalent,
> using a property no equivalence checker states, while the structural pass
> alone cannot tell it from the original.
>
> **What is not shown:** that G4 would have let this particular transform
> through. It did not.

## Four bugs found on the way, all mine

1. **The fifth confident-wrong-verdict in G7, and the same mechanism as the
   fifth.** Auto-detected crossings were handed `declared.get(sig)`, empty
   whenever `--crossing` was not passed, so the source clock fell back to the
   **destination** clock. `wgray_r` lives in `wclk` and was checked against
   `rclk`, and **the original async_fifo came back REFUTED**, having been
   PROVEN that morning by the run that declared its crossings explicitly. The
   earlier fix covered declared crossings only. The source flop is known at
   detection time, so its clock and reset are now recorded on the crossing
   rather than re-derived later from something that may be empty, and there is
   no fallback to the destination clock at all.
2. **The differential gate keyed on signal names.** `"verdict:sources"` would
   have read a rename as a new violation, so G7 would have rejected this
   variant for renaming `wgray_r` and reported it as a CDC catch. Now keyed on
   the crossing: verdict, source clock, destination clock, width.
3. **`depth` under EQY's `[options]`**, which EQY does not accept. This project
   already hit that exact error in `experiments/slackbench` and it was
   reintroduced here.
4. **The first I/O miter compared uninitialised memory.** Each instance has its
   own unreset `mem`, started at independent arbitrary values by BMC, so the
   `rdata` assert failed immediately and I read that as "the variant is not I/O
   equivalent". It was a miter bug. Caught by reading which assert line
   actually failed instead of the one assumed: line 30 was `rdata`, not
   `wfull`. `rdata` is now excluded, with the reason in the script.

Bug 1 is the one that would have destroyed the experiment: with the original
refuted too, the differential gate sees a violation on both sides, and
depending on the comparison key it reports either a false PASS or a REJECT for
the wrong reason. Bug 4 nearly produced a published claim that was false.

## Limits

- **One transform, one module, one defect class.** An outcome, not a rate.
- **The separation between G4 and G7 is not demonstrated**, only the fact that
  G7 catches a defect using a property equivalence does not state. Building a
  CDC-breaking transform that leaves internal net names intact would settle it
  and is not done.
- **G7 fires only on modules with crossings.** L4 confirms it SKIPs everything
  the current proposals target, so this closes a hole the existing runs never
  walked into rather than fixing a verdict any of them got wrong.
- Both the variant and the gate were written by the same session, the standing
  conflict disclosed in every registration here.
