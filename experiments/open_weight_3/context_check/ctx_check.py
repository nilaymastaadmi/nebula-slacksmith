"""Measure how much of the open-weight request Ollama actually evaluates.

Run from the repository root with Ollama serving qwen2.5-coder:7b. Sends the
identical 18,554-character request twice with num_predict 1: once with
Ollama's default options, as all three local runs were sent, and once with
num_ctx 16384. prompt_eval_count is the number of prompt tokens the model saw.
Run 2026-09-14; result.json beside this file.
"""
import json, time, urllib.request
REQ = "experiments/open_weight_2/results/REQUEST_O1.md"
prompt = open(REQ, encoding="utf-8").read()
out = {"request_chars": len(prompt)}
for label, opts in (("default_options", {"num_predict": 1}),
                    ("num_ctx_16384", {"num_predict": 1, "num_ctx": 16384})):
    body = json.dumps({"model": "qwen2.5-coder:7b", "prompt": prompt, "stream": False,
                       "options": opts}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        p = json.load(r)
    out[label] = {"prompt_eval_count": p.get("prompt_eval_count"),
                  "wall_s": round(time.time() - t0, 1)}
    print(label, out[label], flush=True)
show = urllib.request.Request("http://localhost:11434/api/show",
                              data=json.dumps({"model": "qwen2.5-coder:7b"}).encode(),
                              headers={"Content-Type": "application/json"})
with urllib.request.urlopen(show, timeout=60) as r:
    s = json.load(r)
out["modelfile_parameters"] = s.get("parameters")
out["model_context_length"] = {k: v for k, v in (s.get("model_info") or {}).items() if "context_length" in k}
print(json.dumps(out, indent=2))
open("experiments/open_weight_3/context_check/result.json", "w").write(json.dumps(out, indent=2))
