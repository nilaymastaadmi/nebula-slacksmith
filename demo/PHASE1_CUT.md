# Phase 1, picture. State and the per-beat duration table.

Measured 2026-09-12, branch `sandbox`. **No number in this file is typed by
hand.** The table regenerates from the script, the rendered cards and the real
captures:

    python3 tools/duration_table.py --write --width 165 --target 292

Decisions taken 2026-09-12, so later sessions do not reopen them:

| decision | value |
|---|---|
| runtime | **ship the floor.** No narration trim. It was 4:52 at 701 words; finding 11 moved it, and the generated block below carries the current value. |
| narration values | **use what is currently written.** Improvements are underway; the tooling updates itself, the script is not edited to chase a number. |
| recording width | **165 columns.** |
| Beat 2 | pre-run and play back, see finding 1. |
| Beats 1 and 6 | **also pre-run.** Measured 46.1 s and 583.0 s, see finding 8. |
| Beat 5 caveat | **added 2026-09-13**: 3.32x is now said with its flow-defect caveat (finding 10). |
| on-screen numbers | **read as "no invented or contradicting number"**, decided by the main session 2026-09-13 and written into `demo/VIDEO_PROMPT.md` step 4. Beat 3's two contradictions are flagged in its narration; findings 9 and 11. |
| Beat 2 playback | **disclosed in narration**: "under a minute" is now "replayed from file", finding 2. No narration line states or implies the loop's runtime. |
| Beat 3 | **two narration edits and a re-take**, 2026-09-13, approved by the author: the P4 verdict flag and the depth-side sentence, +17 words. Finding 11. |
| Beat 0 | **narrated from the title card's first frame**, 2026-09-13, so Beat 3's growth fits under 300 s. Only the card's 12-frame fade out is silent. |
| Beat 5, first zoom | **tightened below the `+4.925` row**, 2026-09-13, by re-exporting that one region; no re-take. Finding 11. |
| narration | **humanized 2026-09-13**, at the request of the author. Every paragraph kept its beat and position and none got longer, so the recorded takes still fit; every spoken figure, qualifier and retraction was checked mechanically before and after. |

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

## Step 3. Recordly, the screen. DONE.

Recorded 2026-09-13, one take per beat, in `DEMO.md` order. The final set is the
third full pass; the first two were discarded for a watcher bug and for
Recordly's own "Stop" tooltip showing in frame. Beat 3 was re-taken alone later
that day for finding 11.

How the takes were made, since an agent could not do it alone:

- **The author clicked Record and Stop.** The Claude computer-use indicator is a
  capturable screen-edge glow that appeared in every frame of every take the agent
  clicked (measured from the raw files), so the agent did not touch the screen
  during takes.
- **`demo/present.sh` played each beat** in a fullscreen Windows Terminal profile
  (`demo/terminal/slacksmith-demo.json`, 11 pt, 172 x 45), holding each screen for
  as long as `demo/present_plan.py` derives from the narration.
- **A background watcher triggered each take** on Recordly's native
  `wgc-capture.exe` helper starting, then checked every raw take for the edge glow
  and for Recordly's hover tooltip, re-arming a beat if either appeared. The first 8
  takes passed on the first try; the Beat 3 re-take was rejected twice for the
  tooltip (both rows in `demo/takes/video/rejected.tsv`) and passed on the third; an independent scan of 136 frames found neither,
  with the detector re-validated on known positive and negative frames.

The eight takes, with their trigger offsets, are in `demo/takes/video/takes.tsv`;
the assembly reads the last row per beat.

**The Beat 3 re-take's offset is measured from its frames, not from the watcher.**
The watcher takes a recording's start time from its filename. For the first eight
takes the file was created in the same second as that timestamp; for the re-take
it was created 2.1 s later, so the computed offset (4.553 s) was 2.7 s late. Read
from the raw frames instead: the command line appears at 1.817 s and the output at
1.867 s, so the row carries 1.917 s. The screen is static from 1.867 s to the end of
the take, so only the cut point moved, and Beat 3 now opens on the command line
with its output one frame later, as it did before.

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

