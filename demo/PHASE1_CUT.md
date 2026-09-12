# Phase 1, picture. State and the per-beat duration table.

Measured 2026-09-12, branch `sandbox`. **No number in this file is typed by
hand.** The table regenerates from the script, the rendered cards and the real
captures:

    python3 tools/duration_table.py --write --width 165 --target 292

Decisions taken 2026-09-12, so later sessions do not reopen them:

| decision | value |
|---|---|
| runtime | **ship the 4:52 floor.** No narration trim. |
| narration values | **use what is currently written.** Improvements are underway; the tooling updates itself, the script is not edited to chase a number. |
| recording width | **165 columns.** |
| Beat 2 | pre-run and play back, see finding 1. |
| Beats 1 and 6 | **also pre-run.** Measured 46.1 s and 583.0 s, see finding 8. |

A parallel session is committing to this repository. The generated block carries
`demo/SCRIPT.md`'s fingerprint; if it no longer matches the file, the table is
stale and must be regenerated before it is signed off.

---

## Step 1. The demo still runs

    bash tools/preflight.sh     # all present, exit 0
    bash tools/demo_check.sh    # 15 pass, 0 fail, exit 0

`demo_check` wall clock 8 min 51 s (10:29:01 to 10:37:52 UTC). **15 pass, 0
fail** is the measured count from this run, not from any document. Preflight
found all 8 required tools, both optional OpenROAD paths, all 4 fixtures, git
history present, and no credential-shaped string in a tracked file.

## Step 2. Remotion, two cards, nothing else

`demo/remotion/` holds exactly two compositions, `Title` and `End`. No lower
thirds, no callout graphics: every ZOOM TARGET is reached with Recordly's
cursor zoom on the real terminal.

- 1920x1080, 30 fps, 150 frames each, which is 5.000 s of frames.
- Ground `#101214`, one accent `#c08b2c`, body `#e9e6e0`.
- Georgia / Times serif, the same family `tools/render_report.py` sets for
  `REPORT.html`, so the cards and the document read as one artefact.
- Animation is a fade only, 12 frames in and 12 frames out.
- Card text is copied from `SUBMISSION_PACK.md` lines 1 to 7 and lives in one
  file, `src/facts.ts`, so a name or URL is never retyped from memory.

Build:

    REMOTION_BROWSER="C:\Program Files\Google\Chrome\Application\chrome.exe" \
      npm run cards --prefix demo/remotion

`REMOTION_BROWSER` exists because Remotion's own Chrome Headless Shell download
stalled here (`storage.googleapis.com` sent no data for 20 s). The variable
points it at an installed Chrome instead. Unset, Remotion behaves as normal.

## Step 3. Recordly, the screen. NOT DONE.

Recordly is `github.com/webadderallorg/recordly`: an open-source Electron
desktop recorder and editor, AGPL, 27,108 stars, latest release v1.4.0
(2026-09-08), with Windows builds. It has `electron-builder.json5`, an
`electron/` tree and a Vite entry point, and **no CLI and no headless mode**.

It is not installed here. Two things stand between this session and the takes,
and only the first is hard:

1. **Typing into a terminal is blocked.** In this environment terminals are
   granted click-only access for computer use: clicks and scrolling are
   allowed, typing and key presses are not. Driving the beats by hand is
   therefore out.
2. **The cursor zooms are a GUI edit.** Recordly's zooms are placed in its
   editor after capture, which means clicking through a desktop app.

The first is avoidable and should not be reported as a wall. A presenter script
that plays the nine beats with pauses needs no typing at all: launch the
terminal with the script as its command, and the screen shows the beats on its
own. That leaves installing the app and hand-placing 7 zooms in its editor,
which is a long and fragile chain to drive through screenshots but is not
impossible. It also needs an explicit decision to download and install a
desktop application, which is yours to give, not mine to assume.

So the takes are blocked on a choice, not on a missing dependency. The fastest
path is still a person at the keyboard; the automatable path exists and costs
more.

What is prepared so the recording session is deterministic:

**`demo/takes/` holds the real output of every beat**, captured 2026-09-12 by
running each command exactly as `DEMO.md` writes it. No command was altered.
Three uses: the reference for what each screen must show, the playback file for
beat 2, and the width and height budget for the terminal. The `cols`, `lines`
and `measured` columns of the table below are read from these files, so the
table tracks them.

Recording checklist, derived from the measurements below:

1. Terminal at **165 columns**, 40 rows or taller.
2. `rm -rf ~/demo_run` first, or beat 2's replay shows the run twice (finding 3).
   Measured: `beat2_showrun.txt` is 16 lines with a stale workdir and 8 lines
   with a clean one.
3. **Beats 1, 2 and 6 play back from `demo/takes/`**, and say so on camera.
   Live they are 46.1 s, 832.8 s and 583.0 s (finding 8). Beats 3, 4, 5, 7 and
   8 are genuinely fast, 0.03 s to 11.4 s, and can run on camera.
