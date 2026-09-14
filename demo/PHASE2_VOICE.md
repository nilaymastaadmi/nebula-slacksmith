# Phase 2, voice. State after the narration was laid under the locked cut.

Done 2026-09-14, branch `sandbox`, after the author signed off the duration table
in `demo/PHASE1_CUT.md`. Every number below is read back from a tool or a file.

**Final video: `%USERPROFILE%\Videos\slacksmith-demo\slacksmith_demo.mp4`**, 298.500 s,
1920x1080 30 fps H.264 (the silent cut's video stream, byte-identical: pts, size
and flags match on all 8,955 packets) plus mono 48 kHz AAC narration. Committed at the
repository root as `slacksmith_demo.mp4` on 2026-09-14; the silent cut stays out of the
repository.

## How it was made, in the order `demo/VIDEO_PROMPT.md` sets

| step | what ran | result |
|---|---|---|
| 5 | `tools/audio_text.py` | `demo/audio/beat0.txt` to `beat8.txt`, 719 words, no table spelling or digit left (guard checked on a planted sentence) |
| 6 | `tools/audio_text.py` | `MANIFEST.tsv`: every beat's 150 wpm estimate at or under its picture, none flagged |
| 7 | `tools/sarvam_tts.py 4` | Beat 4 alone, `bulbul:v3`, `rahul`, pace 1.0: 49.257 s on a 51.800 s picture. The author listened and approved voice, pace and pronunciation |
| 7 | `tools/sarvam_tts.py 0 1 2 3 5 6 7 8` | the other eight in one pass at pace 1.0 |
| 8 | `tools/lay_voice.py` | Beats 5, 6 and 8 did not fit their screens (see below); after re-synthesis every screen fits |

**Sarvam calls: 12.** Beat 4 once, the other eight once, then Beats 5, 6 and 8 once
more. No call failed or was retried.

**Beats 5, 6 and 8 at pace 1.0 overran their screens**, by 0.9 s (Beat 5's lever
screen), 2.4 s (Beat 6's classify screen) and 1.5 s (Beat 8). They were the slowest
reads, 138 to 145 wpm against 150 to 170 elsewhere. The author chose a faster pace
over trimming words, with the switch between beats kept seamless, so each got the
pace that brings it back to its neighbours' rate rather than the fastest that fits:

| beat | pace | audio | picture |
|---|---:|---:|---:|
| 0, 1, 2, 3, 4, 7 | 1.00 | as in `MANIFEST.tsv` | |
| 5 | 1.08 | 45.127 s | 48.967 s |
| 6 | 1.13 | 21.741 s | 24.200 s |
| 8 | 1.10 | 26.293 s | 27.000 s |

The minimum fitting paces, measured by time-compressing the pace-1.0 audio, were 1.05,
1.10 and 1.06. `demo/audio/beatN.json` records the text hash, voice, pace and model
of every WAV, and `sarvam_tts.py` refuses to call again for an unchanged beat.

## Laying the voice: screen by screen, not beat by beat

Laid as one file per beat, Beat 4's "forty-six seconds" paragraph would have been
heard 3.0 s before RESULT.md appears. So `tools/lay_voice.py` splits each beat at
the break before every paragraph and sentence, and places each screen's text at the
moment that screen appeared (`demo/takes/video/times/beatN.times`, copied from the
presenter's logs of the recorded takes).

- **Where the breaks are** comes from a local whisper.cpp transcript
  (`demo/audio/whisper/beatN.json`; model `ggml-base.en.bin`, SHA-1
  137c40403d78fd54d454da0f9bd998f78703390c, downloaded with the author's consent;
  Recordly's bundled `whisper-cli.exe`). Pause length alone failed: Beat 5's three
  screens' text reads at 206, 180 and 141 wpm of speech, so a rate-based guess put paragraph 3's
  start a sentence early.
- **Spare time is spread**, per the author: each screen's slack goes into its
  paragraph breaks (weight 1.0), real sentence breaks (0.6, only where the audio has
  at least 0.12 s of quiet) and, at half weight, its two edges, because the silence
  across a cut belongs to both screens.
- **A paragraph may start up to 0.75 s before its screen** when the screen is shorter
  than its text; the latest is Beat 5's PPA paragraph, 0.68 s early.
- **Loudness**: each beat's speech level is matched to the median (corrections
  -0.8 to +0.7 dB), then the mix is normalized in two passes: -16.7 LUFS integrated,
  -1.4 dBTP true peak.

Placement for every run is in `demo/audio/PLACEMENT.tsv`. Measured on the final mix:
speech from 0.15 s to 293.13 s (the end card starts at 293.50 s and is silent), the
silence across each beat cut 0.49 to 1.56 s, and no silence before the end card
longer than 1.56 s.

## For the author's ear

The whisper transcript is a weak judge: it heard Beat 4's approved "counterexample"
as "cultural example". These are the mismatches where a listener mishearing would
change the meaning, worth one listen each in the final video:

| beat | written | heard as |
|---|---|---|
| 0 | "So we made transforms typed" | "need" |
| 3 | "This log predates two fixes" | "creates" |
| 6 | "Every wrong log stays" | "long" |
| 7 | "One netlist, identical in every row" | "at least" |
| 8 | "a pair that's provably equivalent" | "probably" |

Beat 2 is the fastest read, 190 wpm of speech against 168 and 161 for Beats 1 and 3, at pace 1.0 with 1.30 s to spare on its screen. A slower pace on Beat 2 alone would
cost one call.

## Open

- `SUBMISSION_PACK.md` still says the demo video is pending, voice not added. That
  file belongs to the main session.
