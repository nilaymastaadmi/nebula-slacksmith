#!/usr/bin/env python3
"""Second equivalence checker: PDR on a miter (PREREGISTRATION.md, amendment 2).

Adapted from the checker validated in experiments/slackbench/run_bench.py
(check_miter_pdr: SBY, mode prove, engine abc pdr, a Verilog miter module).
Two adaptations, both forced by gate-level input:

- Each netlist is read with liberty functional models and flattened before
  it is renamed, so the miter instantiates plain logic, not library cells.
- The common start state is all-zero on every flop in both copies
  (`setundef -zero -init`), not a forced reset. The reset ports differ in name
  and polarity across designs, and gold and gate here share one flop set, so
  identical initial states are well defined. SlackBench's own note applies:
  without a defined start state PDR flags even trivially equivalent pairs.

  PROVEN          PDR proved the outputs equal in every reachable state
  COUNTEREXAMPLE  PDR found an input sequence on which they differ
  UNRESOLVED      timeout or UNKNOWN
  ERROR           the run broke; never read as a verdict

    --control   the three registered controls; writes /results/pdr_control.json
    --all       every candidate whose registered CEC is not PROVEN;
                appends to /results/pdr_raw.jsonl, resumable
"""
import argparse
import json
import os
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_arms as R  # noqa: E402

TIMEOUT = 600
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def vname(n):
    return n if IDENT.match(n) else "\\" + n + " "


def ports_of(net, top, wd):
    p = R.netinfo(net, top, wd, "pdr_ports")["ports"]
    if not p:
        raise RuntimeError(f"no ports read from {net}")
    return p


def write_miter(path, ports):
    ins = [(n, w) for n, d, w in ports if d == "input"]
    outs = [(n, w) for n, d, w in ports if d == "output"]
    if any(d not in ("input", "output") for _, d, _ in ports):
        raise RuntimeError("inout ports are not supported")
    if not outs:
        raise RuntimeError("design has no outputs to compare")
    rng = lambda w: f"[{w - 1}:0] " if w > 1 else ""
    L = ["module cd_miter(" + ", ".join(f"input wire {rng(w)}{vname(n)}" for n, w in ins) + ");"]
    for n, w in outs:
        L.append(f"  wire {rng(w)}{vname(n + '__gold')}, {vname(n + '__gate')};")
    for inst, sfx in (("gold_dut", "__gold"), ("gate_dut", "__gate")):
        conns = [f".{vname(n)}({vname(n)})" for n, _ in ins] + \
                [f".{vname(n)}({vname(n + sfx)})" for n, _ in outs]
        L.append(f"  {inst} u{sfx} (" + ", ".join(conns) + ");")
    L.append("  always @(*) begin")
    L += [f"    assert ({vname(n + '__gold')} == {vname(n + '__gate')});" for n, _ in outs]
    L += ["  end", "endmodule", ""]
    open(path, "w").write("\n".join(L))


def sby_cfg(gold, gate, miter, top):
    load = lambda net, nm: (f"read_liberty -ignore_miss_func -ignore_miss_dir {R.LIBERTY}\n"
                            f"read_verilog {net}\nhierarchy -top {top}\nflatten\n"
                            f"rename {top} {nm}\ndesign -stash {nm}\n")
    # aigsmt none: report a FAIL without replaying the AIGER witness through an
    # SMT solver; the first control run died in that replay (ERROR, "Could not
    # determine aigsmt status") on a counterexample found in 7 s.
    return ("[options]\nmode prove\naigsmt none\n"
            f"timeout {TIMEOUT}\n\n[engines]\nabc pdr\n\n[script]\n"
            + load(gold, "gold_dut") + load(gate, "gate_dut") +
            "design -copy-from gold_dut -as gold_dut gold_dut\n"
            "design -copy-from gate_dut -as gate_dut gate_dut\n"
            f"read_verilog -formal {miter}\nprep -top cd_miter\nflatten\n"
            "setundef -zero -init\n\n"
            f"[files]\n{miter}\n")


