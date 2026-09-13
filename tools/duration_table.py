#!/usr/bin/env python3
"""Emit the phase-1 per-beat duration table for the demo video.

Every number is derived at run time. Nothing is typed in:

  - per-beat narration length comes from demo/SCRIPT.md by the same rule
    tools/script_words.py uses (lines beginning '>' inside a '## Beat');
  - the two card durations are *probed* from the rendered files with ffprobe,
    not assumed to be 5 s because a document says 5 s;
  - each beat's screen width, height and measured wall-clock come from the real
    captures in demo/takes/, so a step that gets faster or an output that gets
    wider updates the table by itself;
  - the window, the speaking rate and the terminal geometry are flags.

Why it is a script and not a table in a Markdown file: this repository already
learned that a written word count goes stale (tools/script_words.py explains
it). A written *duration* goes stale the same way, and three files here gave
three different figures for beat 2's live compute (DEMO.md "48 to 50 s",
demo/VIDEO_PROMPT.md "about 45 seconds", demo/README.md "about a minute") while
it measured 93.88 s and 367.8 s on 2026-09-12. A written *width* went stale the
same way: "110 columns or wider" protects a 97-column line and is 52 columns
short of beat 8's table. A duration and a geometry are measurements and need
the same treatment as a result.

    python3 tools/duration_table.py                 # the table
    python3 tools/duration_table.py --markdown      # as a Markdown block
    python3 tools/duration_table.py --write         # inject into demo/PHASE1_CUT.md
    python3 tools/duration_table.py --width 205 --target 282
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HERE, "demo", "SCRIPT.md")
OUT = os.path.join(HERE, "demo", "remotion", "out")
TAKES = os.path.join(HERE, "demo", "takes")
DOC = os.path.join(HERE, "demo", "PHASE1_CUT.md")
FFPROBE = os.path.join(
    HERE, "demo", "remotion", "node_modules", "@remotion",
    "compositor-win32-x64-msvc", "ffprobe.exe",
)
BEGIN, END = "<!-- BEGIN generated -->", "<!-- END generated -->"

# Defaults, all overridable: the narration is under revision, the recording
# width was already wrong once, and the runtime target is a judgement call.
WPM = 150
WINDOW_LO, WINDOW_HI = 180.0, 300.0   # the organisers' 3:00 to 5:00
WIDTH, HEIGHT = 165, 40               # recording terminal, columns and rows

# What each beat shows, for the take sheet. The commands themselves live in
# DEMO.md and are not duplicated here; this is only the label.
SCREENS = {
    "Beat 0": "Remotion title card",
    "Beat 1": "tools/bench_size.py",
    "Beat 2": "the loop, then show_run.py",
    "Beat 3": "show_run.py on 3 committed logs",
    "Beat 4": "prereg + git log, then the table",
    "Beat 5": "lever table, post-repair, PPA",
    "Beat 6": "verdict_regression, classify_regression",
    "Beat 7": "sdc_integrity/run.sh",
    "Beat 8": "SlackBench table",
}


def per_beat_words(path):
    """Word count per beat: exactly tools/script_words.py's rule."""
    beat, per = None, {}
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("## Beat") or line.startswith("## End"):
            beat = line[3:].split(".")[0].strip()
            per.setdefault(beat, 0)
        elif line.startswith("## "):
            beat = None
        if beat and line.startswith(">"):
            per[beat] += len(line.lstrip("> ").split())
    return per


def zoom_paragraphs(path):
    """The ZOOM TARGET paragraph for each beat, verbatim.

    Deliberately NOT a count. A first version counted backtick-quoted spans on
    the 'ZOOM TARGET' line and reported 6 targets where there are 7: beat 5's
    targets run onto continuation lines, and one backticked span in that same
    paragraph ('buffer; upsize') is an editorial note rather than a target. A
    number that is quietly wrong is worse than text a human reads.
    """
    beat, per, collecting = None, {}, False
    for line in io.open(path, encoding="utf-8"):
        if line.startswith("## Beat") or line.startswith("## End"):
            beat = line[3:].split(".")[0].strip()
            per.setdefault(beat, [])
            collecting = False
        elif line.startswith("## "):
            beat, collecting = None, False
        if beat is None:
            continue
        if "ZOOM TARGET" in line:
            collecting = True
        elif collecting and not line.strip():
            collecting = False
        if collecting:
            per[beat].append(line.rstrip())
    return per


