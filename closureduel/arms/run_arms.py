#!/usr/bin/env python3
"""Run the six pre-registered classical arms (closureduel/PREREGISTRATION.md).

Runs inside closureduel:dev with the repo mounted read-only at /repo, the
designs at /designs, a fast scratch volume at /work and the results directory
at /results. Launch through arms/run.sh, which sources docker/toolpaths.sh.

Every evaluation (design x candidate x run) is one JSONL row, appended and
flushed as it completes, so an interrupted run resumes instead of restarting.
C2, C3, C4 and C5 are all answered from the 39 lever sequences: C2 is
("buffer",), C3 is ("upsize", "dnsize"), C4's candidates are among them, and
C5 draws from them. That equivalence holds only if evaluation is
deterministic, which is why every candidate runs twice.
"""
import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # closureduel/
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import select_holdout  # noqa: E402
import remeasure       # noqa: E402

SCHEMA = 1
HEAD = "+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put"
TOKEN = {"buffer": "buffer,-N,16", "upsize": "upsize", "dnsize": "dnsize"}
SEQS = [s for L in (1, 2, 3) for s in itertools.product(("buffer", "upsize", "dnsize"), repeat=L)]
CEC_TIMEOUT = 300


def env(name):
    v = os.environ.get(name, "")
    if not v:
        sys.exit(f"BROKEN: {name} is not set; launch through arms/run.sh")
    return v


YOSYS, STA, OPENROAD = env("YOSYS"), env("STA"), env("OPENROAD")
LIBERTY, STA_KIND = env("LIBERTY"), env("STA_KIND")
TECH_LEF, SC_LEF = os.environ.get("TECH_LEF", ""), os.environ.get("SC_LEF", "")


def dev_designs():
    """The 10 development designs, derived from the seal rather than typed."""
    tiered = [d for ms in select_holdout.TIERS.values() for d in ms]
    dev = [d for d in tiered if d not in select_holdout.SEALED]
    if len(tiered) != 15 or len(dev) != 10:
        sys.exit(f"BROKEN: expected 15 tiered / 10 dev designs, got {len(tiered)} / {len(dev)}")
    return dev


def run(cmd, timeout=None, cwd=None):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout + p.stderr, time.time() - t0
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + (e.stderr or "") if isinstance(e.stdout, str) else ""
        return 124, out, time.time() - t0


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def seq_cells():
    """Sequential cell names read from the liberty itself: any cell with an
    ff or latch group. Guarded: an empty set, or one missing the flop the
    whole dataset uses, is a broken instrument."""
    text = open(LIBERTY, encoding="utf-8", errors="replace").read()
    cells, cur = set(), None
    for m in re.finditer(r'cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)|\b(ff|latch)\s*\(', text):
        if m.group(1):
            cur = m.group(1)
        elif cur:
            cells.add(cur)
    if "sky130_fd_sc_hd__dfxtp_1" not in cells or len(cells) < 10:
        sys.exit(f"BROKEN: sequential-cell scan found {len(cells)} cells, dfxtp_1 missing or too few")
    return cells


SEQ = None
DU = None


def init_worker():
    global SEQ, DU
    SEQ = seq_cells()
    DU = remeasure.dont_use_flags(LIBERTY)
    if len(DU.split()) < 2:
        sys.exit(f"BROKEN: dont_use returned {len(DU.split())} words")


# ---------------------------------------------------------------- the flow

def synth(src, ext, top, out, script):
    """run_classify.sh synth(), run-1 flow, verbatim in effect."""
    rv = "read_verilog -sv" if ext == "sv" else "read_verilog"
    abc = f"abc -liberty {LIBERTY} {DU}" + (f" -script {script}" if script else "")
    cmd = [YOSYS, "-q", "-p",
           f"{rv} {src}; hierarchy -check -top {top}; synth -top {top}; "
           f"dfflibmap -liberty {LIBERTY}; {abc}; opt_clean -purge; write_verilog -noattr {out}"]
    rc, log, secs = run(cmd)
    if not (os.path.exists(out) and os.path.getsize(out) > 0):
        return "SYNTH_FAIL", secs, log[-2000:]
    txt = open(out).read()
    txt = re.sub(r"^(\s*(input|output|inout|wire|reg))\s+signed\s+", r"\1 ", txt, flags=re.M)
    open(out, "w").write(txt)
    if re.search(r"^\s*always|^\s*(input|output|inout|wire|reg)\s+signed", txt, re.M):
        return "FLOW_FAIL", secs, ""
    return "OK", secs, ""


