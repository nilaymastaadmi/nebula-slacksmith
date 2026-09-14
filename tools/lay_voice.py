#!/usr/bin/env python3
"""Lay demo/audio/beatN.wav under the locked silent cut, screen by screen.

Phase 2, step 8 of demo/VIDEO_PROMPT.md. The picture is never re-cut. Each beat
shows one or more screens (demo/present_plan.py says which narration belongs to
which), and the presenter logged when each screen appeared
(demo/takes/video/times/beatN.times). The voice is placed the same way:

  1. find the pauses in the beat's audio;
  2. split it at the pause just before each paragraph (or screen's text)
     begins, located from a local whisper.cpp transcript when one exists
     (delivery rate varies too much by content to infer it from pauses);
  3. start each piece's speech ANCHOR s after its screen appears, but never
     within MIN_GAP of the previous piece and never so late that it runs into
     the next screen or the end of the beat.

A piece that cannot fit, or that would start more than EARLY_LIMIT s before its
screen, fails the run: the text was wrong at step 6 and is fixed there. Every
placement is written to demo/audio/PLACEMENT.tsv.

    python3 tools/lay_voice.py --beat 4      # one beat, a preview MP4 beside the cut
    python3 tools/lay_voice.py               # every beat, the narration track, the final MP4
"""
import argparse, io, json, os, re, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo"))
import present_plan as plan

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(HERE, "demo", "audio")
TIMES = os.path.join(HERE, "demo", "takes", "video", "times")
CUT_JSON = os.path.join(HERE, "demo", "takes", "video", "cut_manifest.json")
OUT = os.path.join(os.environ.get("USERPROFILE", HERE), "Videos", "slacksmith-demo")
FF = os.path.join(HERE, "demo", "remotion", "node_modules", "@remotion", "compositor-win32-x64-msvc", "ffmpeg.exe")
LEAD = 0.10          # s: every beat segment starts this long before its trigger (assembly)
ANCHOR = 0.15        # s after a screen appears that its speech should start
MIN_GAP = 0.30       # s of silence kept between consecutive pieces
EARLY_LIMIT = 0.75   # s a piece may start before its own screen, a normal lead-in to a cut
TAIL = 0.05          # s of picture kept after a piece's speech ends
SR = 24000


def read_wav(path):
    with wave.open(path) as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2, path
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def pauses(x):
    """[(start_s, end_s)] of silences of at least 0.25 s, and the voiced span."""
    hop = SR // 100
    rms = np.sqrt(np.convolve(x ** 2, np.ones(hop * 2) / (hop * 2), mode="same")[::hop])
    db = 20 * np.log10(rms / 32768 + 1e-9)
    quiet = db < np.percentile(db, 95) - 35
    out, start = [], None
    for i, q in enumerate(np.append(quiet, False)):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if i - start >= 25:
                out.append((start / 100, i / 100))
            start = None
    voiced = np.where(~quiet)[0]
    return out, voiced[0] / 100, voiced[-1] / 100


