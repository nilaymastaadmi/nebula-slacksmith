# Video build prompt

Run this in a **separate session**, in the repository root
(`nebula-slacksmith`, branch `sandbox`).

## The three tools, and what each one is for

| tool | does exactly this | never does this |
|---|---|---|
| **Recordly** | records the real terminal for all 9 beats, and does the cursor zoom on each ZOOM TARGET | narration, titles, graphics |
| **Remotion** | renders two cards only: a 5 s title card and a 5 s end card | lower thirds, callouts, animated numbers |
| **Sarvam TTS** | the voice track, generated **once**, only after the picture is locked | anything in phase 1 |

**Order is not negotiable: picture first, voice second.** A re-cut after
narration exists means re-synthesizing narration, and the Sarvam budget is
limited with little margin for error. **Generate no audio in phase 1.**

## The three files that govern everything

| file | what it is |
|---|---|
| **`DEMO.md`** | the shot list. 9 beats, the exact command each runs, the expected output. Do not change a command in it. |
| **`demo/SCRIPT.md`** | **the script.** Verbatim narration per beat, the pronunciation table, the ZOOM TARGETS, and the deliverable each beat evidences. |
| **`SUBMISSION_PACK.md`** | author names, repository URL, and the deliverable mapping the video is evidence for. |

**Read `DEMO.md` and `demo/SCRIPT.md` end to end before producing anything.**

**Never quote a word count or a pass count from memory or from a header.** Both
are measured:

```
python3 tools/script_words.py     # narration length, per beat and total
bash tools/demo_check.sh          # every command in DEMO.md, must end "0 fail"
```

Until 2026-09-12 this file carried a hardcoded 690-word budget while the script
held 983 words, which is 6.6 minutes of narration against a 5-minute cap. The
number had been written once and never re-measured. Run the tools.

The organisers' window is **3 to 5 minutes**. 5:00 is the ceiling, not the
target: a 4:10 cut that lands every number beats a 4:58 cut that rushes one.

---

# Phase 1. Picture

## Step 1. Prove the demo still runs

```
bash tools/preflight.sh
bash tools/demo_check.sh
```

**If demo_check does not end in `0 fail`, stop and report it.** Do not record a
demo whose commands no longer work. Note the pass count it prints; that is the
current number, whatever any document says.

## Step 2. Remotion, two cards, nothing else

Build `demo/remotion/` with exactly two compositions:

- **Title, 5 s.** Project name; the track name (Nebula Track A, Constraint
  Optimization through RTL Enhancement Using Generative AI); the two author
  names from `SUBMISSION_PACK.md`.
- **End, 5 s.** The repository URL from `SUBMISSION_PACK.md`.

Dark background, one accent colour, a system serif to match the report, no
animation beyond a fade.

**Build no lower thirds and no callout graphics.** Every number marked **ZOOM
TARGET** in `demo/SCRIPT.md` is reached with Recordly's cursor zoom on the real
terminal output. A graphic restating a number the tool just printed is weaker
than the tool printing it, and it is one more thing that can disagree with the
report.

## Step 3. Recordly, the screen

- **Terminal at 110 columns or wider**, or Beat 2's classify lines wrap and
  become unreadable.
- Record the beats in `DEMO.md` order, one take per beat.
- **Beat 2 is the only live compute**, about 45 seconds. If it is slow on the
  day, pre-run it into a file, play that back, and say so on camera.
- Cursor-zoom on each **ZOOM TARGET** in `demo/SCRIPT.md`, and nowhere else.
- Never read a table aloud. Point at one number and let the rest sit there.

## Step 4. Cut it silent, then verify the cut

Assemble: title card, Beat 0 through Beat 8, end card. **Then check the silent
cut before any audio exists.**

```
python3 tools/script_words.py     # per-beat seconds at 150 wpm
```

- Total runtime between 3:00 and 5:00.
- Every beat's screen time is **at least** the seconds that tool prints for it,
  or the narration will not fit without speeding it up.