def lef_tcl():
    return f"read_lef {TECH_LEF}\nread_lef {SC_LEF}\n" if STA_KIND == "openroad-embedded" else ""


def sta(net, top, clk, period, workdir, tag):
    """docker/smoke.sh sta_r2r(), plus report_tns. Every unrecognised
    failure is an instrument failure, never a design fact."""
    tcl = os.path.join(workdir, f"{tag}.tcl")
    rpt = os.path.join(workdir, f"{tag}.rpt")
    open(tcl, "w").write(
        f"{lef_tcl()}read_liberty {LIBERTY}\nread_verilog {net}\nlink_design {top}\n"
        f"create_clock -name clk -period {period} [get_ports {clk}]\n"
        f"report_checks -path_delay max -from [all_registers -clock_pins] "
        f"-to [all_registers -data_pins] -group_path_count 1 -digits 3\n"
        f"report_tns -digits 3\n")
    rc, out, secs = run([STA, "-no_init", "-no_splash", "-exit", tcl])
    open(rpt, "w").write(out)
    if re.search(r"syntax error", out):
        return {"status": "STA_READ_FAIL"}
    if re.search(r"report_checks command failed", out):
        return {"status": "NO_PATH"}
    if re.search(r"^\[ERROR|^Error", out, re.M):
        return {"status": "STA_ERROR"}
    s = re.findall(r"(-?[0-9.]+)\s+slack \((?:MET|VIOLATED)\)", out)
    t = re.findall(r"^tns(?: max)?\s+(-?[0-9.]+)", out, re.M)
    if not s or not t:
        return {"status": "STA_ERROR"}
    return {"status": "OK", "wns": float(s[-1]), "tns": float(t[-1]), "report": rpt}


def netinfo(net, top, workdir, tag):
    """Area, cell count, flop count and the port signature, from one Yosys
    read with liberty cell definitions. Ports come from Yosys' own JSON, so
    two different netlist writers are compared on meaning, not formatting."""
    js = os.path.join(workdir, f"{tag}.ports.json")
    rc, out, _ = run([YOSYS, "-q", "-p",
                      f"read_liberty -lib {LIBERTY}; read_verilog {net}; hierarchy -top {top}; "
                      f"tee -o {js}.stat stat -liberty {LIBERTY}; write_json {js}"])
    area = None
    if os.path.exists(js + ".stat"):
        m = re.findall(r"Chip area for (?:top )?module '\\?[^']*':\s*([0-9.]+)", open(js + ".stat").read())
        area = float(m[-1]) if m else None
    ports = None
    if os.path.exists(js):
        mod = json.load(open(js))["modules"].get(top, {})
        ports = sorted((n, p["direction"], len(p["bits"])) for n, p in mod.get("ports", {}).items())
    cells = re.findall(r"^\s*(sky130_fd_sc_hd__\w+)\s+\S+\s*\(", open(net).read(), re.M)
    return {"area": area, "cells": len(cells),
            "flops": sum(1 for c in cells if c in SEQ), "ports": ports}


def cec(gold, gate, top, workdir, tag):
    """The committed G6 recipe. NOT_PROVEN means equiv_status -assert found
    unproven compare points; it is not a demonstration of inequivalence."""
    ys = os.path.join(workdir, f"{tag}.cec.ys")
    blk = lambda net, nm: (f"read_liberty -ignore_miss_func -ignore_miss_dir {LIBERTY}\n"
                           f"read_verilog {net}\nsplitnets -ports\nhierarchy -top {top}\n"
                           f"flatten\nrename -top {nm}\ndesign -stash {nm}\n")
    open(ys, "w").write(blk(gold, "gold") + blk(gate, "gate") +
                        "design -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\n"
                        "equiv_make gold gate equiv\nprep -flatten -top equiv\nasync2sync\n"
                        "equiv_struct\nequiv_simple -seq 10\nequiv_induct -seq 4\nequiv_status -assert\n")
    rc, out, secs = run([YOSYS, "-q", "-s", ys], timeout=CEC_TIMEOUT)
    open(ys + ".log", "w").write(out)
    unproven = re.findall(r"Found (\d+) unproven", out)
    if rc == 0:
        st = "PROVEN"
    elif rc == 124:
        st = "TIMEOUT"
    elif unproven:
        st = "NOT_PROVEN"
    else:
        st = "ERROR"
    return {"cec": st, "cec_unproven": int(unproven[-1]) if unproven else 0, "cec_s": round(secs, 1)}