def takes():
    """Measured geometry and wall-clock of the real captures, per beat.

    Returns {beat: {"files": [(name, cols, lines)], "seconds": float|None}}.
    Absent captures are not an error: the table still reports the narration
    floor, and says the screens have not been measured.
    """
    out = {}
    if not os.path.isdir(TAKES):
        return out
    for name in sorted(os.listdir(TAKES)):
        m = re.match(r"beat(\d+)", name)
        if not m or not name.endswith(".txt"):
            continue
        beat = f"Beat {int(m.group(1))}"
        rec = out.setdefault(beat, {"files": [], "seconds": None})
        path = os.path.join(TAKES, name)
        text = io.open(path, encoding="utf-8", errors="replace").read()
        if name.endswith("_timing.txt"):
            hit = re.search(r"=\s*([0-9.]+)", text)
            if hit:
                rec["seconds"] = float(hit.group(1))
            continue
        lines = text.splitlines()
        cols = max((len(l) for l in lines), default=0)
        rec["files"].append((name, cols, len(lines)))
    return out


def probe_seconds(mp4):
    """Real duration of a rendered card. None if it cannot be probed."""
    if not (os.path.exists(FFPROBE) and os.path.exists(mp4)):
        return None
    try:
        raw = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "json", mp4],
            capture_output=True, text=True, timeout=60,
        ).stdout
        return float(json.loads(raw)["format"]["duration"])
    except Exception:
        return None


def mmss(s):
    return f"{int(s) // 60}:{int(round(s)) % 60:02d}"


def build(args):
    """Compute everything. Returns a dict; no printing, so --markdown and the
    plain report cannot disagree with each other."""
    words = per_beat_words(SCRIPT)
    zooms = zoom_paragraphs(SCRIPT)
    tk = takes()
    beats = sorted((b for b in words if b.startswith("Beat")),
                   key=lambda b: int(b.split()[1]))
    rows, narration = [], 0.0
    for b in beats:
        secs = words[b] / args.wpm * 60
        narration += secs
        rec = tk.get(b, {"files": [], "seconds": None})
        widest = max((c for _, c, _ in rec["files"]), default=0)
        tallest = max((l for _, _, l in rec["files"]), default=0)
        rows.append({
            "beat": b, "words": words[b], "floor": secs,
            "zoom": bool(zooms.get(b)), "screen": SCREENS.get(b, ""),
            "cols": widest, "lines": tallest, "measured": rec["seconds"],
            "files": rec["files"],
        })
    title = probe_seconds(os.path.join(OUT, "title.mp4"))
    end = probe_seconds(os.path.join(OUT, "end.mp4"))
    cards = None if title is None or end is None else title + end
    digest = hashlib.sha256(io.open(SCRIPT, "rb").read()).hexdigest()[:16]
    return {
        "rows": rows, "narration": narration, "title": title, "end": end,
        "cards": cards, "digest": digest, "bytes": os.path.getsize(SCRIPT),
        "zooms": zooms, "beats": beats,
        "floor": None if cards is None else narration + cards,
    }


def markdown(d, args):
    L = [BEGIN, ""]
    L.append(f"`demo/SCRIPT.md` sha256 `{d['digest']}`, {d['bytes']:,} bytes. "
             f"{args.wpm} wpm. Recording terminal {args.width}x{args.height}.")
    L.append("")
    L.append("| beat | words | floor | zoom | cols | lines | measured | screen |")
    L.append("|---|---:|---:|:---:|---:|---:|---:|---|")
    for r in d["rows"]:
        over = r["cols"] > args.width
        cols = f"**{r['cols']}**" if over else (r["cols"] or "")
        tall = f"**{r['lines']}**" if r["lines"] > args.height else (r["lines"] or "")
        meas = f"{r['measured']:.1f} s" if r["measured"] else ""
        L.append(f"| {r['beat']} | {r['words']} | {r['floor']:.0f} s | "
                 f"{'yes' if r['zoom'] else ''} | {cols} | {tall} | {meas} | "
                 f"{r['screen']} |")
    tw = sum(r["words"] for r in d["rows"])
    L.append(f"| **beats** | **{tw}** | **{d['narration']:.0f} s** | | | | | |")
    L.append("")
    if d["cards"] is None:
        L.append("Cards not probed, so no total. Render them and re-run.")
    else:
        L.append(f"Title card {d['title']:.2f} s probed, end card "
                 f"{d['end']:.2f} s probed. "
                 f"**Floor runtime {d['floor']:.1f} s = {mmss(d['floor'])}**, "
                 f"window {mmss(WINDOW_LO)} to {mmss(WINDOW_HI)}, "
                 f"{WINDOW_HI - d['floor']:.1f} s slack to the cap.")
        if args.target:
            delta = d["floor"] - args.target
            if delta > 0:
                L.append(f"Target {mmss(args.target)} needs "
                         f"{delta:.0f} s out, which is "
                         f"{round(delta * args.wpm / 60)} words, from Beat 6 or "
                         f"Beat 8 and never from Beat 4 or Beat 5's second "
                         f"paragraph.")
            else:
                L.append(f"Target {mmss(args.target)} is already met with "
                         f"{-delta:.0f} s to spare.")
    L += cut_markdown(d)
    L += ["", END]
    return "\n".join(L)


