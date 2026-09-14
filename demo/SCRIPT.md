# Narration script for the demo video

Verbatim text for Sarvam TTS. `DEMO.md` stays the authoritative shot list and
is what `tools/demo_check.sh` verifies; this file is the audio layer and adds
nothing that is not evidenced there.

**Budget: 5 minutes.** Sarvam runs about 150 words per minute, so the ceiling
is **750 words of narration** and the target is under 700, because 5:00 is the
ceiling and not the target. **The count is measured, never written here:**
`python3 tools/script_words.py` counts the quoted narration lines and fails
above 750. Until 2026-09-12 this header said 690 while the file held 983,
6.6 minutes at 150 wpm; the count had been written once and never re-measured
after two rounds of narration corrections. Do not add to the narration
without cutting something, and re-run the counter after every edit.

**Screen is a real terminal throughout.** Remotion builds **only the title card
and the end card**. Every number marked ZOOM TARGET below is reached with
Recordly's cursor zoom on the real terminal output, not a graphic: a callout
restating a number the tool just printed is weaker than the tool printing it.
This matches `demo/VIDEO_PROMPT.md`.

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

> We couldn't find a published agentic R T L optimizer that changes latency
> and discharges a formal obligation for it. So we made transforms typed: the
> declared type picks the proof obligation, which makes latency-changing
> transforms checkable. Then we measured whether the generative A I half
> works.

---

## Beat 1. The benchmark. 20 seconds.

**COVERS:** benchmark specification
**SCREEN:** `python3 tools/bench_size.py`

> Forty-eight thousand six hundred and sixteen standard cells in five
> asynchronous clock domains, each generating its own clock in R T L, odd
> ratios included. Every multi-bit crossing has a gray-code FIFO. There's an
> R V thirty-two I core and two A E S cores.

---

## Beat 2. The closed loop. 45 seconds. **This is the demo.**

**COVERS:** deliverables 1, 2 and 3
**SCREEN:** the loop command, then `tools/show_run.py` on the same run

> One command, two iterations, replayed from file, and nobody steering it.
> Physical lever only. The generative half runs unattended in a separate run.
>
> It didn't guess. Ninety-one percent of that path's delay is in cells driving
> thirty-two or more loads, and the worst cell burns twenty-one nanoseconds
> driving three hundred loads. Buffering is built to fix a net's load and
> R T L isn't, so it went physical without spending a proposal.

**ZOOM TARGET:** `fanout 300 — 21.029 ns in one cell`

---

## Beat 3. Proven is not the same as useful. 45 seconds.

**COVERS:** deliverables 2 and 4
**SCREEN:** `tools/show_run.py experiments/closed_loop/run_v3_final.jsonl`

> The first three transforms here are formally proven correct, and all three
> make the number worse. The loop reverted each one by itself. This log
> predates two fixes; its depth and P four verdicts are wrong.
>
> The brief names four optimization classes. For most of this project our gate
> rejected retiming and state re-encoding by construction. Now both go through
> their own proof obligation.
>
> On that ninety-one percent fanout path, the model ran unattended, lever
> forced by hand, and proposed a fanout split. Our gate proved it. Measured
> outside the loop: one point four one four nanoseconds, and no group paid.
> Where the router picked R T L itself, on two designs, no proven transform
> helped.

---

## Beat 4. The refutation. 55 seconds. **The best beat. Do not cut it.**

**COVERS:** deliverable 6
**SCREEN:** the git log showing registration precedes results, then the table

> Proposal P four rewrote the A L U's shift arms as a single ternary. It
> passes every precondition and saves two hundred and eight cells, and it's
> wrong. A conditional operator takes its signedness from both branches, so
> pairing a signed branch with an unsigned one quietly turns an arithmetic
> right shift into a logical one. The instruction breaks for every negative
> operand.
>
> The file it edited has a six-line comment warning about exactly this, ten
> lines above the code it changed.
>
> Formal verification caught it in forty-six seconds with a concrete
> counterexample. The design's own firmware missed it. So did twenty thousand
> random instruction words.
>
> Catching it came down to stimulus, not severity. Those simulation gates are
> what agentic R T L tools ship with today.

**ZOOM TARGETS:** `46 s — counterexample a=ae19f605` and `20,000 vectors — missed`.
Both are evidenced: the witness is in `experiments/llm_proposer_aes/NOTES.md` and
`tools/demo_check.sh`; the directed probe's differing outputs are `ffffffff` against
`0fffffff` in `experiments/llm_proposer/fourchecker/RESULT.md`.

---

## Beat 5. Levers, what survives, and what closure costs. 50 seconds.