def repair(c0net, top, clk, period, out, workdir):
    """C1: stock repair_design -pre_placement. No floorplan, no placement,
    no parasitics (PREREGISTRATION.md, C1)."""
    if not (TECH_LEF and SC_LEF):
        return "TOOL_ERROR", 0.0, "C1 needs TECH_LEF and SC_LEF; OpenROAD refuses a netlist without them"
    tcl = os.path.join(workdir, "c1.tcl")
    open(tcl, "w").write(
        f"read_lef {TECH_LEF}\nread_lef {SC_LEF}\nread_liberty {LIBERTY}\nread_verilog {c0net}\n"
        f"link_design {top}\ncreate_clock -name clk -period {period} [get_ports {clk}]\n"
        f"repair_design -pre_placement\nwrite_verilog {out}\n")
    rc, log, secs = run([OPENROAD, "-no_init", "-no_splash", "-exit", tcl])
    open(os.path.join(workdir, "c1.log"), "w").write(log)
    if rc != 0 or not (os.path.exists(out) and os.path.getsize(out) > 0):
        return "TOOL_ERROR", secs, log[-2000:]
    bufs = re.findall(r"Inserted (\d+) buffers", log)
    return "OK", secs, f"inserted={bufs[-1] if bufs else 0} est0027={'EST-0027' in log}"


# ---------------------------------------------------------------- tasks

def cand_label(c):
    return "C0" if c is None else ("C1" if c == "C1" else "S:" + "+".join(c))


def eval_task(t):
    """One candidate, one run: build its netlist, time it at the design's
    period, measure it. Returns a row."""
    init_worker() if SEQ is None else None
    d, cand, runno = t["design"], t["cand"], t["run"]
    wd = os.path.join(t["work"], d, cand_label(cand).replace(":", "_").replace("+", "-"), f"run{runno}")
    os.makedirs(wd, exist_ok=True)
    net = os.path.join(wd, "net.v")
    row = {"schema": SCHEMA, "kind": "eval", "design": d, "cand": cand_label(cand), "run": runno,
           "period": t["period"], "harness_commit": t["commit"], "image": t["image"],
           "sta_kind": STA_KIND, "liberty_sha256": t["lib_sha"]}
    t0 = time.time()
    if cand == "C1":
        st, secs, note = repair(t["c0net"], t["top"], t["clk"], t["period"], net, wd)
        row["note"] = note
    else:
        script = None if cand is None else HEAD + ";" + ";".join(TOKEN[x] for x in cand)
        st, secs, note = synth(t["src"], t["ext"], t["top"], net, script)
    row["build"] = st
    if st != "OK":
        row.update(status=st, wall_s=round(time.time() - t0, 1), detail=note[-600:])
        return row
    s = sta(net, t["top"], t["clk"], t["period"], wd, "tight")
    row.update({k: v for k, v in s.items() if k != "report"}, net_sha256=sha(net), net_path=net)
    row.update(netinfo(net, t["top"], wd, "info"))
    row["wall_s"] = round(time.time() - t0, 1)
    return row


def cec_task(t):
    init_worker() if SEQ is None else None
    wd = os.path.dirname(t["gate"])
    r = cec(t["gold"], t["gate"], t["top"], wd, "vsC0")
    r.update(schema=SCHEMA, kind="cec", design=t["design"], cand=t["cand"],
             harness_commit=t["commit"], image=t["image"])
    return r


# ---------------------------------------------------------------- driver

