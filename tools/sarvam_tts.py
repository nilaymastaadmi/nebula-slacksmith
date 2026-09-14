#!/usr/bin/env python3
"""Synthesize demo/audio/beatN.txt with Sarvam, one call per beat, and measure it.

Phase 2, step 7 of demo/VIDEO_PROMPT.md. Every call is spend, so this script
refuses to call when it cannot justify one:

  - it runs tools/audio_text.py first and stops if any beat is flagged;
  - it skips a beat whose beatN.wav already matches that text, voice, pace and
    model (recorded in beatN.json beside it) unless --force is given;
  - it synthesizes only the beats named on the command line.

After each call it measures the WAV and writes audio_s and fits into
demo/audio/MANIFEST.tsv, where fits compares the audio with the beat's picture.
The key comes from SARVAM_API_KEY or from a file given with --key-file holding a
SARVAM_API_KEY= line; it is never printed or written anywhere.

    python3 tools/sarvam_tts.py 4                       # beat 4 alone
    python3 tools/sarvam_tts.py 0 1 2 3 5 6 7 8         # the rest, one pass
"""
import argparse, base64, hashlib, io, json, os, subprocess, sys, time, urllib.error, urllib.request, wave
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(HERE, "demo", "audio")
MANIFEST = os.path.join(AUDIO, "MANIFEST.tsv")
URL = "https://api.sarvam.ai/text-to-speech"
MODEL, LANG, RATE = "bulbul:v3", "en-IN", 24000


def key(path):
    k = os.environ.get("SARVAM_API_KEY")
    if not k and path:
        for line in io.open(path, encoding="utf-8"):
            if line.startswith("SARVAM_API_KEY="):
                k = line.split("=", 1)[1].strip()
    if not k:
        sys.exit("no Sarvam key: set SARVAM_API_KEY or pass --key-file")
    return k


def synth(text, voice, pace, api_key):
    body = json.dumps({"text": text, "target_language_code": LANG, "speaker": voice, "model": MODEL,
                       "pace": pace, "speech_sample_rate": RATE, "output_audio_codec": "wav"}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
                                 headers={"api-subscription-key": api_key, "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return base64.b64decode(json.loads(r.read())["audios"][0])
        except urllib.error.HTTPError as e:
            msg = e.read()[:200].decode("utf-8", "replace")
            if e.code not in (429, 500, 502, 503, 504):
                sys.exit(f"Sarvam HTTP {e.code}, not retried: {msg}")
            print(f"  Sarvam HTTP {e.code} on attempt {attempt + 1}, retrying: {msg}")
            time.sleep(5 * (attempt + 1))
    sys.exit("Sarvam failed 3 times")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("beats", nargs="+", type=int)
    ap.add_argument("--voice", default="rahul")
    ap.add_argument("--pace", type=float, default=1.0)
    ap.add_argument("--key-file")
    ap.add_argument("--force", action="store_true", help="call even if the WAV already matches")
    a = ap.parse_args()

    if subprocess.run([sys.executable, os.path.join(HERE, "tools", "audio_text.py")]).returncode:
        sys.exit("tools/audio_text.py flagged a beat: fix the text before spending a call")
    rows = [r.split("\t") for r in io.open(MANIFEST, encoding="utf-8").read().splitlines()]
    head, body = rows[0], {r[0]: r for r in rows[1:]}

    api_key = None
    for b in a.beats:
        name = f"beat{b}"
        text = io.open(os.path.join(AUDIO, name + ".txt"), encoding="utf-8").read().strip()
        tag = hashlib.sha256(f"{text}|{a.voice}|{a.pace}|{MODEL}|{LANG}".encode()).hexdigest()[:16]
        wav_path, side = os.path.join(AUDIO, name + ".wav"), os.path.join(AUDIO, name + ".json")
        fresh = os.path.exists(wav_path) and os.path.exists(side) and json.load(io.open(side)).get("tag") == tag
        if fresh and not a.force:
            print(f"  {name}: WAV already matches this text, voice and pace; no call")
        else:
            api_key = api_key or key(a.key_file)
            print(f"  {name}: calling Sarvam ({MODEL}, {a.voice}, pace {a.pace}, {len(text.split())} words)")
            io.open(wav_path, "wb").write(synth(text, a.voice, a.pace, api_key))
            json.dump({"tag": tag, "model": MODEL, "voice": a.voice, "pace": a.pace, "language": LANG,
                       "text_sha256": hashlib.sha256(text.encode()).hexdigest(), "made": time.strftime("%Y-%m-%d %H:%M:%S")},
                      io.open(side, "w", encoding="utf-8"), indent=1)
        with wave.open(wav_path) as w:
            secs = w.getnframes() / w.getframerate()
        row = body[name + ".txt"]
        picture = float(row[head.index("picture_s")])
        row[head.index("audio_s")] = f"{secs:.3f}"
        row[head.index("fits")] = "yes" if secs <= picture else f"OVER by {secs - picture:.2f} s"
        words = int(row[head.index("words")])
        print(f"  {name}: {secs:.3f} s of audio, {words / secs * 60:.1f} wpm, picture {picture:.3f} s, "
              f"{'fits' if secs <= picture else 'OVERRUNS'} ({picture - secs:+.2f} s)")
    with io.open(MANIFEST, "w", encoding="utf-8", newline="\n") as m:
        m.write("\n".join("\t".join(r) for r in [head] + list(body.values())) + "\n")


if __name__ == "__main__":
    main()
