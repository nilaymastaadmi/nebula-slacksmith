#!/usr/bin/env python3
"""Carry a handoff request to a HOSTED open-weight model and write the reply.

Adapted from experiments/open_weight_2/shim.py. The loop side is identical: it
watches for REQUEST_<id>.md, sends it verbatim, writes the reply UNEDITED to
RESPONSE_<id>.json, and lets the loop's own _extract_json decide whether it
counts. Only the transport changes, from Ollama's local /api/generate to an
OpenAI-compatible /chat/completions endpoint. Like the earlier shims it lives
outside tools/, because the claim under test is that the handoff backend takes
any model with no change to the tool.

The API key is read from a file OUTSIDE the repository (default
~/.openrouter_key, override with OPENWEIGHT_KEY_FILE) and is never printed,
logged or written anywhere. tools/preflight.sh fails if a credential-shaped
string reaches a tracked file.

Sampling and retries, as registered in PREREGISTRATION.md:
- default sampling: no temperature, no top_p, no reasoning setting is sent;
- max_tokens 16384, because a free endpoint's default output cap could cut a
  whole-module rewrite and that would measure the endpoint, not the model;
- one sample. A reply with content is never retried. A TRANSPORT failure
  (HTTP 429 or 5xx, or no connection) is retried at most twice, 60 s apart,
  and every attempt is recorded in META.
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request


def read_key(path):
    with open(os.path.expanduser(path), encoding="utf-8") as fh:
        key = fh.read().strip()
    if not key:
        raise SystemExit("VOID: key file %s is empty" % path)
    return key


def chat(base, model, prompt, key, timeout, max_tokens, json_mode):
    payload = {"model": model, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="the loop's handoff directory")
    ap.add_argument("--model", required=True)
    ap.add_argument("--base", default="https://openrouter.ai/api/v1")
    ap.add_argument("--key-file", default=os.environ.get("OPENWEIGHT_KEY_FILE",
                                                         "~/.openrouter_key"))
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("--max-tokens", type=int, default=16384)
    ap.add_argument("--json-mode", action="store_true",
                    help="response_format json_object. R104's declared follow-up only.")
    ap.add_argument("--watch", type=float, default=900)
    a = ap.parse_args()

    key = read_key(a.key_file)
    os.makedirs(a.dir, exist_ok=True)
    print("shim: watching %s for REQUEST_*.md" % a.dir, flush=True)
    print("shim: model %s at %s, default sampling, one sample, max_tokens=%d, json_mode=%s"
          % (a.model, a.base, a.max_tokens, a.json_mode), flush=True)
    seen, answered, t_start = set(), 0, time.time()
    while time.time() - t_start < a.watch:
        for name in sorted(os.listdir(a.dir)):
            if not (name.startswith("REQUEST_") and name.endswith(".md")):
                continue
            pid = name[len("REQUEST_"):-len(".md")]
            rsp = os.path.join(a.dir, "RESPONSE_%s.json" % pid)
            if pid in seen or os.path.exists(rsp):
                seen.add(pid)
                continue
            prompt = open(os.path.join(a.dir, name), encoding="utf-8").read()
            print("shim: request %s, %d chars -> %s" % (pid, len(prompt), a.model), flush=True)
            attempts, payload, err = [], None, None
            for attempt in range(3):
                t0 = time.time()
                try:
                    payload = chat(a.base, a.model, prompt, key, a.timeout,
                                   a.max_tokens, a.json_mode)
                    attempts.append({"attempt": attempt + 1, "ok": True,
                                     "seconds": round(time.time() - t0, 1)})
                    break
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8", "replace")[:500]
                    attempts.append({"attempt": attempt + 1, "http": e.code, "body": body,
                                     "seconds": round(time.time() - t0, 1)})
                    err = "HTTP %d: %s" % (e.code, body)
                    if e.code != 429 and e.code < 500:
                        break
                except (urllib.error.URLError, TimeoutError, OSError) as e:
                    attempts.append({"attempt": attempt + 1, "error": str(e),
                                     "seconds": round(time.time() - t0, 1)})
                    err = str(e)
                print("shim: transport attempt %d failed: %s" % (attempt + 1, err), flush=True)
                if attempt < 2:
                    time.sleep(60)
            meta = {"model_requested": a.model, "attempts": attempts,
                    "max_tokens": a.max_tokens, "json_mode": a.json_mode}
            if payload is None:
                meta["void"] = "no reply after %d transport attempts" % len(attempts)
                open(os.path.join(a.dir, "META_%s.json" % pid), "w",
                     encoding="utf-8").write(json.dumps(meta, indent=2))
                open(rsp, "w", encoding="utf-8").write("hosted shim transport failure: %s" % err)
                print("shim: VOID, no reply: %s" % err, flush=True)
            else:
                choice = (payload.get("choices") or [{}])[0]
                text = (choice.get("message") or {}).get("content") or ""
                meta.update({"model_served": payload.get("model"),
                             "provider": payload.get("provider"),
                             "finish_reason": choice.get("finish_reason"),
                             "usage": payload.get("usage")})
                open(os.path.join(a.dir, "RAW_%s.txt" % pid), "w", encoding="utf-8").write(text)
                open(os.path.join(a.dir, "META_%s.json" % pid), "w",
                     encoding="utf-8").write(json.dumps(meta, indent=2))
                open(rsp, "w", encoding="utf-8").write(text)
                print("shim: %s replied, %d chars, finish_reason %s, usage %s"
                      % (a.model, len(text), meta["finish_reason"], meta["usage"]), flush=True)
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
