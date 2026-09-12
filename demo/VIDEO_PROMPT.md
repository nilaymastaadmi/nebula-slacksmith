# Video build prompt

Run this in a **separate session**, in the repository root. It produces the
demo video in **two phases, in this order**:

1. **Picture first.** Recordly for the screen, Remotion for the title and end
   card, cut silent, verified.
2. **Voice second, once, on top of a verified cut.** Sarvam TTS. The Sarvam
   budget is limited, so audio is not generated until the picture is locked.

**Do not generate a single second of audio in phase 1.** A re-cut after
narration exists means re-synthesizing narration.

---

You are assembling the demo video for a hackathon submission. The repository is
`nebula-slacksmith`, branch `sandbox`. Three files govern everything:

- **`DEMO.md`** is the shot list: 9 beats, the exact command each one runs, and
  the expected output. `tools/demo_check.sh` runs every command in it and
  reports **15 pass, 0 fail** (verified 2026-09-12). Do not change a command in
  it.
- **`demo/SCRIPT.md`** is the narration: verbatim text per beat, a
  pronunciation table, ZOOM TARGETS, and the deliverable each beat evidences.
  Budgeted at **690 words for a 5-minute runtime** at Sarvam's ~150 wpm. Hard
  cap.
- **`SUBMISSION_PACK.md`** carries the author names, the repository URL and the
  deliverable mapping the video is evidence for.

The organiser's runtime window is **3 to 5 minutes**. 5:00 is the ceiling, not
the target; a 4:10 cut that lands every number beats a 4:58 cut that rushes one.

**Read `DEMO.md` and `demo/SCRIPT.md` end to end before producing anything.**

---

# Phase 1. Picture

## 1.1 Verify the commands still run

    bash tools/preflight.sh
    bash tools/demo_check.sh

**If demo_check is not `15 pass, 0 fail`, stop and report it** rather than
recording a demo whose commands no longer work. Beat 2 is live compute, about
50 seconds; everything else is instant or replayed from a committed log.

## 1.2 Remotion: two cards, nothing else

`demo/remotion/`, minimal. Two compositions:

- **Title**, 5 s: the project name, the track name (Nebula Track A, Constraint
  Optimization through RTL Enhancement Using Generative AI), and the two author
  names from `SUBMISSION_PACK.md`.
- **End**, 5 s: the repository URL from `SUBMISSION_PACK.md`.

Dark background, one accent colour, a system serif to match the report. No
animation beyond a fade.

**Do not build lower-third callouts.** Every number marked **ZOOM TARGET** in
`SCRIPT.md` is reached with Recordly's cursor zoom on the real terminal output.
A graphic restating a number the tool just printed is weaker than the tool
printing it, and it is one more thing that can disagree with the report.

## 1.3 Recordly: the screen

- **Terminal at 110 columns or wider**, or Beat 2's classify lines wrap and
  become unreadable.
- Record beats in `DEMO.md` order. Beat 2 is the only live compute; if it is
  slow on the day, pre-run it into a file, play that back, and say so on camera.
- Use cursor zoom on each ZOOM TARGET in `SCRIPT.md`, and nowhere else.
- Never read a table aloud on camera. Point at one number.

## 1.4 Cut it silent, and verify the cut

Assemble title card, 9 beats, end card. **Then check the silent cut against
`SCRIPT.md` before any audio exists:**

- total runtime is between 3:00 and 5:00
- every beat's screen time is at least its `SCRIPT.md` target, so the narration
  will fit without speeding it up
- every ZOOM TARGET is on screen long enough to read
- no frame shows a number that is not in `REPORT.md` or `SUBMISSION_PACK.md`

**Phase 1 ends with a locked silent cut and a per-beat duration table.** Get
that table signed off before phase 2.

---

# Phase 2. Voice, once

Only after the cut is locked.

**The Sarvam budget is limited and there is little margin for error.** Treat
every synthesis call as spend. The order below exists so that text errors are
caught before they cost tokens, not after.

## 2.1 Write the text files first, synthesize nothing

One plain-text file per beat, `demo/audio/beat0.txt` through `beat8.txt`,
containing **only** that beat's narration with the `>` quote markers stripped.
No headings, no stage directions, no ZOOM TARGET lines.

Apply the pronunciation table in `SCRIPT.md` **by rewriting the text itself**,
not by adding markup: "Yosys" becomes "YO-sis", "RTL" becomes "R T L", and so
on. Numbers are already written as words; if you find one still in digits,
spell it out.

## 2.2 Dry-run before spending anything

Write `demo/audio/MANIFEST.tsv`, one row per beat: file, word count, expected
seconds at 150 wpm, the beat's target duration from `SCRIPT.md`, and the
**measured** duration of that beat in the locked cut.

**Flag every beat whose expected seconds exceed its measured picture
duration.** Fix the text, not the picture. Re-check the manifest. Only when no
beat is flagged does anything get synthesized.

## 2.3 Synthesize one beat, listen, then the rest

Synthesize **beat 4 first**, alone. It is the strongest sixty seconds in the
video and it carries the hardest pronunciations. Listen to it. If the voice,
pace or pronunciation is wrong, fix the text and spend one more call on beat 4,
not on nine beats.

Once beat 4 is right, synthesize the remaining eight. **One pass.** Keep every
`.txt` alongside its audio, so a later fix re-synthesizes one beat and not the
set.

## 2.4 Lay it under the picture

No re-cutting the picture to fit the voice. If a beat's audio overruns, the
text was wrong in 2.2 and gets shortened there.

---

## Rules that hold in both phases

- **Do not invent a number.** Every figure spoken or shown appears in
  `REPORT.md` or `SUBMISSION_PACK.md` and is checked by
  `tools/check_report_numbers.py`. If a number in `SCRIPT.md` looks wrong,
  **report it, do not correct it silently.**
- **Do not extend the runtime.** The script is 690 of 750 words. Anything added
  comes out of something else.
- **Beat 4 is never cut.** It is the LLM proposal that passes the design's own
  shipped firmware and 20,000 random vectors and is formally refuted in 46
  seconds with a concrete counterexample. If the cut runs long, take it out of
  Beat 5 or Beat 8.
- **Beat 2's screen contains no model call.** It is the v2 closed-loop run
  pulling the physical lever; "nobody steering it" refers to the loop. The
  unattended generative run is a different run, a different SDC and a different
  number (`experiments/cli_backend/`, N = 1, REPORT §7.7). Do not let the edit
  merge them.
- **Retracted claims stay retracted.** Do not reinstate "no RTL rewrite
  shortens a net's load delay", the universal "every published optimizer"
  framing, the 55.805-over-4.925 ratio, or Beat 7's "more than our best proven
  transform bought" (withdrawn in REPORT §5.2, removed from the narration
  2026-09-12). `DEMO.md` and `SCRIPT.md` carry the corrected wording and say why.
- **Beat 3's unattended run keeps its qualifiers on camera**: lever forced by
  hand, gain measured outside the loop. REPORT §7.7 puts them in the sentence,
  so the narration does too.