def check(gold, gate, top, wd, tag):
    d = os.path.join(wd, f"pdr_{tag}")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    try:
        miter = os.path.join(d, "miter.v")
        write_miter(miter, ports_of(gold, top, d))
    except Exception as e:  # a harness defect, never a verdict
        return {"pdr": "ERROR", "pdr_s": 0.0, "detail": str(e)[:300]}
    cfg = os.path.join(d, "run.sby")
    open(cfg, "w").write(sby_cfg(gold, gate, miter, top))
    rc, out, secs = R.run(["sby", "-f", "-d", os.path.join(d, "job"), cfg], timeout=TIMEOUT + 120)
    open(os.path.join(d, "sby.log"), "w", errors="replace").write(out)
    m = re.findall(r"DONE \((PASS|FAIL|UNKNOWN|TIMEOUT|ERROR)", out)
    last = m[-1] if m else ("TIMEOUT" if rc == 124 else "ERROR")
    st = {"PASS": "PROVEN", "FAIL": "COUNTEREXAMPLE",
          "UNKNOWN": "UNRESOLVED", "TIMEOUT": "UNRESOLVED"}.get(last, "ERROR")
    r = {"pdr": st, "pdr_s": round(secs, 1), "sby_status": last}
    if st == "ERROR":
        r["detail"] = "\n".join(l for l in out.splitlines() if "ERROR" in l or "rror" in l)[-500:]
    return r


def control():
    cfg = json.load(open("/designs/syn_flow/design_all.json"))
    g = "/work/gate_test"
    dsp, aes = cfg["DSP"][0], cfg["aes"][0]
    for p in (f"{g}/c0.v", f"{g}/c2.v", f"{g}/c2_functional_defect.v",
              "/work/aes/C0/run1/net.v", "/work/aes/S_upsize-dnsize/run1/net.v"):
        if not os.path.exists(p):
            sys.exit(f"BROKEN: {p} missing")
    out = "/work/pdr_control"
    os.makedirs(out, exist_ok=True)
    res = {
        "planted_defect": check(f"{g}/c0.v", f"{g}/c2_functional_defect.v", dsp, out, "planted"),
        "unmodified_dsp": check(f"{g}/c0.v", f"{g}/c2.v", dsp, out, "unmodified"),
        "registered_proven_aes_sizing": check("/work/aes/C0/run1/net.v",
                                              "/work/aes/S_upsize-dnsize/run1/net.v", aes, out, "aes_sizing"),
    }
    res["controls_pass"] = (res["planted_defect"]["pdr"] == "COUNTEREXAMPLE"
                            and res["unmodified_dsp"]["pdr"] == "PROVEN"
                            and res["registered_proven_aes_sizing"]["pdr"] == "PROVEN")
    json.dump(res, open("/results/pdr_control.json", "w"), indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res["controls_pass"] else 1


def one(t):
    r = check(t["gold"], t["gate"], t["top"], os.path.dirname(t["gate"]), "vsC0")
    r.update(kind="pdr", design=t["design"], cand=t["cand"], cec=t["cec"], harness_commit=t["commit"])
    return r


def all_(jobs, raw="/results/arms_raw.jsonl", out="/results/pdr_raw.jsonl"):
    ctl = json.load(open("/results/pdr_control.json")) if os.path.exists("/results/pdr_control.json") else {}
    if not ctl.get("controls_pass"):
        sys.exit("REFUSED: controls have not passed (/results/pdr_control.json); run --control first")
    commit = R.env("HARNESS_COMMIT")
    rows = [json.loads(l) for l in open(raw)]
    ev = {(r["design"], r["cand"]): r for r in rows
          if r["kind"] == "eval" and r["run"] == 1 and r.get("status") == "OK"}
    done = set()
    if os.path.exists(out):
        done = {(json.loads(l)["design"], json.loads(l)["cand"]) for l in open(out)}
    cfg = json.load(open("/designs/syn_flow/design_all.json"))
    tasks = [dict(design=r["design"], cand=r["cand"], cec=r["cec"], commit=commit,
                  gold=ev[(r["design"], "C0")]["net_path"], gate=ev[(r["design"], r["cand"])]["net_path"],
                  top=cfg[r["design"]][0])
             for r in rows if r["kind"] == "cec" and r["cec"] != "PROVEN"
             and (r["design"], r["cand"]) not in done]
    if not tasks and not done:
        sys.exit("BROKEN: no unproven candidates found in the raw rows")
    print(f"{len(tasks)} PDR checks on {jobs} workers ({len(done)} already done)", flush=True)
    with open(out, "a") as f, ProcessPoolExecutor(jobs) as ex:
        for i, fu in enumerate(as_completed([ex.submit(one, t) for t in tasks]), 1):
            f.write(json.dumps(fu.result(), sort_keys=True) + "\n")
            f.flush()
            if i % 10 == 0 or i == len(tasks):
                print(f"  {i}/{len(tasks)}", flush=True)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    R.init_worker()
    sys.exit(control() if a.control else all_(a.jobs) if a.all else 2)