- Every ZOOM TARGET is on screen long enough to read.
- **No frame shows an invented number, and no frame shows a number that
  contradicts `REPORT.md` or `SUBMISSION_PACK.md`**, meaning the same quantity at
  a different value. A real terminal prints raw output those documents do not
  carry (iteration slacks, per-row table cells, fixture counts, cycle counts),
  and that is expected: absence is not the risk, contradiction is. A screen
  showing a value the report has **retracted** must be flagged in that beat's
  narration or not shown. Every **spoken** number and every **ZOOM TARGET** must
  appear in one of the two documents. (Amended 2026-09-13: the literal reading,
  every on-screen number in the documents, failed 61 of 125 raw terminal values
  and is unsatisfiable by a real terminal.)

**Phase 1 ends with a locked silent cut and a per-beat duration table.** Hand
that table over and get it signed off. Do not start phase 2 without it.

---

# Phase 2. Voice, once

Only after the cut is locked and the duration table is approved.

**Treat every Sarvam call as spend.** The order below exists so that text
errors are caught before they cost tokens, not after.

## Step 5. Write the text files, synthesize nothing

One plain-text file per beat, `demo/audio/beat0.txt` through `beat8.txt`,
containing **only** that beat's narration from `demo/SCRIPT.md` with the `>`
quote markers stripped. No headings, no stage directions, no ZOOM TARGET lines.

Apply the pronunciation table in `demo/SCRIPT.md` **by rewriting the words
themselves**, not by adding markup: "Yosys" becomes "YO-sis", "RTL" becomes
"R T L". Numbers are already written as words; if one is still in digits,
spell it out.

## Step 6. Dry-run the manifest before spending anything

Write `demo/audio/MANIFEST.tsv`, one row per beat: file, word count, expected
seconds at 150 wpm (from `tools/script_words.py`), and the **measured** duration
of that beat in the locked cut.

**Flag every beat whose expected seconds exceed its measured picture duration.
Fix the text, never the picture.** Re-check. Synthesize nothing until no beat is
flagged.

## Step 7. Synthesize Beat 4 alone, listen, then the rest

Beat 4 first, by itself. It is the strongest stretch in the video and it carries
the hardest pronunciations. Listen to it. If voice, pace or pronunciation is
wrong, fix the text and spend one more call on **Beat 4 only**, not on nine
beats.

Once Beat 4 is right, synthesize the remaining eight in **one pass**. Keep every
`.txt` beside its audio, so a later fix costs one beat and not the set.

## Step 8. Lay the voice under the picture

No re-cutting the picture to fit the voice. If a beat's audio overruns, the text
was wrong at step 6 and gets shortened there.

---

## Rules that hold in both phases

- **Do not invent a number.** Every figure spoken, and every ZOOM TARGET,
  appears in `REPORT.md` or `SUBMISSION_PACK.md`, which
  `tools/check_report_numbers.py` checks. Figures merely visible in raw terminal
  output must not contradict those documents (phase 1, step 4). If a number in `demo/SCRIPT.md` looks wrong,
  **report it, do not fix it silently.**
- **Do not extend the runtime.** Anything added comes out of something else, and
  `tools/script_words.py` is the arbiter, not a header.
- **Beat 4 is never cut.** It is the LLM proposal that passes the design's own
  shipped firmware and 20,000 random vectors and is formally refuted in 46
  seconds with a concrete counterexample.
- **Beat 5's second paragraph is never cut either.** It is the composed-RTL
  result: +5.165 ns before wires, **zero after the physical flow, inside the
  flow's own noise**, and the classifier having routed that path to buffering
  before any of it was measured. That is the report's headline negative result.
  **The video must not tell a cleaner story than the document.**
- **If the cut runs long, take it out of Beat 6 or Beat 8**, never Beat 4 and
  never Beat 5's second paragraph. `demo/SCRIPT.md`'s own edit notes say the
  same; if these two files ever disagree, `demo/SCRIPT.md` wins and this file
  is the one to fix.
- **Beat 2's screen contains no model call.** It is the v2 closed-loop run
  pulling the physical lever; "nobody steering it" refers to the loop. The
  unattended generative run is a different run, a different SDC and a different
  number. Do not let the edit merge them.
- **Retracted claims stay retracted.** Do not reinstate "no RTL rewrite shortens
  a net's load delay", the universal "every published optimizer" framing, or the
  55.805-over-4.925 ratio. `DEMO.md` and `demo/SCRIPT.md` carry the corrected
  wording and say why.