4. Beat 8 is 57 lines, so that shot scrolls or zooms; it is not one static screen.
5. Beat 2's `show_run` has one 204-column line, the `g0_sdc` sha256. It is not a
   ZOOM TARGET, so let it scroll past rather than shrinking the font for it.
6. Cursor-zoom only on the ZOOM TARGETs listed by `tools/duration_table.py`.

## Step 4. The per-beat duration table

Narration floor is `words / 150 wpm`. A beat's screen time may not be shorter
than its floor, or the narration will not fit without speeding it up. `cols`,
`lines` and `measured` come from the real captures in `demo/takes/`, so a step
that gets faster or an output that gets wider changes this table by itself. A
bold value exceeds the recording terminal.

<!-- BEGIN generated -->

`demo/SCRIPT.md` sha256 `df4c70096e7fc97b`, 10,136 bytes. 150 wpm. Recording terminal 165x40.

| beat | words | floor | zoom | cols | lines | measured | screen |
|---|---:|---:|:---:|---:|---:|---:|---|
| Beat 0 | 47 | 19 s |  |  |  |  | Remotion title card |
| Beat 1 | 46 | 18 s |  | 110 | 5 | 46.1 s | tools/bench_size.py |
| Beat 2 | 73 | 29 s | yes | **204** | 15 | 832.8 s | the loop, then show_run.py |
| Beat 3 | 99 | 40 s |  | 148 | 37 | 0.9 s | show_run.py on 3 committed logs |
| Beat 4 | 128 | 51 s | yes | 89 | 30 | 11.4 s | prereg + git log, then the table |
| Beat 5 | 121 | 48 s | yes | 83 | 7 | 0.3 s | lever table, post-repair, PPA |
| Beat 6 | 59 | 24 s |  | 85 | 29 | 583.0 s | verdict_regression, classify_regression |
| Beat 7 | 66 | 26 s | yes | 79 | 9 | 6.0 s | sdc_integrity/run.sh |
| Beat 8 | 66 | 26 s |  | 162 | **57** | 0.0 s | SlackBench table |
| **beats** | **705** | **282 s** | | | | | |

Title card 5.06 s probed, end card 5.06 s probed. **Floor runtime 292.1 s = 4:52**, window 3:00 to 5:00, 7.9 s slack to the cap.
Target 4:52 needs 0 s out, which is 0 words, from Beat 6 or Beat 8 and never from Beat 4 or Beat 5's second paragraph.

<!-- END generated -->

Assembly is the title card, Beat 0 to Beat 8, then the end card. The floor sits
inside the organisers' 180 s to 300 s window, and the slack to the cap is the
entire budget for transitions and for holding each ZOOM TARGET, so the cut is
close to the ceiling by construction rather than by accident.

Per the decision above the floor ships as it is. If that changes, both governing
files agree the words come out of Beat 6 or Beat 8 and never out of Beat 4 or
Beat 5's second paragraph. Beat 6 and Beat 8 hold 125 words between them, so
`--target 282` (4:42) and `--target 270` (4:30) are the practical range, and the
tool prints the word count to cut for any target given to it.

One assembly ambiguity, worth 5 s. `demo/VIDEO_PROMPT.md` step 4 lists the
title card and Beat 0 as separate elements, while `demo/SCRIPT.md` gives Beat
0's screen as the title card. The table takes the strict reading: 5.06 s of
silent card, then Beat 0's 19 s narrated over the same held card, so the card is
on screen 24.1 s. Narrating Beat 0 from the first frame instead removes 5.06 s
and lands the floor at 4:47.

---

## Findings. None of these were fixed silently.

**1. Beat 2's live compute is not under a minute.** `DEMO.md` says "48 to 50 s
across two runs on 2026-09-03", `demo/VIDEO_PROMPT.md` says "about 45 seconds",
`demo/README.md` says "about a minute". Measured twice today on this machine:
**93.88 s** inside `demo_check`, and **367.8 s** when run as `DEMO.md` writes
the command. The larger number is longer than the whole video. Recording beat 2
live is not viable; `demo/VIDEO_PROMPT.md` already sanctions the alternative,
which is to pre-run it and say so on camera. `demo/takes/beat2_loop.txt` is
that playback file. The measured figure is now an input to the duration table,
so when the improvements underway land, re-run the capture and the table moves
by itself.

**2. `demo/SCRIPT.md` line 74 says "Under a minute, nobody steering it."** With
both of today's measurements that sentence is false as spoken. Reporting, not
editing: the narration is yours, the decision above is to keep what is written,
and a replacement of the same length would keep the duration table valid.

**3. `~/demo_run` accumulates across runs.** After today's capture,
`~/demo_run/decisions.jsonl` held 12 records with **2** `g0_sdc` markers, so
`tools/show_run.py` replayed the same run twice. On camera that is a visible
duplicate. `rm -rf ~/demo_run` before recording beat 2. `demo_check` does not
hit this because it uses a fresh per-PID workdir.