`demo/SCRIPT.md` sha256 `0e1cb0a9570af191`, 10,449 bytes. 150 wpm. Recording terminal 165x40.

| beat | words | floor | zoom | cols | lines | measured | screen |
|---|---:|---:|:---:|---:|---:|---:|---|
| Beat 0 | 47 | 19 s |  |  |  |  | Remotion title card |
| Beat 1 | 45 | 18 s |  | 110 | 5 | 46.1 s | tools/bench_size.py |
| Beat 2 | 72 | 29 s | yes | **204** | 15 | 832.8 s | the loop, then show_run.py |
| Beat 3 | 116 | 46 s |  | 148 | 37 | 0.9 s | show_run.py on 3 committed logs |
| Beat 4 | 127 | 51 s | yes | 89 | 30 | 11.4 s | prereg + git log, then the table |
| Beat 5 | 121 | 48 s | yes | 83 | 7 | 0.3 s | lever table, post-repair, PPA |
| Beat 6 | 59 | 24 s |  | 85 | 29 | 583.0 s | verdict_regression, classify_regression |
| Beat 7 | 66 | 26 s | yes | 79 | 9 | 6.0 s | sdc_integrity/run.sh |
| Beat 8 | 66 | 26 s |  | 162 | **57** | 0.0 s | SlackBench table |
| **beats** | **719** | **288 s** | | | | | |

Title card 5.06 s probed, narrated from its first frame so only its 0.40 s fade out is silent; end card 5.06 s probed. **Floor runtime 293.1 s = 4:53**, window 3:00 to 5:00, 6.9 s slack to the cap.

**Silent cut, measured** from `demo/takes/video/cut_manifest.json`. Beat 0 is narrated from the title card's first frame: its screen time is the card's fade in and hold together, and only the fade out is silent.

| segment | measured | narration floor | spare | check |
|---|---:|---:|---:|:---:|
| Beat 0 narration over the title card, from its first frame | 18.800 s | 18.8 s | +0.00 s | pass |
| title card, fade out | 0.400 s | | | |
| Beat 1 (raw take, no zoom target) | 19.000 s | 18.0 s | +1.00 s | pass |
| Beat 2 (Recordly export, zoomed) | 29.767 s | 28.8 s | +0.97 s | pass |
| Beat 3 (raw take, no zoom target) | 46.600 s | 46.4 s | +0.20 s | pass |
| Beat 4 (Recordly export, zoomed) | 51.800 s | 50.8 s | +1.00 s | pass |
| Beat 5 (Recordly export, zoomed) | 48.967 s | 48.4 s | +0.57 s | pass |
| Beat 6 (raw take, no zoom target) | 24.200 s | 23.6 s | +0.60 s | pass |
| Beat 7 (Recordly export, zoomed) | 26.967 s | 26.4 s | +0.57 s | pass |
| Beat 8 (raw take, no zoom target) | 27.000 s | 26.4 s | +0.60 s | pass |
| end card | 5.000 s | | | |
| **silent cut** | **298.500 s = 4:58** | | +1.50 s to cap | pass |

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

One assembly ambiguity, worth 5 s, **now decided: Beat 0 is narrated from the
title card's first frame** (decision above). `demo/VIDEO_PROMPT.md` step 4 lists the
title card and Beat 0 as separate elements, while `demo/SCRIPT.md` gives Beat
0's screen as the title card. The table took the strict reading until finding 11: 5.06 s of
silent card, then Beat 0's 19 s narrated over the same held card, so the card is
on screen 24.1 s. Narrating Beat 0 from the first frame instead removes 5.06 s
and lands the floor at 4:47.

## The locked silent cut

