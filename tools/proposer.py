#!/usr/bin/env python3
"""
proposer.py -- the online proposer, and the two offline ones it replaces.

Registered in experiments/online_proposer/PREREGISTRATION.md BEFORE this file
existed. Git is the evidence for that ordering.

REPORT section 7.3 called the offline proposer an honest limit and gave a
reason that conflated two things: pre-registration forbids the EXPERIMENTER
changing the hypothesis or the prompt after seeing results, not the SYSTEM
producing a proposal in response to a measurement. This module is the
generative half the loop was missing.

Three backends, selected with --proposer:

  frozen    Read committed JSON from experiments/llm_proposer/proposals/.
            The existing behaviour, kept so every earlier run still replays.

  handoff   Write a complete request, halt, and resume when a response file
            appears. The proposer can be an agent or a person. This is what
            the registered run uses.

  cli       Shell out to `claude -p`. Full automation, no human in the loop.
            WRITTEN BUT UNTESTED: the OAuth session on the machine this was
            developed on is expired, and the registration lists reporting it
            as exercised among the void conditions.

WHAT THE PROPOSER IS NOT GIVEN, deliberately: any counterexample, and any G4
verdict. Feeding refutations back is batch 3, which was registered and then
deferred on 2026-09-02 because counterexample-feedback-to-LLM for RTL is
already published. This changes WHEN the proposer sees the design state, not
whether it is told about its own failures.
"""
import json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# The frozen v1 template is the default, so experiments/online_proposer
# reproduces byte-identically. SLACKSMITH_PROMPT points a later
# experiment at its own template rather than editing a frozen one,
# which that registration lists as a void condition.
PROMPT = os.environ.get("SLACKSMITH_PROMPT",
                        os.path.join(HERE, "proposer_prompt.md"))

# Everything above the horizontal rule in the template is documentation about
# the template. The prompt itself is what follows it.
def load_template():
    text = open(PROMPT, encoding="utf-8").read()
    marker = "\n---\n"
    return text.split(marker, 1)[1].strip() if marker in text else text


def render(ctx):
    """Fill the frozen template from live loop state. No counterexample and no
    gate verdict is ever placed here; see the module docstring."""
    ev = ctx.get("top_cells") or []
    rows = ["| instance | cell | incr ns | fanout | module |",
            "|---|---|---|---|---|"]
    for c in ev[:8]:
        rows.append("| `%s` | `%s` | %.3f | %s | %s |" % (
            c.get("inst", "?"), c.get("cell", "?"), c.get("incr_ns", 0.0),
            c.get("fanout", "?"), c.get("module", "?")))
    hist = ", ".join("it%d %+.3f" % (i, s) for i, s in ctx.get("history", []))

    return load_template().format(
        iteration=ctx["iteration"],
        clock=ctx["clock"],
        slack="%+.3f" % ctx["slack"],
        history=hist or "(first measurement)",
        verdict=ctx.get("verdict", "?"),
        fanout_share=ctx.get("fanout_delay_share", "?"),
        path_delay=ctx.get("path_delay_ns", "?"),
        cells_on_path=ctx.get("cells_on_path", "?"),
        evidence="\n".join(rows),
        module=ctx["module"],
        timing_report=ctx.get("timing_report", "(not captured)"),
        module_source=ctx["module_source"],
        proposal_id=ctx["proposal_id"],
    )