**4. 110 columns is not enough; 165 is.** The rule in both governing files is
"terminal at 110 columns or wider, or the classify lines wrap". The line it
protects is 97 columns, so 110 is right for that one. Measured across all beats,
four captures exceed it: beat 2's `show_run` at **204** (the `g0_sdc` line
carrying the full sha256), beat 3's `run_v3_final` at **148**, beat 3's
`run_v3_fixed` at **111**, and beat 8's table at **162**. Beat 1 sits exactly at
110 with no margin. At the chosen 165 columns everything fits except the
`g0_sdc` line, which is not a ZOOM TARGET. Beat 8 is also **57 lines**, which
exceeds a normal terminal height, so that shot needs a scroll or a zoom rather
than one static screen.

**5. `DEMO.md` beat 5's flatten command prints nothing.** As written:

    grep -E "^(A|C) " experiments/flatten_control/results/summary.tsv | cut -f1,5,7

`summary.tsv` is tab separated (`A<TAB>False<TAB>...`), so `^(A|C)` followed by
a space matches zero lines and the command outputs 0 bytes. Two defects, not
one: with the separator corrected, `cut -f1,5,7` selects arm, clock and
**verdict**, while the +22.4 ns claim lives in the **slack** column, which is
field 6. The underlying result is sound and was verified independently: arm A
`clk_a` is -13.167 and arm C is +9.279, a difference of **+22.446 ns**. Only the
command is wrong. Not fixed, because `DEMO.md`'s commands are yours.
`tools/duration_table.py` now reports any capture that produced no output, so
this class of defect surfaces from the tooling rather than from a reading.

**6. `tools/demo_check.sh` does not check beat 5.** It covers beats 1, 2, 3, 4,
6, 7 and 8 plus the explorer build and the classifier regression. `DEMO.md` says
of it "Runs every command in this file", which is not true today, and finding 5
is the cost: a beat-5 command has been printing nothing and the check still
reported 15 pass, 0 fail. A pass count answers whether what ran succeeded, never
whether everything ran.

**7. `tools/script_words.py`'s 750-word ceiling does not subtract the cards.**
750 words is 300 s of narration, which is the whole 5:00 window, leaving nothing
for the two 5 s cards that `demo/VIDEO_PROMPT.md` mandates. A script at the
ceiling would cut to 5:10 and breach the organisers' cap. The ceiling the cards
leave is **725 words**. The script is at 705, so it passes either way, with 20
words of margin against the corrected ceiling rather than 45.

**8. Beat 2 is not the only live compute, and the total is 30x what `DEMO.md`
says.** `DEMO.md` states "Total live compute in the demo is about 50 seconds
(beat 2). Everything else is either instant or replayed from a committed log",
and `demo/VIDEO_PROMPT.md` repeats "Beat 2 is the only live compute". Measured
per beat by `tools/capture_takes.sh`:

| beat | measured | instant? |
|---|---:|---|
| 1 | 46.1 s | no |
| 2 | 832.8 s | no |
| 3 | 0.9 s | yes |
| 4 | 11.4 s | yes |
| 5 | 0.3 s | yes |
| 6 | **583.0 s** | no |
| 7 | 6.0 s | yes |
| 8 | 0.03 s | yes |
| **total** | **1,480.5 s = 24.7 min** | |

Beat 6 runs `tools/verdict_regression.sh`, which invokes EQY, so it is live
formal compute and not a replay. Beat 1 decompresses and counts a netlist
fixture. Three beats need pre-running, not one, and the checklist above says so.

Beat 2's spread across three samples today is **93.88 s, 367.8 s and 832.8 s**,
an 8.9x range on one machine with one command. Whatever the cause, that is not
a number any document should assert, and it is now measured into the table
instead.

## Verifications that came back clean

- **Every number the video says or shows traces to `REPORT.md` or
  `SUBMISSION_PACK.md`.** 24 spelled-out spoken figures and 6 digit-numbers in
  the ZOOM TARGET lines, all found. "minus eighteen point nine" is a spoken
  rounding of 18.957, which is in the report.
- `tools/check_report_numbers.py`: 218 numbers checked, 0 unsupported.
- **All four retracted claims are absent from spoken narration**: the "no RTL
  rewrite shortens a net's load delay" absolute, the universal "every published
  optimizer" framing, the 55.805-over-4.925 ratio, and beat 7's withdrawn
  comparison to the best proven RTL transform.
- Beat 4 is intact at 128 words, and Beat 5's composed-RTL paragraph is present.
- Beat 5's headline negative is real on screen: `repair_composed` `clk_b` 5.046
  against `repair_gold` 5.283 is the -0.237 the narration states, and the ABC
  pair shows `+0.000` on `clk_b`.

## Phase 2 does not start yet

No audio was generated. No Sarvam call was made. Phase 2 needs a locked silent
cut and this table signed off, and the cut needs the takes from step 3.