def speech_rms(x):
    """RMS over voiced 10 ms frames only, so pauses do not dilute a beat's level."""
    hop = SR // 100
    frames = x[:len(x) // hop * hop].reshape(-1, hop)
    r = np.sqrt((frames ** 2).mean(axis=1))
    db = 20 * np.log10(r / 32768 + 1e-9)
    voiced = r[db >= np.percentile(db, 95) - 20]
    return float(np.sqrt((voiced ** 2).mean()))


SENTENCE = re.compile(r"(?<=[.!?])\s+")


def units(beat):
    """[(screen, [(boundary, words), ...])] in speaking order. boundary says what
    separates a run from the one before it: "para" or "sent". Spare time goes
    into those breaks, so the text is kept at sentence resolution; a sentence-based
    screen splits its sentences the same way, and a long output paged in two is one
    screen holding everything."""
    paras = plan.paragraphs(beat)
    plan_rows = plan.PLAN.get(beat, [("card", ("p", 1, len(paras)))])

    def runs_of(par_list):
        out = []
        for para in par_list:
            for j, sent in enumerate(SENTENCE.split(para)):
                out.append(("sent" if j else "para", len(sent.split())))
        return out

    if any(u[0] == "half" for _, u in plan_rows):
        return [(plan_rows[0][0], runs_of(paras))]
    sentences = [(pi, sent) for pi, para in enumerate(paras) for sent in SENTENCE.split(para)]
    rows = []
    for name, u in plan_rows:
        if u[0] == "p":
            rows.append((name, runs_of(paras[u[1] - 1:u[2]])))
        else:
            chosen = sentences[u[1] - 1:(u[2] or len(sentences))]
            rows.append((name, [("sent" if k and chosen[k - 1][0] == pi else "para", len(t.split()))
                                for k, (pi, t) in enumerate(chosen)]))
    return rows


def screen_starts(beat, names):
    if beat == 0:
        return [0.0]
    t = {}
    for line in io.open(os.path.join(TIMES, f"beat{beat}.times"), encoding="utf-8"):
        k, v = line.split()
        t[k] = float(v)
    return [t[n] + LEAD for n in names]


def split_points(gaps, onset, end, words):
    """Cut times between runs of text, one pause per boundary.

    Every combination of pauses is tried; the chosen one makes each run read at
    the same rate as the beat overall (squared log ratio), with a small credit
    for longer pauses, which is where paragraphs usually break. A greedy choice
    by word share alone picked a sentence pause on a beat whose delivery was
    uneven, so the search is exhaustive (at most a few hundred combinations)."""
    from itertools import combinations
    k = len(words) - 1
    if k == 0:
        return []
    if len(gaps) < k:
        sys.exit(f"{len(gaps)} pauses cannot make {k} cuts")
    total_rate = sum(words) / (end - onset)
    best = None
    for combo in combinations(range(len(gaps)), k):
        edges = [onset] + [x for i in combo for x in gaps[i]] + [end]
        durs = [edges[2 * j + 1] - edges[2 * j] for j in range(k + 1)]
        if min(durs) <= 0:
            continue
        cost = sum(np.log((w / d) / total_rate) ** 2 for w, d in zip(words, durs))
        cost -= 0.02 * sum(np.log((gaps[i][1] - gaps[i][0]) / 0.25) for i in combo)
        if best is None or cost < best[0]:
            best = (cost, combo)
    return [(gaps[i][0] + gaps[i][1]) / 2 for i in best[1]]


WHISPER = os.path.join(AUDIO, "whisper")


def heard_boundaries(beat, words):
    """Where each run of text after the first begins in the audio, from a local
    whisper.cpp transcript (demo/audio/whisper/beatN.json, ggml-base.en). None if
    there is no transcript. Text and transcript are aligned word by word; a run
    whose first words were misheard is anchored on the first word that matched
    and moved back by the words skipped, at the beat's own pace."""
    import difflib
    path = os.path.join(WHISPER, f"beat{beat}.json")
    if not os.path.exists(path):
        return None
    norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    heard = []
    for seg in json.load(io.open(path, encoding="utf-8"))["transcription"]:
        for tok in seg["text"].split():
            if norm(tok):
                heard.append((norm(tok), seg["offsets"]["from"] / 1000))
    text = [norm(w) for w in io.open(os.path.join(AUDIO, f"beat{beat}.txt"), encoding="utf-8").read().split()]
    sm = difflib.SequenceMatcher(a=text, b=[h[0] for h in heard], autojunk=False)
    t2h = {blk.a + k: blk.b + k for blk in sm.get_matching_blocks() for k in range(blk.size)}
    span = heard[-1][1] - heard[0][1]
    per_word = span / max(1, len(text) - 1)
    out, start = [], 0
    for w in words[:-1]:
        start += w
        k = next((k for k in range(start, min(len(text), start + 8)) if k in t2h), None)
        if k is None:
            sys.exit(f"beat {beat}: no transcript word matches near text word {start}")
        out.append(heard[t2h[k]][1] - (k - start) * per_word)
    return out


def cut_near(x, t):
    """(cut time, quiet seconds) at the longest quiet stretch in the 0.7 s ending
    just after t.

    whisper.cpp folds the pause before a word into the previous word, so a heard
    start sits at or just after the real break; the break itself may be shorter
    than the 0.25 s pauses() reports, so this looks at 10 ms frames directly."""
    hop = SR // 100
    lo, hi = max(0, int((t - 0.70) * 100)), int((t + 0.05) * 100)
    frames = x[:len(x) // hop * hop].reshape(-1, hop)
    db_all = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) / 32768 + 1e-9)
    db = db_all[lo:hi]
    quiet = db < np.percentile(db_all, 95) - 30
    best, run = None, None
    for i, q in enumerate(np.append(quiet, False)):
        if q and run is None:
            run = i
        elif not q and run is not None:
            if best is None or i - run >= best[1] - best[0]:
                best = (run, i)
            run = None
    if best is None:
        return (lo + int(np.argmin(db))) / 100, 0.0
    return (lo + (best[0] + best[1]) / 2) / 100, (best[1] - best[0]) / 100