def _extract_json(text):
    """Pull the JSON object out of a reply. Tolerates a fenced block or
    surrounding prose, because the instruction not to add prose is an
    instruction, not a guarantee."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    blob = m.group(1) if m else None
    if blob is None:
        i, j = text.find("{"), text.rfind("}")
        if i < 0 or j <= i:
            return None, "no JSON object in the reply"
        blob = text[i:j + 1]
    try:
        return json.loads(blob), None
    except json.JSONDecodeError as e:
        return None, "reply is not valid JSON: %s" % e


REQUIRED = ("id", "def_id", "target_module", "latency_delta_k",
            "obligation_branch", "variant_source")


def _validate(p, ctx):
    missing = [k for k in REQUIRED if k not in p]
    if missing:
        return "missing field(s): %s" % ", ".join(missing)
    if p["target_module"] != ctx["module"]:
        return "target_module %r is not the binding module %r" % (
            p["target_module"], ctx["module"])
    src = p.get("variant_source") or ""
    if ("module %s" % ctx["module"]) not in src:
        return "variant_source does not declare module %s" % ctx["module"]
    if "endmodule" not in src:
        return "variant_source has no endmodule"
    return None


def _materialise(p, ctx, workdir):
    """Write variant_source to disk and point target_file at it, so the loop's
    existing splice/variant path can consume an online proposal unchanged."""
    vd = os.path.join(workdir, "online_variants")
    os.makedirs(vd, exist_ok=True)
    path = os.path.join(vd, "%s_%s.v" % (p["id"], ctx["module"]))
    open(path, "w", encoding="utf-8", newline="\n").write(p["variant_source"])
    p["variant_file"] = os.path.relpath(path, REPO)
    # ctx carries the real path; rtl/<module>.v is wrong for anything vendored
    # in a subdirectory, which is every AES source.
    p["target_file"] = ctx.get("target_file") or ("rtl/%s.v" % ctx["module"])

    # gate() shells out to gate_proposal.py with --proposal <path>, and frozen
    # proposals carry _path from the file they were read out of. An online
    # proposal needs the same, and having it on disk is what makes the
    # registration's "every response committed verbatim" checkable.
    pj = os.path.join(vd, "%s.json" % p["id"])
    json.dump({k: v for k, v in p.items() if not k.startswith("_")},
              open(pj, "w", encoding="utf-8"), indent=1)
    p["_path"] = pj
    return p


# --------------------------------------------------------------------------
# backends
# --------------------------------------------------------------------------
def propose_frozen(ctx, a):
    import gate_proposal
    out = []
    for f in a.proposals:
        out.extend(json.load(open(f, encoding="utf-8"))
                   if f.endswith(".json") else [])
    return out


def propose_handoff(ctx, a, workdir, timeout=1800, poll=3):
    """Write the request, halt, resume when the response appears.

    The loop stops dead here. That is the point: the transform that comes back
    was written against the state printed in the request, not chosen from a
    list written days earlier.
    """
    d = os.path.join(workdir, "handoff")
    os.makedirs(d, exist_ok=True)
    req = os.path.join(d, "REQUEST_%s.md" % ctx["proposal_id"])
    rsp = os.path.join(d, "RESPONSE_%s.json" % ctx["proposal_id"])
    open(req, "w", encoding="utf-8", newline="\n").write(render(ctx))

    print("\n" + "=" * 72)
    print("ONLINE PROPOSER, handoff backend. The loop is waiting.")
    print("  request : %s" % req)
    print("  response: %s   <- write this file" % rsp)
    print("=" * 72 + "\n", flush=True)

    t0 = time.time()
    while not os.path.exists(rsp):
        if time.time() - t0 > timeout:
            return [], "handoff timed out after %ds with no response" % timeout
        time.sleep(poll)

    text = open(rsp, encoding="utf-8").read()
    p, err = _extract_json(text)
    if err:
        return [], err
    err = _validate(p, ctx)
    if err:
        return [], err
    return [_materialise(p, ctx, workdir)], None


def propose_cli(ctx, a, workdir, timeout=None):
    """Shell out to `claude -p`. UNTESTED: see the module docstring and the
    registration's void conditions. It is committed so the automation path is
    reviewable, not so it can be claimed as exercised."""
    # 600 s was not enough. The prompt carries the whole module source, and on
    # i2c (25 KB, 3 modules) the CLI exceeded it and the loop recorded
    # "returned nothing usable" for what was a wall-clock limit, not a model
    # failure. Overridable so a slow design does not read as a bad proposer.
    if timeout is None:
        timeout = getattr(a, "cli_timeout", None) or 1800
    prompt = render(ctx)
    d = os.path.join(workdir, "cli")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "REQUEST_%s.md" % ctx["proposal_id"]),
         "w", encoding="utf-8", newline="\n").write(prompt)
    # An EMPTY claude_bin raises PermissionError, not FileNotFoundError, so the
    # handler below never sees it. That is how the first cli run died: run.sh
    # resolved the binary with `command -v claude` in a non-login shell where
    # ~/.local/bin is not on PATH, and passed "" straight through.
    if not a.claude_bin or not os.path.isfile(a.claude_bin)        and not shutil.which(a.claude_bin):
        return [], ("claude CLI path is empty or not a file: %r. Pass "
                    "--claude-bin with a real path." % a.claude_bin)
    try:
        r = subprocess.run([a.claude_bin, "-p", prompt],
                           capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, PermissionError) as e:
        return [], "claude CLI not runnable at %r: %s" % (a.claude_bin, e)
    except subprocess.TimeoutExpired:
        return [], "claude CLI timed out after %ds" % timeout
    out = r.stdout + r.stderr
    open(os.path.join(d, "RESPONSE_%s.txt" % ctx["proposal_id"]),
         "w", encoding="utf-8").write(out)
    if "Failed to authenticate" in out or "OAuth" in out:
        return [], "claude CLI is not authenticated: %s" % out.strip()[:120]
    p, err = _extract_json(out)
    if err:
        return [], err
    err = _validate(p, ctx)
    if err:
        return [], err
    return [_materialise(p, ctx, workdir)], None


def propose(ctx, a, workdir):
    """Return (proposals, error). An error is a result, not an exception: a
    proposer that returns nothing usable is a finding and the loop records it."""
    mode = getattr(a, "proposer", "frozen")
    if mode == "frozen":
        return propose_frozen(ctx, a), None
    if mode == "handoff":
        return propose_handoff(ctx, a, workdir)
    if mode == "cli":
        return propose_cli(ctx, a, workdir)
    return [], "unknown proposer backend %r" % mode
