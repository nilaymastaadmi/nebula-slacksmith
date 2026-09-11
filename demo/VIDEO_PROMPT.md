# Video build prompt

Run this in a **separate session**, in the repository root. It produces the
assets for the demo video. It does not record anything: recording is a human
sitting in front of Recordly, and the checklist at the end says how.

---

You are assembling the demo video for a hackathon submission. The repository is
`nebula-slacksmith`, branch `sandbox`. Two files govern everything:

- **`DEMO.md`** is the shot list: 9 beats, the exact command each one runs, and
  the expected output. `tools/demo_check.sh` runs every command in it and
  currently reports **15 pass, 0 fail**. Do not change any command in it.
- **`demo/SCRIPT.md`** is the narration: verbatim text per beat, a pronunciation
  table, and the deliverable each beat evidences. It is budgeted at **690 words
  for a 5-minute runtime** at Sarvam's ~150 wpm. Treat that budget as a hard
  cap.

**Read both before writing anything.** Then produce four things.

## 1. Per-beat narration files for Sarvam

One plain-text file per beat, `demo/audio/beat0.txt` through `beat8.txt`,
containing **only** the narration text for that beat with the `>` quote markers
stripped. No headings, no stage directions, no callout lines.

Apply the pronunciation table in `SCRIPT.md` by rewriting the text itself, not
by adding markup: "Yosys" becomes "YO-sis", "RTL" becomes "R T L", and so on.
Numbers are already written as words in the script; leave them that way. If you
find a number that is still in digits, spell it out.

Write `demo/audio/MANIFEST.tsv` with one row per beat: file, word count,
expected seconds at 150 wpm, and the beat's target duration from `SCRIPT.md`.
**Flag any beat whose word count implies more than its target duration.**

## 2. A Remotion project for the title card and end card only

`demo/remotion/`, minimal. Two compositions:

- **Title**: the project name, the track name (Nebula Track A, Constraint
  Optimization through RTL Enhancement Using Generative AI), and the two author
  names from `SUBMISSION_PACK.md`. 5 seconds.
- **End**: the repository URL from `SUBMISSION_PACK.md`. 5 seconds.

Nothing else. **Do not build lower-third callouts.** Recordly's cursor-driven
zoom does that job on the real terminal output, and a graphic restating a number
the tool just printed is weaker than the tool printing it.

Keep the styling plain: dark background, one accent colour, a system serif to
match the report. No animation beyond a fade.

## 3. A recording checklist

`demo/RECORDING.md`, derived from the "Notes for the edit" section of
`SCRIPT.md` plus what you find in `DEMO.md`. It must state:

- the terminal width required (110 columns or wider, or Beat 2's classify lines
  wrap and become unreadable)
- which beat is the only live compute, and what to do if it is slow on the day
- the exact order to record in
- which beats may be cut if the edit runs long, and which may not

## 4. A verification step

Before you finish, run:

    bash tools/demo_check.sh

and report the result. **If it is not `15 pass, 0 fail`, stop and say so**
rather than producing assets for a demo whose commands no longer work.

---

## Rules

- **Do not invent a number.** Every figure spoken in the video appears in
  `REPORT.md` or `SUBMISSION_PACK.md` and is checked by
  `tools/check_report_numbers.py`. If a number in `SCRIPT.md` looks wrong,
  report it; do not correct it silently.
- **Do not extend the runtime.** The cap is 5 minutes and the script is already
  at 690 of 750 words. Anything you add comes out of something else.
- **Beat 4 is the strongest sixty seconds and is never cut.** It is the LLM
  proposal that passes the design's own shipped firmware and 20,000 random
  vectors and is formally refuted in 46 seconds with a concrete counterexample.
- **Beat 2's narration says "no human in it".** That is true of the `cli`
  backend (`experiments/cli_backend/`, N = 1) and **not** of the `handoff`
  backend, where a person passes the prompt to a model. If the recording uses
  handoff, that clause must be cut. Ask which is being demonstrated rather than
  assuming.