def waterfill(mins, total, weights):
    """Pause lengths summing to total, each at least its minimum, and otherwise
    proportional to its weight. A screen's lead and trail get weight 0.5 because
    each is half of the silence across a cut; the other half belongs to the
    neighbouring screen, so a cut ends up as long as a paragraph pause."""
    lo, hi = 0.0, total / min(weights)
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(max(m, w * mid) for m, w in zip(mins, weights)) > total:
            hi = mid
        else:
            lo = mid
    return [max(m, w * lo) for m, w in zip(mins, weights)]


SENT_WEIGHT = 0.6    # share of spare time a sentence break takes, against 1.0 for a paragraph
MIN_QUIET = 0.12     # s of real quiet needed before a sentence break is used at all


def place(beat, picture_s, prev_tail):
    """prev_tail: silence left at the end of the previous beat, so a beat's first
    words never start over the previous beat's last ones."""
    x = read_wav(os.path.join(AUDIO, f"beat{beat}.wav"))
    level = speech_rms(x)
    gaps, onset, end = pauses(x)
    screens = units(beat)
    flat = [(k, kind, w) for k, (_n, runs) in enumerate(screens) for kind, w in runs]
    words = [w for _k, _kind, w in flat]
    heard = heard_boundaries(beat, words)
    cuts, merged = [], [list(flat[0])]
    if heard is None:                      # no transcript: split at screen changes only
        per_screen = [sum(w for kk, _, w in flat if kk == k) for k in range(len(screens))]
        screen_cuts = split_points(gaps, onset, end, per_screen)
        merged = [[k, "para", per_screen[k]] for k in range(len(screens))]
        cuts = screen_cuts
    else:
        for i, t in enumerate(heard):
            k, kind, w = flat[i + 1]
            at, quiet = cut_near(x, t)
            if k == merged[-1][0] and kind == "sent" and quiet < MIN_QUIET:
                merged[-1][2] += w         # no real break here: keep the sentences joined
                continue
            cuts.append(at)
            merged.append([k, kind, w])
    bounds = [0.0] + cuts + [len(x) / SR]
    sub = []
    for i, (k, kind, w) in enumerate(merged):
        seg = x[int(bounds[i] * SR):int(bounds[i + 1] * SR)]
        _g, on, off = pauses(seg)
        sub.append({"screen_k": k, "kind": kind, "samples": seg, "seg_onset": on, "speech_s": off - on,
                    "level": level, "orig_on": bounds[i] + on, "orig_off": bounds[i] + off, "words": w})
    starts = screen_starts(beat, [n for n, _ in screens])
    runs_k = [[r for r in sub if r["screen_k"] == k] for k in range(len(screens))]
    nat_k = [[rs[j + 1]["orig_on"] - rs[j]["orig_off"] for j in range(len(rs) - 1)] for rs in runs_k]
    need_k = [sum(r["speech_s"] for r in rs) + sum(n) for rs, n in zip(runs_k, nat_k)]
    # backwards: a screen must end early enough for a tight screen after it to start early
    latest_end = [0.0] * len(screens)
    nxt_start = picture_s
    for k in reversed(range(len(screens))):
        cap = (starts[k + 1] if k + 1 < len(screens) else picture_s) - TAIL
        latest_end[k] = min(cap, nxt_start - MIN_GAP) if k + 1 < len(screens) else cap
        nxt_start = min(starts[k] + ANCHOR, latest_end[k] - need_k[k])
    pieces, problems, prev_end = [], [], None
    for k, (name, _runs) in enumerate(screens):
        run = runs_k[k]
        w0 = starts[k]
        w1 = latest_end[k]
        speech = sum(r["speech_s"] for r in run)
        natural = nat_k[k]
        inner_w = [1.0 if run[j + 1]["kind"] == "para" else SENT_WEIGHT for j in range(len(run) - 1)]
        lower = max(w0 - EARLY_LIMIT, (MIN_GAP - prev_tail) if prev_end is None else prev_end + MIN_GAP)
        lead_min = max(ANCHOR, lower - w0)
        room = (w1 - w0) - speech
        if room >= lead_min + sum(natural):
            gapsz = waterfill([lead_min] + natural + [0.0], room, [0.5] + inner_w + [0.5])
            t, inner = w0 + gapsz[0], gapsz[1:-1]
        else:
            need = speech + sum(natural)
            t, inner = min(w0 + ANCHOR, w1 - need), natural
            if t < lower - 1e-9:
                problems.append(f"beat {beat} {name}: {need:.2f} s of speech cannot fit between "
                                f"{lower:.2f} and {w1:.2f} s")
        for j, r in enumerate(run):
            r.update(screen=name, screen_at=w0, speak_at=t, offset=t - w0, ends=t + r["speech_s"],
                     next_at=starts[k + 1] if k + 1 < len(screens) else picture_s,
                     pause_after=inner[j] if j < len(inner) else None)
            r["wpm"] = r["words"] / r["speech_s"] * 60 if r["speech_s"] > 0 else 0
            t = r["ends"] + (inner[j] if j < len(inner) else 0.0)
            pieces.append(r)
        prev_end = run[-1]["ends"]
        rate = sum(r["words"] for r in run) / speech * 60
        if not 110 <= rate <= 210:
            problems.append(f"beat {beat} {name}: {rate:.0f} wpm, the split is probably wrong")
        for r in run:
            r["slack"] = r["next_at"] - prev_end
            r["screen_wpm"] = rate
    return pieces, problems


