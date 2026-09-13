#!/usr/bin/env python3
"""How long each screen of a beat stays up, derived from demo/SCRIPT.md.

demo/present.sh shows each beat as one or more screens (a command and its
output). A screen must stay up while the narration that refers to it is spoken,
so its hold time is the word count of those narration paragraphs at the
speaking rate. Nothing here is a typed duration: edit the narration and the
holds move with it.

    python3 demo/present_plan.py 5          # screen<TAB>seconds, then TOTAL
    python3 demo/present_plan.py all        # every beat, for a quick check

The mapping below says which narration paragraphs belong to which screen. It is
the one hand-written part, and it is checked: if a beat has fewer paragraphs
than the mapping names, the plan falls back to an even split and says so on
stderr instead of silently mistiming the take.
"""
import io
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HERE, "demo", "SCRIPT.md")
WPM = float(os.environ.get("WPM", 150))
MIN_SCREEN = float(os.environ.get("MIN_SCREEN", 6))    # s, so any screen is readable
MARGIN = float(os.environ.get("MARGIN", 0.5))          # s added to a beat's last screen

# screen name -> narration unit. ("p", a, b): paragraphs a..b, 1-based,
# inclusive. ("s", a, b): sentences a..b across the whole beat, b None = to the
# end. ("half", k): the k-th half of the beat's words, for a long output shown
# in two pages. Screens follow demo/SCRIPT.md's SCREEN line for each beat.
PLAN = {
    1: [("bench", ("p", 1, 1))],
    2: [("loop", ("p", 1, 1)), ("showrun", ("p", 2, 2))],
    3: [("final", ("p", 1, 3))],
    4: [("gitlog", ("p", 1, 2)), ("result", ("p", 3, 3)), ("trace", ("p", 4, 4))],
    5: [("lever", ("p", 1, 1)), ("post_repair", ("p", 2, 2)), ("ppa", ("p", 3, 3))],
    6: [("verdict", ("s", 1, 1)), ("classify", ("s", 2, None))],
    7: [("sdc", ("p", 1, 1))],
    8: [("page1", ("half", 1)), ("page2", ("half", 2))],
}


def paragraphs(beat):
    """Spoken paragraphs of one beat: '>' lines, split on a bare '>'."""
    out, cur, inside = [], [], False
    for line in io.open(SCRIPT, encoding="utf-8"):
        if line.startswith("## Beat") or line.startswith("## End"):
            inside = line[3:].split(".")[0].strip() == f"Beat {beat}"
            continue
        if line.startswith("## "):
            inside = False
        if not inside or not line.startswith(">"):
            continue
        text = line[1:].strip()
        if text:
            cur.append(text)
        elif cur:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def words(text):
    return len(text.split())


def plan(beat):
    paras = paragraphs(beat)
    total_words = sum(words(p) for p in paras)
    screens = PLAN[beat]
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(paras))
    need = max((u[2] for _, u in screens if u[0] == "p"), default=0)
    fallback = need > len(paras)
    if fallback:
        print(f"WARN beat {beat}: mapping names paragraph {need} but SCRIPT.md has "
              f"{len(paras)}; splitting evenly", file=sys.stderr)
    rows = []
    for name, unit in screens:
        if fallback:
            w = total_words / len(screens)
        elif unit[0] == "p":
            w = sum(words(p) for p in paras[unit[1] - 1:unit[2]])
        elif unit[0] == "s":
            end = unit[2] if unit[2] is not None else len(sentences)
            w = sum(words(s) for s in sentences[unit[1] - 1:end])
        else:
            w = total_words / 2
        rows.append([name, w / WPM * 60])
    # every screen readable: lift short ones to MIN_SCREEN, paid for by the
    # longest, so the beat's total never changes
    for r in rows:
        if r[1] < MIN_SCREEN:
            longest = max(rows, key=lambda x: x[1])
            if longest is not r:
                longest[1] -= MIN_SCREEN - r[1]
                r[1] = MIN_SCREEN
    floor = total_words / WPM * 60
    rows[-1][1] += MARGIN
    return rows, floor


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    beats = sorted(PLAN) if arg == "all" else [int(arg)]
    for b in beats:
        rows, floor = plan(b)
        for name, secs in rows:
            print(f"{name}\t{secs:.2f}" if arg != "all" else
                  f"beat {b}\t{name:<12}\t{secs:6.2f} s")
        take = sum(s for _, s in rows)
        print(f"TOTAL\t{take:.2f}" if arg != "all" else
              f"beat {b}\t{'TOTAL':<12}\t{take:6.2f} s   floor {floor:.2f} s,"
              f" take = floor + {MARGIN} s margin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
