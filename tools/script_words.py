#!/usr/bin/env python3
"""Count the spoken narration in demo/SCRIPT.md and fail above the ceiling.

Only lines that begin with '>' inside a '## Beat' section count; headings,
ZOOM TARGET notes and edit notes are not spoken. The ceiling is 750 words at
Sarvam's ~150 wpm for the organisers' 5-minute window; the target is under 700.

Why this exists: SCRIPT.md's header said "690 words" from 2026-09-11 while the
file held 983, 6.6 minutes at 150 wpm, because the count was written once and
never re-measured after two rounds of narration corrections. A written count
is a number no tool checks. exit 1 above the ceiling.

    python3 tools/script_words.py            # per-beat table and total
"""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(HERE, "demo", "SCRIPT.md")
CEILING, TARGET, WPM = 750, 700, 150

beat, per, total = None, {}, 0
for line in open(PATH, encoding="utf-8"):
    if line.startswith("## Beat") or line.startswith("## End"):
        beat = line[3:].split(".")[0].strip()
    elif line.startswith("## "):
        beat = None
    if beat and line.startswith(">"):
        n = len(line.lstrip("> ").split())
        per[beat] = per.get(beat, 0) + n
        total += n

for b, n in per.items():
    print(f"  {b:<8} {n:>4} words  ~{n / WPM * 60:>4.0f} s")
print(f"total {total} words, ~{total / WPM:.1f} min at {WPM} wpm; ceiling {CEILING}, target under {TARGET}")
if total > CEILING:
    print(f"FAIL: {total - CEILING} words over the ceiling"); sys.exit(1)
print("OK" if total < TARGET else "OK, but above the target")
