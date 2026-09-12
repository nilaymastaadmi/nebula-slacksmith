#!/usr/bin/env python3
"""Carry a handoff request to a local open-weight model and write the reply.

This is a COPY of experiments/open_weight/shim.py with one change: the default
model tag. The original is left untouched because it is the first experiment's
artifact, and an adapter edited after the fact is not the adapter that produced
the result it is cited for.

This file is deliberately NOT in tools/. The claim under test
(SUBMISSION_PACK.md section 5d) is that the existing handoff backend already
takes any model "with no code change", so the adapter that proves it has to
live outside the thing it is proving. If this script ever needs an edit to
tools/proposer.py to work, R41 has missed and the pack is wrong.

    python3 experiments/open_weight/shim.py --dir WORKDIR/handoff \
        --model qwen2.5-coder:7b

Watches for REQUEST_<id>.md, sends it verbatim to Ollama's local HTTP API, and
writes the model's reply to RESPONSE_<id>.json, which is what the loop polls
for. The reply is written UNEDITED. The loop's own _extract_json decides
whether a model that wrapped its JSON in prose still counts as answering, and
that decision belongs to the harness, not to this shim.

Default sampling. No temperature, no top_p, no retry, one sample per request,
matching how every Claude proposal in this repository was taken.
"""
import argparse
import json
import os
import time
import urllib.request

def generate(host, model, prompt, timeout):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(host.rstrip("/") + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        payload = json.load(r)
    return payload, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="the loop's handoff directory")
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--watch", type=float, default=900,
                    help="seconds to wait for a request before giving up")
    a = ap.parse_args()

    os.makedirs(a.dir, exist_ok=True)
    print("shim: watching %s for REQUEST_*.md" % a.dir, flush=True)
    print("shim: model %s at %s, default sampling, one sample" % (a.model, a.host), flush=True)
    seen = set()
    t_start = time.time()
    answered = 0
    while time.time() - t_start < a.watch:
        for name in sorted(os.listdir(a.dir)):
            if not (name.startswith("REQUEST_") and name.endswith(".md")):
                continue
            pid = name[len("REQUEST_"):-len(".md")]
            if pid in seen:
                continue
            rsp = os.path.join(a.dir, "RESPONSE_%s.json" % pid)
            if os.path.exists(rsp):
                seen.add(pid)
                continue
            prompt = open(os.path.join(a.dir, name), encoding="utf-8").read()
            print("shim: request %s, %d chars -> %s" % (pid, len(prompt), a.model), flush=True)
            try:
                payload, secs = generate(a.host, a.model, prompt, a.timeout)
            except Exception as e:                      # noqa: BLE001
                # A failure here is a result, not a crash: the loop must see
                # something and record it, the same way propose() treats a
                # proposer that returns nothing usable as a finding.
                print("shim: FAILED after asking %s: %s" % (a.model, e), flush=True)
                open(rsp, "w", encoding="utf-8").write(
                    "open-weight shim error: %s" % e)
                seen.add(pid)
                answered += 1
                continue
            text = payload.get("response", "")
            raw = os.path.join(a.dir, "RAW_%s.txt" % pid)
            open(raw, "w", encoding="utf-8").write(text)
            meta = {k: payload.get(k) for k in
                    ("model", "total_duration", "eval_count", "prompt_eval_count")}
            meta["wall_seconds"] = round(secs, 1)
            open(os.path.join(a.dir, "META_%s.json" % pid), "w",
                 encoding="utf-8").write(json.dumps(meta, indent=2))
            print("shim: %s replied in %.1f s, %d chars" % (a.model, secs, len(text)), flush=True)
            open(rsp, "w", encoding="utf-8").write(text)
            seen.add(pid)
            answered += 1
        if answered:
            print("shim: answered %d request(s), exiting" % answered, flush=True)
            return 0
        time.sleep(2)
    print("shim: no request appeared within %.0f s" % a.watch, flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