def load_done(path):
    done = set()
    if os.path.exists(path):
        for line in open(path):
            r = json.loads(line)
            done.add((r["kind"], r["design"], r["cand"], r.get("run")))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", nargs="*", help="subset of development designs")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--cec-jobs", type=int, default=3)
    ap.add_argument("--out", default="/results/arms_raw.jsonl")
    ap.add_argument("--work", default="/work")
    ap.add_argument("--dr", default="/designs")
    a = ap.parse_args()

    init_worker()
    commit, image = env("HARNESS_COMMIT"), env("IMAGE_ID")
    lib_sha = sha(LIBERTY)
    dev = dev_designs()
    designs = a.designs or dev
    for d in designs:
        if d in select_holdout.SEALED:
            sys.exit(f"REFUSED: {d} is in the sealed holdout (SPEC.md 2.3)")
        if d not in dev:
            sys.exit(f"REFUSED: {d} is not a development design")
    cfg = json.load(open(os.path.join(a.dr, "syn_flow", "design_all.json")))
    if len(SEQS) != 39:
        sys.exit(f"BROKEN: {len(SEQS)} sequences, registered 39")

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    done = load_done(a.out)
    outf = open(a.out, "a")

    def emit(row):
        outf.write(json.dumps(row, sort_keys=True) + "\n")
        outf.flush()

    # Phase A: C0 twice per design, the period, and the classifier verdict.
    base = {}
    for d in designs:
        top, clk, _rst, ext = cfg[d]
        src = os.path.join(a.dr, "rtl_dataset", f"{d}.v0.{ext}")
        if not os.path.getsize(src):
            sys.exit(f"BROKEN: empty source {src}")
        wd = os.path.join(a.work, d, "C0_period")
        os.makedirs(wd, exist_ok=True)
        net = os.path.join(wd, "net.v")
        st, _, note = synth(src, ext, top, net, None)
        if st != "OK":
            emit({"schema": SCHEMA, "kind": "design", "design": d, "cand": "C0", "run": 0,
                  "status": st, "detail": note[-600:], "harness_commit": commit})
            print(f"{d}: C0 {st}, design reported as failed, not replaced", flush=True)
            continue
        loose = sta(net, top, clk, 1000, wd, "loose")
        if loose["status"] != "OK":
            emit({"schema": SCHEMA, "kind": "design", "design": d, "cand": "C0", "run": 0,
                  "status": loose["status"], "harness_commit": commit})
            print(f"{d}: loose STA {loose['status']}", flush=True)
            continue
        required = round(1000.0 - loose["wns"], 3)
        period = round(0.9 * required, 3)
        tight = sta(net, top, clk, period, wd, "tight")
        rc, out, _ = run([sys.executable, os.path.join(REPO, "tools", "classify_path.py"),
                          "--report", tight.get("report", ""), "--netlist", net, "--top", top, "--json"])
        try:
            verdict = json.loads(out[out.index("{"):])["verdict"]
        except Exception:
            verdict = "UNPARSED"
        base[d] = dict(top=top, clk=clk, ext=ext, src=src, period=period, c0net=net)
        if ("design", d, "C0", 0) not in done:
            emit({"schema": SCHEMA, "kind": "design", "design": d, "cand": "C0", "run": 0,
                  "status": "OK", "required": required, "period": period, "verdict": verdict,
                  "c0_net_sha256": sha(net), "harness_commit": commit, "image": image})
        print(f"{d}: required={required} period={period} verdict={verdict}", flush=True)

    # Phase B: every candidate, twice.
    tasks = []
    for d, b in base.items():
        for cand in [None, "C1"] + SEQS:
            for runno in (1, 2):
                if ("eval", d, cand_label(cand), runno) in done:
                    continue
                tasks.append(dict(design=d, cand=cand, run=runno, work=a.work, commit=commit,
                                  image=image, lib_sha=lib_sha, **b))
    print(f"phase B: {len(tasks)} evaluations on {a.jobs} workers", flush=True)
    evals = {}
    with ProcessPoolExecutor(a.jobs, initializer=init_worker) as ex:
        futs = [ex.submit(eval_task, t) for t in tasks]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            emit(r)
            if i % 25 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} evaluations", flush=True)
    for line in open(a.out):
        r = json.loads(line)
        if r["kind"] == "eval" and r["run"] == 1 and r.get("status") == "OK":
            evals[(r["design"], r["cand"])] = r

    # Phase C: CEC of every run-1 candidate against its design's C0 run-1 netlist.
    ctasks = []
    for (d, cand), r in evals.items():
        if cand == "C0" or ("cec", d, cand, None) in done:
            continue
        c0 = evals.get((d, "C0"))
        if not c0:
            continue
        ctasks.append(dict(design=d, cand=cand, gold=c0["net_path"], gate=r["net_path"],
                           top=base[d]["top"], commit=commit, image=image))
    print(f"phase C: {len(ctasks)} equivalence checks on {a.cec_jobs} workers", flush=True)
    with ProcessPoolExecutor(a.cec_jobs, initializer=init_worker) as ex:
        futs = [ex.submit(cec_task, t) for t in ctasks]
        for i, f in enumerate(as_completed(futs), 1):
            emit(f.result())
            if i % 25 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} checks", flush=True)
    outf.close()
    print("done", flush=True)


if __name__ == "__main__":
    main()
