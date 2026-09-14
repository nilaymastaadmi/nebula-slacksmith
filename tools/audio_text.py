#!/usr/bin/env python3
"""Write demo/audio/beatN.txt and demo/audio/MANIFEST.tsv from demo/SCRIPT.md.

Phase 2, steps 5 and 6 of demo/VIDEO_PROMPT.md. Each beat file holds only that
beat's spoken narration, '>' markers stripped, one paragraph per line with a
blank line between paragraphs. The pronunciation table in SCRIPT.md is applied
by rewriting the words; the script exits 1 if any written form from the table,
or any digit, survives into a beat file, because Sarvam would then guess.

MANIFEST.tsv is the dry run before any Sarvam call: words and expected seconds
at 150 wpm (counted the way tools/script_words.py counts), against the beat's
measured duration in the locked cut (demo/takes/video/cut_manifest.json). A
beat whose expected seconds exceed its picture is flagged, and the script exits
1. Fix the text, never the picture. Columns audio_s and fits are filled in once
a beat has been synthesized and measured; rerunning keeps them.

    python3 tools/audio_text.py
"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HERE, "demo", "SCRIPT.md")
AUDIO = os.path.join(HERE, "demo", "audio")
CUT = os.path.join(HERE, "demo", "takes", "video", "cut_manifest.json")
MANIFEST = os.path.join(AUDIO, "MANIFEST.tsv")
WPM = 150

# SCRIPT.md's pronunciation table, as rewrites. Longest first, so SymbiYosys is
# rewritten before Yosys can match inside it.
REWRITES = [
    (r"\bSymbiYosys\b", "SIM-bee-YO-sis"), (r"\bYosys\b", "YO-sis"),
    (r"\bOpenSTA\b", "open S T A"), (r"\bOpenROAD\b", "open road"),
    (r"\bRV32I\b", "R V thirty-two I"), (r"\bsky130\b", "sky one-thirty"),
    (r"\brepair_design\b", "repair design"), (r"\bnor4_1\b", "nor four"),
    (r"\bns\b", "nanoseconds"),
] + [(rf"\b{a}\b", " ".join(a)) for a in ("RTL", "SDC", "EQY", "CDC", "ABC", "AES", "PPA")] \
  + [(rf"\bG{d}\b", f"gate {w}") for d, w in enumerate("zero one two three four five six seven".split())]


def beats():
    """{beat number: [paragraph, ...]} from the '>' lines, as script_words.py reads them."""
    out, beat, para = {}, None, []
    for line in io.open(SCRIPT, encoding="utf-8"):
        if line.startswith("## "):
            if para:
                out.setdefault(beat, []).append(" ".join(para)); para = []
            beat = int(line.split()[2].rstrip(".")) if line.startswith("## Beat") else None
            continue
        if beat is None:
            continue
        if line.startswith(">"):
            text = line[1:].strip()
            if text:
                para.append(text)
            elif para:
                out.setdefault(beat, []).append(" ".join(para)); para = []
        elif para:
            out.setdefault(beat, []).append(" ".join(para)); para = []
    return out


def picture_seconds():
    """Measured screen time per beat in the locked cut. Beat 0 spans the title
    card's own fade in and the held still after it; its fade out is silent."""
    rows = json.load(io.open(CUT, encoding="utf-8"))["rows"]
    secs = {}
    for _label, name, d, _cum in rows:
        if name.startswith(("00a", "00b")):
            secs[0] = secs.get(0, 0.0) + d
        elif name[:2].isdigit() and name[:2] not in ("00", "99"):
            secs[int(name[:2])] = d
    return secs


def main():
    os.makedirs(AUDIO, exist_ok=True)
    kept = {}
    if os.path.exists(MANIFEST):
        for row in io.open(MANIFEST, encoding="utf-8").read().splitlines()[1:]:
            f = row.split("\t")
            if len(f) >= 8 and f[6]:
                kept[f[0]] = (f[6], f[7])
    pic = picture_seconds()
    bad, rows = [], []
    for b, paras in sorted(beats().items()):
        spoken_words = sum(len(p.split()) for p in paras)
        text = "\n\n".join(paras)
        for pat, say in REWRITES:
            text = re.sub(pat, say, text)
        left = [pat for pat, _ in REWRITES if re.search(pat, text)] + re.findall(r"\d", text)
        if left:
            bad.append(f"beat {b}: still carries {left}")
        name = f"beat{b}.txt"
        io.open(os.path.join(AUDIO, name), "w", encoding="utf-8", newline="\n").write(text + "\n")
        words = len(text.split())
        expected = words / WPM * 60
        flag = "OVER" if expected > pic[b] + 1e-6 else ""
        if flag:
            bad.append(f"beat {b}: {expected:.1f} s expected against a {pic[b]:.3f} s picture")
        audio_s, fits = kept.get(name, ("", ""))
        rows.append((name, words, spoken_words, expected, pic[b], flag, audio_s, fits))
    with io.open(MANIFEST, "w", encoding="utf-8", newline="\n") as m:
        m.write("file\twords\tscript_words\texpected_s\tpicture_s\tflag\taudio_s\tfits\n")
        for name, w, sw, e, p, flag, a, fits in rows:
            m.write(f"{name}\t{w}\t{sw}\t{e:.1f}\t{p:.3f}\t{flag}\t{a}\t{fits}\n")
    for name, w, sw, e, p, flag, a, fits in rows:
        print(f"  {name:<10} {w:>4} words  {e:>5.1f} s expected  {p:>7.3f} s picture  {round(p - e, 3) + 0.0:+6.2f} s  {flag or 'ok'}")
    print(f"total {sum(r[1] for r in rows)} words")
    if bad:
        print("FLAGGED, synthesize nothing:\n  " + "\n  ".join(bad)); sys.exit(1)
    print("no beat flagged")


if __name__ == "__main__":
    main()