def cut_markdown(d):
    """The locked silent cut, measured: every segment's real duration from the
    manifest the assembly step writes, against the narration floor for its beat.
    Absent until a cut exists; nothing here is estimated."""
    man_path = os.path.join(HERE, "demo", "takes", "video", "cut_manifest.json")
    if not os.path.exists(man_path):
        return []
    man = json.load(io.open(man_path, encoding="utf-8"))
    floors = {r["beat"]: r["floor"] for r in d["rows"]}
    L = ["", "**Silent cut, measured** from `demo/takes/video/cut_manifest.json`. "
         "Screen time for Beat 0 is the held title card only, excluding its fade in and out.", "",
         "| segment | measured | narration floor | spare | check |",
         "|---|---:|---:|---:|:---:|"]
    for label, name, secs, _cum in man["rows"]:
        beat = None
        if name.startswith("00b"):
            beat = "Beat 0"
        elif name[:2].isdigit() and name[:2] not in ("00", "99"):
            beat = f"Beat {int(name[:2])}"
        if beat:
            fl = floors[beat]
            ok = "pass" if secs + 1e-6 >= fl else "**FAIL**"
            L.append(f"| {label} | {secs:.3f} s | {fl:.1f} s | {secs - fl:+.2f} s | {ok} |")
        else:
            L.append(f"| {label} | {secs:.3f} s | | | |")
    total = man["cut"]
    within = WINDOW_LO <= total <= WINDOW_HI
    L += [f"| **silent cut** | **{total:.3f} s = {mmss(total)}** | | "
          f"{WINDOW_HI - total:+.2f} s to cap | {'pass' if within else '**FAIL**'} |"]
    return L


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--wpm", type=int, default=WPM)
    p.add_argument("--width", type=int, default=WIDTH,
                   help="recording terminal columns (default %(default)s)")
    p.add_argument("--height", type=int, default=HEIGHT,
                   help="recording terminal rows (default %(default)s)")
    p.add_argument("--target", type=float, default=None,
                   help="runtime target in seconds; prints the words to cut")
    p.add_argument("--markdown", action="store_true")
    p.add_argument("--write", action="store_true",
                   help=f"inject the Markdown block into {os.path.basename(DOC)}")
    args = p.parse_args()

    d = build(args)

    if args.markdown or args.write:
        block = markdown(d, args)
        if not args.write:
            print(block)
            return 0
        doc = io.open(DOC, encoding="utf-8").read()
        if BEGIN not in doc or END not in doc:
            print(f"FAIL: {DOC} has no {BEGIN} / {END} markers to write between")
            return 1
        new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block,
                     doc, flags=re.S)
        io.open(DOC, "w", encoding="utf-8", newline="\n").write(new)
        print(f"wrote the generated block into {os.path.relpath(DOC, HERE)}")
        return 0

    print("per-beat duration table, phase 1")
    print(f"demo/SCRIPT.md sha256 {d['digest']}   {d['bytes']:,} bytes")
    print(f"narration floor = words / {args.wpm} wpm. A beat's screen time may "
          "not be shorter than its narration.")
    print(f"recording terminal {args.width}x{args.height} columns x rows\n")
    print(f"  {'beat':<8} {'words':>6} {'floor':>7} {'zoom':>5} {'cols':>6} "
          f"{'lines':>6} {'measured':>9}   screen")
    print(f"  {'-'*8} {'-'*6} {'-'*7} {'-'*5} {'-'*6} {'-'*6} {'-'*9}   {'-'*34}")
    for r in d["rows"]:
        cols = "" if not r["cols"] else (
            f"{r['cols']}!" if r["cols"] > args.width else str(r["cols"]))
        tall = "" if not r["lines"] else (
            f"{r['lines']}!" if r["lines"] > args.height else str(r["lines"]))
        meas = f"{r['measured']:.1f}s" if r["measured"] else ""
        print(f"  {r['beat']:<8} {r['words']:>6} {r['floor']:>6.0f}s "
              f"{'yes' if r['zoom'] else '-':>5} {cols:>6} {tall:>6} "
              f"{meas:>9}   {r['screen']}")
    tw = sum(r["words"] for r in d["rows"])
    print(f"  {'-'*8} {'-'*6} {'-'*7}")
    print(f"  {'beats':<8} {tw:>6} {d['narration']:>6.0f}s")
    print("  ! = exceeds the recording terminal geometry above")

    if d["cards"] is None:
        print("\n  CARDS NOT PROBED: render demo/remotion, then re-run. No card "
              "duration is assumed here.")
        print("\nno total: the cards are part of the runtime and are unmeasured")
        return 1

    print(f"\n  title card   {d['title']:>8.2f} s   (probed)")
    print(f"  end card     {d['end']:>8.2f} s   (probed)")
    print(f"\n  floor runtime   {d['floor']:>7.1f} s   {mmss(d['floor'])}")
    print(f"  window          {WINDOW_LO:.0f} to {WINDOW_HI:.0f} s"
          f"   {mmss(WINDOW_LO)} to {mmss(WINDOW_HI)}")
    print(f"  slack to cap    {WINDOW_HI - d['floor']:>7.1f} s")

    ceiling = WINDOW_HI / 60 * args.wpm
    corrected = (WINDOW_HI - d["cards"]) / 60 * args.wpm
    print(f"\n  tools/script_words.py ceiling   {ceiling:.0f} words"
          f" = {WINDOW_HI:.0f} s narration"
          f" = {WINDOW_HI + d['cards']:.0f} s with cards "
          f"({mmss(WINDOW_HI + d['cards'])})")
    print(f"  ceiling the {d['cards']:.0f} s of cards leave   {corrected:.0f} words"
          f" = {WINDOW_HI - d['cards']:.0f} s narration = {WINDOW_HI:.0f} s "
          f"with cards ({mmss(WINDOW_HI)})")
    if ceiling > corrected:
        print(f"  -> script_words.py would pass a script "
              f"{ceiling - corrected:.0f} words over what the window allows, "
              f"because its ceiling does not subtract the two cards.")

    if args.target:
        delta = d["floor"] - args.target
        if delta > 0:
            print(f"\n  target {mmss(args.target)}: cut {delta:.0f} s, "
                  f"{round(delta * args.wpm / 60)} words, from Beat 6 or Beat 8")
        else:
            print(f"\n  target {mmss(args.target)}: met, {-delta:.0f} s spare")

    wide = [(r["beat"], n, c) for r in d["rows"] for n, c, _ in r["files"]
            if c > args.width]
    if wide:
        print(f"\n  captures wider than {args.width} columns:")
        for beat, name, c in wide:
            print(f"    {beat:<8} {name:<28} {c} cols")
    empty = [(r["beat"], n) for r in d["rows"] for n, c, l in r["files"]
             if l == 0]
    if empty:
        print("\n  captures that produced NO OUTPUT (a broken command in DEMO.md):")
        for beat, name in empty:
            print(f"    {beat:<8} {name}")

    if d["floor"] > WINDOW_HI:
        print(f"\nFAIL: floor exceeds the window by {d['floor'] - WINDOW_HI:.1f} s")
        return 1
    if d["floor"] < WINDOW_LO:
        print(f"\nFAIL: floor is {WINDOW_LO - d['floor']:.1f} s under the window")
        return 1
    print(f"\nOK: floor runtime is inside the window, "
          f"{WINDOW_HI - d['floor']:.1f} s under the cap")

    print("\nZOOM TARGETs, verbatim from demo/SCRIPT.md. Each must be on screen")
    print("long enough to read, within its beat's screen time. Not counted: read them.")
    for b in d["beats"]:
        para = d["zooms"].get(b) or []
        if not para:
            continue
        print(f"\n  {b}")
        for line in para:
            print(f"    {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
