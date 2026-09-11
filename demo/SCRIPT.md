# Narration script for the demo video

Verbatim text for Sarvam TTS. `DEMO.md` stays the authoritative shot list and
is what `tools/demo_check.sh` verifies; this file is the audio layer and adds
nothing that is not evidenced there.

**Budget: 5 minutes.** Sarvam runs about 150 words per minute, so the ceiling
is roughly **750 words of narration**. This script is 690. Do not add to it
without cutting something.

**Screen is a real terminal throughout.** Remotion is used for three things
only: the title card, three lower-third number callouts, and the end card.

---

## Pronunciation, give these to Sarvam

Numbers are already written as words in the narration below, so the engine
does not have to guess. Tool names it will get wrong unless told:

| written | say |
|---|---|
| RTL, SDC, EQY, CDC, ABC, AES, PPA | spell the letters |
| RV32I | "R V thirty-two I" |
| Yosys | "YO-sis" |
| SymbiYosys | "SIM-bee-YO-sis" |
| OpenSTA | "open S T A" |
| OpenROAD | "open road" |
| sky130 | "sky one-thirty" |
| repair_design | "repair design" |
| nor4_1 | "nor four" |
| G0 to G7 | "gate zero" to "gate seven" |
| ns | "nanoseconds", never "N S" |

---

## Beat 0. The claim. 20 seconds. Title card.

**COVERS:** framing
**SCREEN:** Remotion title card

> Every published agentic R T L optimizer that holds a formal gate refuses to
> change latency, because adding a pipeline stage breaks conventional
> equivalence checking. We made transforms typed, so the declared type picks
> the proof obligation, and latency-changing transforms become checkable.
> Then we measured whether the generative A I half actually works.

---

## Beat 1. The benchmark. 20 seconds.

**COVERS:** benchmark specification
**SCREEN:** `python3 tools/bench_size.py`

> Forty-eight thousand six hundred and sixteen standard cells. Five
> asynchronous clock domains, each with its own asynchronous reset and its own
> generated clock in R T L, including odd divide-by-three and divide-by-five.
> Gray-code asynchronous FIFOs on every multi-bit crossing. An R V thirty-two
> I core and two A E S cores. Not a toy.

---

## Beat 2. The closed loop. 50 seconds. **This is the demo. Run it live.**

**COVERS:** deliverables 1, 2 and 3
**SCREEN:** the loop command, then `tools/show_run.py` on the same run

> One command. Two iterations. Under fifty seconds.
>
> It did not guess which lever to pull. Ninety-one percent of that path's
> delay sits in cells driving thirty-two or more loads, and the worst single
> cell burns twenty-one nanoseconds driving three hundred loads inside the
> A E S key memory. No R T L rewrite shortens a net's load delay, so the tool
> routed to a physical lever instead of spending a proposal on it.

**CALLOUT (Remotion lower third):** `fanout 300 — 21.029 ns in one cell`

---

## Beat 3. Proven is not the same as useful. 45 seconds.

**COVERS:** deliverables 2 and 4
**SCREEN:** `tools/show_run.py experiments/closed_loop/run_v3_final.jsonl`

> Three transforms here are all formally proven correct, and all three make
> the number worse. The loop reverted every one of them by itself. Passing a
> formal gate means correct. It does not mean useful, and those are separate
> bars that this tool measures separately.
>
> The problem statement names four optimization classes. For most of this
> project the engine proposed two of them, and we assumed nobody had written
> the other two. That was wrong. Our own gate required a transform to preserve
> the flop count, which excludes every retiming and every state re-encoding by
> construction. Both now route through their own proof obligation.

---

## Beat 4. The refutation. 60 seconds. **The best beat. Do not cut it.**

**COVERS:** deliverable 6
**SCREEN:** the git log showing registration precedes results, then the table

