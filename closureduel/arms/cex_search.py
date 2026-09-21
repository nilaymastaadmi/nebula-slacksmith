#!/usr/bin/env python3
"""Bounded counterexample search beside the CEC gate (PREREGISTRATION.md,
amendment 1).

For a C0 netlist and a candidate whose CEC check was not PROVEN: build a
miter, then bounded model checking for 10 cycles from a common all-zero state.

  COUNTEREXAMPLE   the two differ on some input sequence within 10 cycles
  NONE_WITHIN_10   no difference found; this is not a proof of equivalence
  INCONCLUSIVE     timeout or tool error

    --control   the pre-registered positive control: the planted defect from
                test_cec_gate.py must give COUNTEREXAMPLE and the unmodified
                netlist NONE_WITHIN_10. Writes /results/cex_control.json.
    --all       every candidate whose CEC row is not PROVEN.
                Appends to /results/cex_raw.jsonl, resumable.
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_arms as R  # noqa: E402

DEPTH = 10
TIMEOUT = 600


def search(gold, gate, top, workdir, tag):
    ys = os.path.join(workdir, f"{tag}.cex.ys")
    blk = lambda net, nm: (f"read_liberty -ignore_miss_func -ignore_miss_dir {R.LIBERTY}\n"
                           f"read_verilog {net}\nsplitnets -ports\nhierarchy -top {top}\n"
                           f"flatten\nrename -top {nm}\ndesign -stash {nm}\n")
    open(ys, "w").write(blk(gold, "gold") + blk(gate, "gate") +
                        "design -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\n"
                        "miter -equiv -flatten -make_assert -ignore_gold_x gold gate miter\n"
                        "hierarchy -top miter\nasync2sync\n"
                        f"sat -verify -prove-asserts -set-init-zero -seq {DEPTH} miter\n")
    rc, out, secs = R.run([R.YOSYS, "-q", "-s", ys], timeout=TIMEOUT)
    open(ys + ".log", "w").write(out)
    if rc == 124:
        st = "INCONCLUSIVE"
    elif "proof did fail" in out or "model found: FAIL" in out:
        # Under yosys -q only the ERROR line survives: "Called with -verify and proof did fail!"
        st = "COUNTEREXAMPLE"
    elif rc == 0:
        st = "NONE_WITHIN_10"
    else:
        st = "INCONCLUSIVE"
    return {"cex": st, "cex_s": round(secs, 1), "rc": rc,
            "tail": "" if st != "INCONCLUSIVE" else out[-400:]}


def control():
    wd = "/work/gate_test"
    top = json.load(open("/designs/syn_flow/design_all.json"))["DSP"][0]
    c0, good = os.path.join(wd, "c0.v"), os.path.join(wd, "c2.v")
    bad = os.path.join(wd, "c2_functional_defect.v")
    for p in (c0, good, bad):
        if not os.path.exists(p):
            sys.exit(f"BROKEN: {p} missing; run test_cec_gate.py first")
    res = {"planted_defect": search(c0, bad, top, wd, "ctl_bad"),
           "unmodified": search(c0, good, top, wd, "ctl_good")}
    res["search_can_find"] = (res["planted_defect"]["cex"] == "COUNTEREXAMPLE"
                              and res["unmodified"]["cex"] == "NONE_WITHIN_10")
    json.dump(res, open("/results/cex_control.json", "w"), indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res["search_can_find"] else 1


def one(t):
    r = search(t["gold"], t["gate"], t["top"], os.path.dirname(t["gate"]), "vsC0")
    r.update(kind="cex", design=t["design"], cand=t["cand"], cec=t["cec"],
             harness_commit=t["commit"])
    return r


def all_(jobs, raw="/results/arms_raw.jsonl", out="/results/cex_raw.jsonl"):
    commit = R.env("HARNESS_COMMIT")
    rows = [json.loads(l) for l in open(raw)]
    evals = {(r["design"], r["cand"]): r for r in rows
             if r["kind"] == "eval" and r["run"] == 1 and r.get("status") == "OK"}
    done = set()
    if os.path.exists(out):
        done = {(json.loads(l)["design"], json.loads(l)["cand"]) for l in open(out)}
    cfg = json.load(open("/designs/syn_flow/design_all.json"))
    tasks = [dict(design=r["design"], cand=r["cand"], cec=r["cec"], commit=commit,
                  gold=evals[(r["design"], "C0")]["net_path"],
                  gate=evals[(r["design"], r["cand"])]["net_path"],
                  top=cfg[r["design"]][0])
             for r in rows if r["kind"] == "cec" and r["cec"] != "PROVEN"
             and (r["design"], r["cand"]) not in done]
    print(f"{len(tasks)} searches on {jobs} workers", flush=True)
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
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    R.init_worker()
    sys.exit(control() if a.control else all_(a.jobs) if a.all else 2)