**COVERS:** deliverables 4 and 5
**SCREEN:** the lever table, then `experiments/composed_rtl/results/post_repair_summary.txt`, then the PPA numbers

> Like for like on clock B, our best R T L transform buys three point one
> eight five nanoseconds. The physical lever takes the same group from minus
> eighteen point nine to plus five point six. About one eighth.
>
> Then we composed our three proven transforms into one file. Before wires,
> five point one six five nanoseconds together, fifty-four percent of the sum
> of the parts. After the physical flow, zero, within the flow's own noise.
> The classifier had routed that path to buffering before any of this was
> measured. It was right.
>
> Closing all three groups with placement parasitics costs twenty point two
> percent area and forty-seven percent power. Frequency rises three point
> three two times, partly our flow defect.

**ZOOM TARGETS:** `+55.805 ns — zero lines of RTL`, then the `composed` row of
the post-repair summary against `gold`, then `3.32x achievable frequency`. Say with
the last one: **part of that 3.32x is a flow defect we shipped**, the missing
`buffer; upsize` script, worth 17.557 ns on its own (REPORT section 9).

The 2.799 to 0.844 scaling-factor line (36% to 118% of target) was cut for
time on 2026-09-12; it is in REPORT §8 and may return only if the counter
allows it.

---

## Beat 6. What we caught in ourselves. 35 seconds.

**COVERS:** thought process
**SCREEN:** `tools/verdict_regression.sh`, then `tools/classify_regression.py`

> Our gate once reported a solver timeout as a refutation. Worse, our path
> classifier undercounted fanout across module boundaries. The giveaway, a six
> point seven six two nanosecond cell at fanout one, sat in every log for
> two days. That cell drives three hundred and eighty-seven loads. Both are
> regression tests now. Every wrong log stays in the repository.

---

## Beat 7. The cheat no equivalence checker can catch. 30 seconds.

**COVERS:** innovation, gate zero
**SCREEN:** `bash experiments/sdc_integrity/run.sh`

> One netlist, identical in every row. A single line of S D C closes the
> group, worth five point one seven nine nanoseconds for changing nothing.
> Every equivalence checker we own calls the two designs equivalent, and it's
> right, because they're the same file. So the loop hashes the S D C, counts
> its exceptions, and won't report slack measured under anything but the
> registered constraints.

**ZOOM TARGET:** `+5.179 ns — byte-identical netlist`. The comparison to any RTL
transform ("more than our best proven transform bought") is **withdrawn** in REPORT
§5.2: 26,958-cell flat fixture against the 55,413-cell benchmark. It was in this
narration until 2026-09-12. Do not say it.

---

## Beat 8. We built the exam and published our own score. 35 seconds.

**COVERS:** innovation
**SCREEN:** the SlackBench results table

> Eight transform pairs, ground truth sealed before any checker ran. One wrong
> transform survived forty thousand simulated cycles. Equivalence checking
> couldn't express five of the eight questions, and two checkers rejected a
> pair that's provably equivalent. Ours declines on one case and scores seven
> of eight. We registered it shouldn't sweep its own suite, since a benchmark
> its author aces describes the benchmark, not the tool.

---

## End card. 5 seconds.

**SCREEN:** Remotion end card, repository URL.
No narration.

---

## Notes for the edit

- **Terminal at 165 columns and 40 rows or larger**, or the classify lines wrap
  and Beat 2 becomes unreadable. 110 was measured too narrow on 2026-09-13
  (`demo/PHASE1_CUT.md`, finding 4).
- **Beats 1, 2 and 6 are live compute, and all three are pre-run and played
  back** (`demo/PHASE1_CUT.md`, finding 8). Beat 2's narration says "replayed
  from file"; beats 1 and 6 make no liveness or timing claim. No narration line
  may state or imply how long the loop takes.
- **Beat 2's screen has no model call in it at all.** It is the v2 closed-loop
  run, which classifies the path and pulls the physical lever; "nobody steering
  it" refers to the loop, and the narration says so in the next sentence. The
  unattended generative run is a different run, a different SDC (v3) and a
  different number (`experiments/cli_backend/`, N = 1, REPORT §7.7), and Beat 3
  keeps its qualifiers on camera: lever forced by hand, gain measured outside
  the loop. Do not let the two merge in the edit.
- **Beat 5's composition line is the report's headline negative result** and
  it stays in the cut: the video must not tell a cleaner story than the
  document (`experiments/composed_rtl/NOTES.md`, amendment 2, N = 5).
- **Never read a table aloud.** Point at one number.
- Beat 4 is the strongest fifty-five seconds in the video. If the cut runs
  long, take it out of Beat 6 or Beat 8, never Beat 4 or Beat 5's second
  paragraph.