**`%USERPROFILE%\Videos\slacksmith-demo\slacksmith_silent_cut.mp4`**, 298.500 s,
1920x1080, 30 fps, H.264, no audio. Kept out of the repository; the segments it is
joined from are in `segments\` beside it. The 296.700 s cut from before finding 11 is
kept beside it as `slacksmith_silent_cut_v1_296.7s.mp4`.

| layer | how it was made |
|---|---|
| title and end cards | Remotion, `demo/remotion/out/`. Beat 0 narrates from the title card's first frame: the card's own first 4.6 s (fade in and hold), then a held still of it, then its 0.4 s fade out. |
| beats 2, 4, 5, 7 | Recordly exports with manual zoom regions at 1.8x on each ZOOM TARGET. Every region is recorded in `demo/takes/video/zooms.tsv` (source, start, end, depth, target) so one beat can be re-edited without the others. Beat 5's first region was re-exported alone and spliced in at frame 597 (19.900 s), where zoom 1 has eased out and zoom 2 has not begun; see finding 11. |
| beats 1, 3, 6, 8 | No ZOOM TARGET, so cut straight from the raw Recordly takes. Measured first: a Recordly export of an unzoomed frame differs from the raw by a mean of 0.03 per channel (99th percentile 1), so the two routes are visually identical. |
| assembly | `ffmpeg` trim from each take's measured trigger offset minus 0.1 s, re-encoded to identical settings and joined with the concat demuxer. The per-segment durations above are read back from the output, not from the plan. |

Joins verified: the first frame of all 12 segments shows its intended content, with
no desktop, blank or stray frames.

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

**Resolved 2026-09-13, main session's wording.** "under a minute," is now "replayed
from file,", 3 words for 3. It is the only playback disclosure the narration needs:
beats 1 and 6 make no liveness or timing claim. `tools/script_words.py` still prints
701, so the table above is unchanged.

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

**9. The rule "no frame shows a number that is not in REPORT.md or
SUBMISSION_PACK.md" cannot hold for real terminal output, and it does not hold
here.** Audited from the exact text on each screen: **125 distinct numbers appear
on screen, and 61 of them are in neither document** (the audit file lists 62; one,
5.600, is 5.6 in the report). They are raw output of
committed files and tools (intermediate iteration slacks, per-row table cells,
fanout shares, cycle counts), so nothing is invented, and every spoken figure and
every ZOOM TARGET does trace to the documents. But `demo/VIDEO_PROMPT.md` step 4
says "no frame", and a real terminal cannot meet that literally. Either the rule
is read as "no invented or disagreeing number", which this cut meets, or the
screens need cropping to the numbers the report carries. That is a decision for
you, not a fix.

**Resolved 2026-09-13 by the main session: the rule means no invented number and no
number that contradicts the documents for the same quantity; absence is not a
finding.** Step 4 of `demo/VIDEO_PROMPT.md` now says so. Its check of all eight
screens found one contradiction, and this audit had missed it because it compared
numbers, not verdicts: beat 3's `run_v3_final` prints `clk_a: DEPTH_DOMINATED
(fanout share 0.0, 17.13 ns over 33 cells)`, while REPORT 7.2 and 9 carry that path
as MIXED and beat 6's own screen shows it at MIXED 0.4277. Checked here before
applying: the log was committed 2026-09-01 (`fd08ea1`) and the cross-module fanout
fix landed 2026-09-03 (`bb165ad`). No re-record: Beat 3 is one screen, so the flag is
spoken while the stale verdict is visible. "Proven means correct, not useful, so the
tool measures both separately." is now "This log predates our fanout fix; its depth
verdicts are wrong.", 11 words for 11; the first sentence already says all three
transforms are proven and make the number worse.

**10. Seven spoken figures never appear on their beat's screen, and one ZOOM
TARGET is never spoken.** Checked against the exact screen text:

| beat | spoken | on that beat's screen? |
|---|---|---|
| 3 | one point four one four nanoseconds | no, it is the unattended `cli_backend` run, not `run_v3_final` |
| 3 | four optimization classes | no |
| 5 | three point one eight five nanoseconds | no |
| 5 | minus eighteen point nine | no |
| 5 | twenty point two percent more area | no |
| 5 | forty-seven percent more power | no |
| 8 | forty thousand simulated cycles | no, the screen shows 19,997 and 19,998 per simulator |
| 5 | (not spoken) | **3.32x is a ZOOM TARGET, and `demo/SCRIPT.md` says to say it with a flow-defect caveat, but the narration never mentions it** |

This predates the humanizing pass: the facts and their beats are unchanged. It
weakens "point at one number and let the rest sit there", because the number being
said is often not the one being pointed at.

**Resolved in part, 2026-09-13, at the author's direction ("your call, if important
add to narration").** One mismatch crossed the line `demo/VIDEO_PROMPT.md` draws, that
the video must not tell a cleaner story than the document: Beat 5 zoomed onto
"3.32x achievable frequency" without the caveat REPORT section 9 carries. Beat 5's
third paragraph now says "Frequency rises three point three two times, partly our
flow defect." To fit the recorded 11.7 s PPA screen at the same 28 words, it gave up
"closure survives a clock tree and global routing", a positive claim, and kept both
costs (twenty point two percent area, forty-seven percent power). The other six
spoken-but-not-shown figures stay as narrated context. +55.805 stays unspoken on
purpose, so it cannot be heard as the retracted 55.805-over-4.925 ratio.

**11. Review 5 found a second retracted verdict on Beat 3's screen, and a story the
video did not tell.** Beat 3's `run_v3_final` screen ends with `it8 GATE P4
(mux_priority_to_parallel) ... G4=UNRESOLVED`; REPORT 7.3 retracts that verdict,
Beat 4 is P4's refutation, and Beat 6's screen says P4 "MUST read REFUTED". The
flag from finding 9 named the fanout fix only. Separately, REPORT 7.8 now says that
on both designs where the classifier routed to RTL unforced (i2c and tv80), four
proven transforms bought 0.000, 0.000, -0.268 and -0.421 ns, and the video never
said so. Both checked against REPORT.md before editing.

**Resolved 2026-09-13, main session's wording, re-take approved by the author.**
Beat 3's flag is now "This log predates two fixes; its depth and P four verdicts are
wrong." (13 words for 11), and its last sentence is "Where the router picked R T L
itself, on two designs, no proven transform helped." (15 words).
`tools/script_words.py` prints 718. Beat 3 was re-taken at its new 46.5 s hold, and
Beat 0 now narrates from the title card's first frame to pay for it.

Beat 5's first zoom landed on `+55.805` two rows below `+4.925`, the retracted
cross-regime pair magnified together. Tightened without a re-take: on the lever
screen the `+4.925` row occupies pixel rows 140 to 158 and the `+17.557` row starts at
161, a 3-pixel gap too narrow to hit by dragging. So the region was saved as a
Recordly project and its focus set numerically (`cx 0.27931`, the old zoom's measured
horizontal framing; `cy 0.425926`, top edge at pixel 160), then exported alone and
spliced losslessly into the old export at frame 597. Checked: the zoomed frame shows
only the `+17.557` and `+55.805` rows; the new and old exports are pixel-identical
before the zoom (mean difference 0.000) and at the splice (0.03 to 0.12); frames
150, 610 and 1500 of the spliced file match their sources exactly while their
neighbours differ; Beat 5's segment length is unchanged at 48.967 s.

**12. Contradiction check by eye, all eight beats, against REPORT.md and
SUBMISSION_PACK.md at `f4e58fc`.** `demo/takes/video/onscreen_numbers_audit.txt` is
regenerated: 125 distinct numbers on screen, 61 in neither document (5.600 is
REPORT's 5.6; `1.184` now matches REPORT section 8). None of the files the screens
show changed after the takes were recorded. Each screen value was then compared
with what the documents state for the same quantity, verdicts and labels included.

- **Beats 1, 2, 4, 6, 7, 8: no contradiction.** Beat 2's `set_false_path: 1` now
  matches REPORT section 4's reset false path. Beat 6's `0.2864` is v3's `clk_e`
  path; REPORT's 34.4% is case 4 in `docs/path-classification.md` (`clk_b`, v2
  periods / 6), a different path. Beat 8's confusion matrix, recomputed from
  `raw.tsv`, equals REPORT section 7.4 cell for cell.
- **Beat 3: the two retracted verdicts are flagged (finding 11).** One residual,
  not a contradiction of a REPORT figure: the screen shows four PROVEN transforms,
  P1, P2, P3 reverted and P6 applied provisionally, and the log ends there (27
  records, the last an `apply`). The narration says "All three transforms here".
  REPORT section 7.3 describes the run as P1 to P3. P2's on-screen change, -0.485,
  is the buffered value REPORT states; REPORT's P table (-1.555, -2.102, -1.615) is
  the unbuffered batch, so it does not describe this run.
- **Beat 5: one label disagreement.** `experiments/ppa/fmax/results/table.md` names
  the after-row capture clock `clk_b` at a 79.500 ns period; REPORT section 8 names
  it `clk_b_div3`, which the period confirms (3 x 26.500). It is visible inside the
  3.32x zoom region and not spoken.
- **Spoken figures: all trace except one.** Beat 6's "sat in every log for three
  days" is in neither document; it came from `DEMO.md`. The commits give 51.5 hours:
  6.762 first appears in `fb572f5` (2026-08-31 23:26) and the fix is `bb165ad`
  (2026-09-03 02:56).
- **Document to document, not on screen:** REPORT section 1 says binding paths are
  59% to 91% fanout-attributable; SUBMISSION_PACK D3 says 58.9% to 98.95%.

**Resolved 2026-09-13, main session `54ceb88`.** Beat 6 now says "two days", word for
word; SUBMISSION_PACK carries the 51.5 h and `DEMO.md` line 256 already said two days.
Beat 3 now opens "The first three transforms here", +1 word, so
`tools/script_words.py` prints 719; Beat 3's floor rises to 46.4 s against its 46.6 s
segment, so no re-take. The `clk_b` label is stated in SUBMISSION_PACK D5, with no screen
or REPORT change, and PACK D3 now scopes 58.9% and 91.4% (targets) against 98.95% (the
same path after O1).

## Verifications that came back clean

- **Every number the video says, and every ZOOM TARGET, traces to `REPORT.md` or
  `SUBMISSION_PACK.md`.** Numbers only shown on screen are finding 9. 24 spelled-out spoken figures and 6 digit-numbers in
  the ZOOM TARGET lines, all found. "minus eighteen point nine" is a spoken
  rounding of 18.957, which is in the report.
- `tools/check_report_numbers.py`: 218 numbers checked, 0 unsupported.
- **All four retracted claims are absent from spoken narration**: the "no RTL
  rewrite shortens a net's load delay" absolute, the universal "every published
  optimizer" framing, the 55.805-over-4.925 ratio, and beat 7's withdrawn
  comparison to the best proven RTL transform.
- Beat 4 is intact at 127 words, and Beat 5's composed-RTL paragraph is present.
- Beat 5's headline negative is real on screen: `repair_composed` `clk_b` 5.046
  against `repair_gold` 5.283 is the -0.237 behind the narration's "zero, within
  the flow's own noise", and the ABC
  pair shows `+0.000` on `clk_b`.

## Phase 2 gate, met 2026-09-14

No audio was generated. No Sarvam call was made. Findings 2, 9, 10 and 11 are
resolved in the narration, and finding 12's items are proposals for the main session; finding 11 also re-took Beat 3 and re-cut Beat 5's first
zoom. Phase 2 starts only when all of these hold:

- the Beat 3 re-take is in the cut: done, `recording-1789314137904.mp4`;
- `tools/script_words.py` prints 719: done (718 after finding 11, 719 after finding 12);
- the cut measures at or under 300.0 s: done, 298.500 s;
- the author has signed off the regenerated duration table above: **signed off 2026-09-14**.

Then Beat 4 first, alone, and the hex witness is not spoken.