def render(beat_pieces, length_s):
    track = np.zeros(int(length_s * SR) + SR, dtype=np.float32)
    target = float(np.median([pieces[0]["level"] for _s, pieces in beat_pieces]))
    for seg_start, pieces in beat_pieces:
        for p in pieces:
            at = int(round((seg_start + p["speak_at"] - p["seg_onset"]) * SR))
            s = p["samples"] * (target / p["level"])
            fade = min(len(s) // 4, SR // 100)
            if fade:
                s[:fade] *= np.linspace(0, 1, fade); s[-fade:] *= np.linspace(1, 0, fade)
            if at < 0:              # leading silence reaching back past the track start
                s, at = s[-at:], 0
            s = s[:max(0, len(track) - at)]
            track[at:at + len(s)] += s
    return np.clip(track[:int(length_s * SR)], -32768, 32767).astype(np.int16)


def write_wav(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(samples.tobytes())


def run(args):
    r = subprocess.run([FF, "-v", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg failed: " + r.stderr[-600:])


def loudnorm_args(wav):
    """Two-pass loudnorm to -16 LUFS integrated, -1.5 dBTP: measure, then apply
    linearly. A single dynamic pass measured -17.3 LUFS on the first full mix."""
    r = subprocess.run([FF, "-hide_banner", "-nostats", "-i", wav, "-af",
                        "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    return ["-af", (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                    f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beat", type=int, help="place one beat and write a preview MP4 of its segment")
    a = ap.parse_args()
    man = json.load(io.open(CUT_JSON, encoding="utf-8"))
    seg_start, seg_len = {}, {}
    for _label, name, d, cum in man["rows"]:
        if name.startswith(("00a", "00b")):
            seg_start.setdefault(0, cum - d); seg_len[0] = seg_len.get(0, 0.0) + d
        elif name[:2].isdigit() and name[:2] not in ("00", "99"):
            seg_start[int(name[:2])] = cum - d; seg_len[int(name[:2])] = d
    beats = [a.beat] if a.beat is not None else sorted(seg_start)
    placed, problems, table = [], [], []
    prev_tail = MIN_GAP              # nothing is spoken before the title card
    for b in beats:
        pieces, bad = place(b, seg_len[b], prev_tail if b - 1 in seg_start or b == 0 else MIN_GAP)
        prev_tail = seg_len[b] - pieces[-1]["ends"]
        problems += bad
        placed.append((seg_start[b], pieces))
        for p in pieces:
            table.append((b, p))
        for name in dict.fromkeys(p["screen"] for p in pieces):
            rs = [p for p in pieces if p["screen"] == name]
            longest = max([p["pause_after"] for p in rs if p["pause_after"] is not None], default=0.0)
            print(f"  beat {b} {name:<12} screen {rs[0]['screen_at']:6.2f}  speech {rs[0]['speak_at']:6.2f} to {rs[-1]['ends']:6.2f}"
                  f"  ({rs[0]['offset']:+.2f} s from its screen)  next {rs[0]['next_at']:6.2f}  slack {rs[0]['slack']:+.2f}"
                  f"  {rs[0]['screen_wpm']:.0f} wpm  {len(rs)} runs, longest inner pause {longest:.2f} s")
    if a.beat is None:
        with io.open(os.path.join(AUDIO, "PLACEMENT.tsv"), "w", encoding="utf-8", newline="\n") as f:
            f.write("beat\tscreen\tbreak\twords\tscreen_at\tspeak_at\tspeech_s\tends\tpause_after\tnext_at\n")
            for b, p in table:
                pa = "" if p["pause_after"] is None else f"{p['pause_after']:.2f}"
                f.write(f"{b}\t{p['screen']}\t{p['kind']}\t{p['words']}\t{p['screen_at']:.2f}\t{p['speak_at']:.2f}\t"
                        f"{p['speech_s']:.2f}\t{p['ends']:.2f}\t{pa}\t{p['next_at']:.2f}\n")
    if a.beat is None:
        print("  seams: beat, speech rate, level vs median, silence across the cut into the next beat")
        med = float(np.median([pc[0]["level"] for _s, pc in placed]))
        for idx, (st, pc) in enumerate(placed):
            b = beats[idx]
            rate = sum(p["words"] for p in pc) / sum(p["speech_s"] for p in pc) * 60
            gain = 20 * np.log10(med / pc[0]["level"])
            seam = ""
            if idx + 1 < len(placed):
                nst, npc = placed[idx + 1]
                seam = f"{(nst + npc[0]['speak_at']) - (st + pc[-1]['ends']):.2f} s"
            print(f"    beat {b}  {rate:5.1f} wpm  gain {gain:+5.1f} dB  silence into next {seam}")
    if problems:
        print("FAILED, fix the text at step 6:\n  " + "\n  ".join(problems)); sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    if a.beat is not None:
        b = a.beat
        raw = os.path.join(OUT, f"voice_beat{b}_raw.wav")
        write_wav(raw, render([(0.0, placed[0][1])], seg_len[b]))
        seg = os.path.join(OUT, "segments", sorted(n for n in os.listdir(os.path.join(OUT, "segments")) if n.startswith(f"{b:02d}_"))[0])
        out = os.path.join(OUT, f"preview_beat{b}.mp4")
        run(["-i", seg, "-i", raw, "-map", "0:v", "-map", "1:a", "-c:v", "copy"] + loudnorm_args(raw) +
            ["-ar", "48000", "-c:a", "aac", "-b:a", "192k", out])
        print(f"preview: {out}")
        return
    raw = os.path.join(OUT, "narration_raw.wav")
    write_wav(raw, render(placed, man["cut"]))
    out = os.path.join(OUT, "slacksmith_demo.mp4")
    run(["-i", os.path.join(OUT, "slacksmith_silent_cut.mp4"), "-i", raw, "-map", "0:v", "-map", "1:a", "-c:v", "copy"]
        + loudnorm_args(raw) + ["-ar", "48000", "-c:a", "aac", "-b:a", "192k", out])
    print(f"final: {out}")


if __name__ == "__main__":
    main()