> Proposal P four rewrote the A L U's shift arms into one ternary. It parses,
> it elaborates, it passes every precondition, and it saves two hundred and
> eight cells. It is also wrong. A conditional operator takes its signedness
> from both branches, so pairing a signed branch with an unsigned one silently
> degrades an arithmetic right shift into a logical one, and the instruction
> breaks for every negative operand.
>
> The file it edited carries a six-line comment warning about exactly this,
> ten lines above the code it changed.
>
> Formal verification caught it in forty-six seconds with a concrete
> counterexample. The design's own shipped firmware missed it. Twenty thousand
> random instruction words missed it.
>
> The verdict tracks stimulus quality, not bug severity. Every one of those
> simulation gates is what a real agentic R T L tool ships with today.

**CALLOUTS:** `46 s — counterexample a=ae19f605` and `20,000 vectors — missed`

---

## Beat 5. Levers, and what closure costs. 40 seconds.

**COVERS:** deliverable 5
**SCREEN:** the lever table, then the PPA numbers

> Same clock group, same constraints. Our best proven R T L transform bought
> four point nine two five nanoseconds. OpenROAD's repair design pass, which
> changes no R T L at all, bought fifty-five point eight. We report that as
> the finding it is.
>
> With placement parasitics all three groups close: clock A from minus
> thirty-six point seven to plus seventeen point six, clock B from minus
> forty-three point four to plus twelve point four, clock E from minus
> forty-seven point seven to plus nineteen point five. The price is twenty
> point two percent area, and closure survives clock tree synthesis and global
> routing at seven thousand eight hundred square microns.

**CALLOUT:** `+55.805 ns — zero lines of RTL` and `+20.2% area`

---

## Beat 6. What we caught in ourselves. 35 seconds.

**COVERS:** thought process
**SCREEN:** `tools/verdict_regression.sh`, then `tools/classify_regression.py`

> Our own gate reported a solver timeout as a refutation, because the checker
> prints the same line for both. We only noticed because one partition failed
> while all one hundred and twenty-eight partitions feeding it had passed.
>
> Worse: our path classifier undercounted fanout across module boundaries. Its
> own documentation named the tell, a six point seven six two nanosecond cell
> at fanout one, and that exact number sat in every log we produced for three
> days. The cell drives three hundred and eighty-seven loads.
>
> Both are standing regression tests now. Every wrong log is still in the
> repository, next to the corrected verdict.

---

## Beat 7. The cheat no equivalence checker can catch. 30 seconds.

**COVERS:** innovation, gate zero
**SCREEN:** `bash experiments/sdc_integrity/run.sh`

> One netlist. Twenty-six thousand nine hundred and fifty-eight cells,
> identical in every row. Only the constraints change.
>
> One line of S D C closes the group. It is worth five point one seven nine
> nanoseconds, which is more than our best formally proven transform bought,
> for changing nothing at all. Every equivalence checker we own would call
> these two designs equivalent, correctly, because they are the same file.
>
> So the loop hashes the S D C, counts its timing exceptions, and refuses to
> report slack measured under constraints that are not the registered ones.

**CALLOUT:** `+5.179 ns — byte-identical netlist`

---

## Beat 8. We built the exam and published our own score. 40 seconds.

**COVERS:** innovation
**SCREEN:** the SlackBench results table

> Eight transform pairs with ground truth declared before any checker ran,
> each one built to defeat a specific checker's abstraction. One wrong
> transform survived forty thousand simulated cycles. Combinational and
> sequential equivalence checking could not even express five of the eight
> questions. Two checkers confidently rejected a pair that is provably
> equivalent.
>
> And ours is wrong twice. We registered in advance that it should not sweep
> its own suite, because a benchmark its author aces tells you about the
> benchmark and not about the tool.

---

## End card. 5 seconds.

**SCREEN:** Remotion end card, repository URL.
No narration.

---

## Notes for the edit

- **Terminal at 110 columns or wider**, or the classify lines wrap and Beat 2
  becomes unreadable.
- **Beat 2 is the only live compute.** If it is slow on the day, pre-run it to
  a file and play that back, and say so on camera.
- **Never read a table aloud.** Point at one number. The callouts carry the
  rest.
- Beat 4 is the strongest sixty seconds in the video. If the cut runs long,
  take it out of Beat 5 or Beat 8, never Beat 4.
