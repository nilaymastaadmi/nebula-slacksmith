#!/usr/bin/env python3
"""
slacksmith.py -- the closed loop, in one command.

Everything else in this repository is an experiment that answered one
question. This is the tool those answers add up to. It runs:

    measure  ->  classify  ->  route  ->  apply  ->  re-measure  ->  repeat

and stops when every reported clock group meets its constraint, or when no
lever is left, or at --max-iters.

WHY THERE ARE TWO ROUTERS, AND WHY THAT IS THE POINT

  1. Route the FIX by measured path pathology. tools/classify_path.py scores
     what share of a path's delay comes from cells driving many loads. A
     fanout-dominated path goes to a physical lever; no RTL rewrite shortens a
     net's load delay. A depth-dominated path goes to the RTL proposer. On this
     benchmark the binding paths measured 59% to 91% fanout-attributable, and
     the physical lever beat the best formally-proven RTL transform by 3.6x
     (mapping level) and 11.3x (with placement parasitics).

  2. Route the PROOF OBLIGATION by declared transform type. A k=0 transform
     gets combinational equivalence, k>0 rigid gets a k-padded miter, elastic
     gets stream equivalence, re-encoded state gets mapped-state equivalence.
     tools/gate_proposal.py owns this. Nothing here overrides it: a transform
     whose obligation is not discharged is never accepted, and a transform
     whose obligation is UNRESOLVED is never counted as PROVEN.

HONEST LIMIT ON "CLOSED LOOP". The proposer is offline. This loop does not
call a model; it draws from a directory of proposals that were frozen before
any gate ran (see the two PREREGISTRATION.md files). That is deliberate: the
anti-tuning rule in those registrations forbids generating a proposal after
seeing a gate result, and a loop that invented proposals mid-run would break
it. So the RTL lever here selects, gates and measures. It does not generate.

Engines:
  --engine sta        zero-parasitic OpenSTA. Physical lever is ABC
                      buffer/upsize/dnsize. Fast, good for iterating.
  --engine openroad   floorplan + global placement + placement parasitics.
                      Physical lever is repair_design. Slower, and the only
                      one whose numbers contain wires.

Every decision, its evidence and its outcome are appended to
<workdir>/decisions.jsonl, and a readable summary is written to
<workdir>/SUMMARY.md.

Usage:
  python3 tools/slacksmith.py --sdc sdc/bench_top_v2.sdc \\
      --liberty ~/sta_work/sky130hd_tt.lib \\
      --sta-bin ~/tools/OpenSTA/build/sta \\
      --clock clk_a --clock clk_b --clock clk_e \\
      --proposals experiments/llm_proposer_aes/proposals \\
      --workdir ~/slacksmith_run --engine sta
"""
import argparse, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import remeasure
import gate_proposal
from classify_path import classify

REPO = os.path.dirname(HERE)

# The buffering physical lever. Yosys ships this in its -liberty -constr
# script and not in the plain -liberty script, which is why this flow was not
# running it. Commas become spaces when abc parses a +script argument.
BUFFER_SCRIPT = ("+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;"
                 "&get,-n;&dch,-f;&nf;&put;buffer,-N,16;upsize;dnsize")


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def split_reports(sta_out, clocks):
    """Split one OpenSTA run's output into a per-clock path report."""
    out = {}
    for c in clocks:
        m = re.search(rf"---CLOCK:{re.escape(c)}---(.*?)(?=---CLOCK:|\Z)",
                      sta_out, re.S)
        out[c] = m.group(1) if m else ""
    return out


# ----------------------------------------------------------------- measure

def measure_sta(a, rtl_files, workdir, tag, abc_script):
    """Synthesize and time. Returns (slacks, reports, netlist_path)."""
    d = os.path.join(workdir, tag)
    os.makedirs(d, exist_ok=True)
    net = remeasure.synth_bench_top(
        a.yosys_bin, a.rtl_dir, rtl_files, a.liberty, d, "mapped.v",
        extra_yosys_top=a.top, abc_script=abc_script)
    slacks, out = remeasure.sta_slack(
        a.sta_bin, a.liberty, net, a.top, a.sdc, a.clocks, d)
    return slacks, split_reports(out, a.clocks), net


OR_TCL = """read_lef {plat}/lef/sky130_fd_sc_hd.tlef
read_lef {plat}/lef/sky130_fd_sc_hd_merged.lef
read_liberty {lib}
read_verilog {net}
link_design {top}
read_sdc {sdc}
initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2.0 -site unithd
source {plat}/make_tracks.tcl
place_pins -hor_layers met3 -ver_layers met2
source {plat}/setRC.tcl
global_placement -density 0.60
estimate_parasitics -placement
{repair}
{reports}
write_verilog {outnet}
exit
"""


def measure_openroad(a, netlist, workdir, tag, do_repair):
    d = os.path.join(workdir, tag)
    os.makedirs(d, exist_ok=True)
    repair = ("repair_design\ndetailed_placement\nestimate_parasitics -placement"
              if do_repair else "")
    reports = "\n".join(
        f'puts "---CLOCK:{c}---"\n'
        f'report_checks -path_delay max -to [get_clocks {c}] '
        f'-group_count 1 -digits 3' for c in a.clocks)
    tcl = OR_TCL.format(plat=a.platform, lib=a.liberty, net=netlist, top=a.top,
                        sdc=a.sdc, repair=repair, reports=reports,
                        outnet=os.path.join(d, "out.v"))
    tp = os.path.join(d, "flow.tcl")
    open(tp, "w").write(tcl)
    r = sh([a.openroad_bin, "-no_init", "-exit", tp])
    out = r.stdout + r.stderr
    open(os.path.join(d, "flow.log"), "w", encoding="utf-8",
         errors="replace").write(out)
    reports_by_clk = split_reports(out, a.clocks)
    slacks = {}
    for c in a.clocks:
        m = re.findall(r"([\-0-9.]+)\s+slack \((?:MET|VIOLATED)\)",
                       reports_by_clk[c])
        slacks[c] = float(m[-1]) if m else None
    return slacks, reports_by_clk, os.path.join(d, "out.v")


# ----------------------------------------------------------------- routing

def route(verdict):
    if verdict in ("FANOUT_DOMINATED", "MIXED"):
        return "physical"
    if verdict == "DEPTH_DOMINATED":
        return "rtl"
    return "none"


def load_proposals(dirs):
    props = []
    for d in dirs:
        d = os.path.join(REPO, d) if not os.path.isabs(d) else d
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                p = json.load(open(os.path.join(d, f), encoding="utf-8"))
                p["_path"] = os.path.join(d, f)
                props.append(p)
    return props


def gate(a, prop, workdir, tag):
    """Run G1 to G4 via tools/gate_proposal.py. Returns its JSON verdict."""
    tf = prop.get("target_file", "rtl/rv32i_core.v")
    mod = prop.get("target_module", "rv32i_core")
    outs = a.gate_outputs.get(mod)
    ins = a.gate_inputs.get(mod)
    cmd = [sys.executable, os.path.join(HERE, "gate_proposal.py"),
           "--proposal", prop["_path"],
           "--rtl", os.path.join(REPO, tf),
           "--module", mod,
           "--workdir", os.path.join(workdir, "gates", tag),
           "--repo", REPO, "--timeout", str(a.gate_timeout)]
    if mod != "rv32i_core":
        cmd += ["--clk", a.gate_clk.get(mod, "clk"),
                "--rst", a.gate_rst.get(mod, "rst_n")]
    if outs:
        cmd += ["--outputs", outs]
    if ins:
        cmd += ["--inputs", ins]
    r = sh(cmd)
    try:
        return json.loads(r.stdout[r.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return {"G4": "HARNESS_ERROR", "stderr": r.stderr[-800:]}


# -------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl-dir", default=os.path.join(REPO, "rtl"))
    ap.add_argument("--top", default="bench_top")
    ap.add_argument("--sdc", required=True)
    ap.add_argument("--liberty", required=True)
    ap.add_argument("--sta-bin", default=os.path.expanduser("~/tools/OpenSTA/build/sta"))
    ap.add_argument("--yosys-bin", default=os.path.expanduser("~/tools/oss-cad-suite/bin/yosys"))
    ap.add_argument("--openroad-bin", default=os.path.expanduser("~/or_env/bin/openroad"))
    ap.add_argument("--platform", default=os.path.expanduser("~/orfs/flow/platforms/sky130hd"))
    ap.add_argument("--clock", action="append", dest="clocks", required=True)
    ap.add_argument("--proposals", action="append", default=[],
                    help="directory of frozen proposals; repeatable")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--engine", choices=["sta", "openroad"], default="sta")
    ap.add_argument("--max-iters", type=int, default=6)
    ap.add_argument("--gate-timeout", type=int, default=420)
    a = ap.parse_args()

    a.liberty = os.path.expanduser(a.liberty)
    a.sta_bin = os.path.expanduser(a.sta_bin)
    a.yosys_bin = os.path.expanduser(a.yosys_bin)
    a.workdir = os.path.expanduser(a.workdir)
    a.sdc = a.sdc if os.path.isabs(a.sdc) else os.path.join(REPO, a.sdc)
    os.makedirs(a.workdir, exist_ok=True)

    # Per-module gate wiring. Only what gate_proposal.py cannot infer.
    a.gate_outputs = {"aes_key_mem": "round_key:128,ready:1,sboxw:32"}
    a.gate_inputs = {"aes_key_mem": "key:256,keylen:1,init:1,round:4,new_sboxw:32"}
    a.gate_clk = {"aes_key_mem": "clk"}
    a.gate_rst = {"aes_key_mem": "reset_n"}

    # The dont_use list must be non-empty. A silently empty one reintroduces
    # the lpflow artifact that contaminated eight commits of this project.
    ndu = len(remeasure.dont_use_flags(a.liberty).split())
    if ndu < 2:
        sys.exit(f"FATAL: dont_use returned {ndu} flags, expected >= 2")

    log_path = os.path.join(a.workdir, "decisions.jsonl")
    log = open(log_path, "a", encoding="utf-8")

    def record(**kw):
        kw["t"] = round(time.time() - t0, 1)
        log.write(json.dumps(kw) + "\n")
        log.flush()
        return kw

    t0 = time.time()
    rtl_files = list(remeasure.BENCH_TOP_FILES)
    file_subs = {}          # original rtl file -> accepted variant path
    physical_applied = False
    tried = set()
    history = []
    # An RTL proposal is provisionally applied, then confirmed or reverted on
    # the NEXT measurement. Passing the formal gate means it is correct, not
    # that it helps: batch 1 had 4 transforms formally proven and 3 of them
    # made timing worse. G5 is a separate bar and this is where it is applied.
    pending = None

    print(f"dont_use flags: {ndu}")
    print(f"engine: {a.engine}   clocks: {', '.join(a.clocks)}")

    for it in range(1, a.max_iters + 1):
        print(f"\n=== iteration {it} ===")
        files = [file_subs.get(f, f) for f in rtl_files]

        abc = BUFFER_SCRIPT if (physical_applied and a.engine == "sta") else None
        slacks, reports, net = measure_sta(a, files, a.workdir, f"it{it}", abc)

        if a.engine == "openroad":
            slacks, reports, net = measure_openroad(
                a, net, a.workdir, f"it{it}_or", physical_applied)

        shown = "  ".join(f"{c}={slacks[c]}" for c in a.clocks)
        print(f"measure: {shown}")
        record(iter=it, step="measure", engine=a.engine, slacks=slacks,
               physical_applied=physical_applied,
               rtl_applied=sorted(file_subs.values()))
        history.append((it, dict(slacks)))

        # G5 on anything the RTL lever applied last iteration.
        if pending:
            now = slacks.get(pending["clock"])
            before = pending["prev_slack"]
            if now is None or now <= before:
                file_subs.pop(pending["key"], None)
                print(f"  REVERT {pending['id']}: {pending['clock']} "
                      f"{before} -> {now}, no improvement. G4 passed, G5 did not.")
                record(iter=it, step="revert", proposal=pending["id"],
                       clock=pending["clock"], before=before, after=now,
                       reason="G5_no_improvement")
                pending = None
                continue
            print(f"  CONFIRM {pending['id']}: {pending['clock']} "
                  f"{before} -> {now} ({now - before:+.3f})")
            record(iter=it, step="confirm", proposal=pending["id"],
                   clock=pending["clock"], before=before, after=now,
                   gain=round(now - before, 3))
            pending = None

        violated = [c for c in a.clocks
                    if slacks.get(c) is not None and slacks[c] < 0]
        if not violated:
            print("ALL REPORTED GROUPS MEET. stopping.")
            record(iter=it, step="stop", reason="all_met", slacks=slacks)
            break

        worst = min(violated, key=lambda c: slacks[c])
        cls = classify(reports[worst], net, top=a.top)
        lever = route(cls["verdict"])
        print(f"classify {worst}: {cls['verdict']} "
              f"(fanout share {cls.get('fanout_delay_share')}) -> {lever}")
        record(iter=it, step="classify", clock=worst, verdict=cls["verdict"],
               fanout_delay_share=cls.get("fanout_delay_share"),
               path_delay_ns=cls.get("path_delay_ns"),
               cells_on_path=cls.get("cells_on_path"),
               top_cells=cls.get("top_cells"), lever=lever)

        if lever == "physical":
            if physical_applied:
                print("physical lever already applied and the group still "
                      "violates. no lever left for it.")
                record(iter=it, step="stop", reason="physical_exhausted",
                       clock=worst)
                break
            physical_applied = True
            print(f"apply: physical lever "
                  f"({'repair_design' if a.engine=='openroad' else 'abc buffer/upsize/dnsize'})")
            record(iter=it, step="apply", lever="physical",
                   how=("repair_design" if a.engine == "openroad"
                        else "abc buffer -N 16; upsize; dnsize"))
            continue

        if lever == "rtl":
            # Only consider proposals that touch a module actually ON the
            # binding path. Without this the loop will happily gate an AES
            # transform against a violation in the RV32I domain: formally
            # correct, and incapable of moving the number. The classifier
            # already names the owning module of every cell on the path.
            on_path = {c.get("module") for c in (cls.get("top_cells") or [])
                       if c.get("module")}
            props = [p for p in load_proposals(a.proposals)
                     if p["id"] not in tried
                     and p.get("target_module") in on_path]
            if not props:
                print(f"no untried proposal targets the binding modules "
                      f"{sorted(on_path)}.")
                record(iter=it, step="stop", reason="no_proposal_on_path",
                       binding_modules=sorted(on_path))
                break
            accepted = False
            for p in props:
                tried.add(p["id"])
                g = gate(a, p, a.workdir, p["id"])
                v = str(g.get("G4", "?"))
                print(f"  gate {p['id']} ({g.get('def_id')}): "
                      f"G3={g.get('G3')} G4={v}")
                record(iter=it, step="gate", proposal=p["id"],
                       def_id=g.get("def_id"), declared_k=g.get("declared_k"),
                       G1=g.get("G1"), G2=g.get("G2"), G3=g.get("G3"), G4=v)
                # Only PROVEN is accepted. UNRESOLVED is NOT a pass.
                if not v.startswith("PROVEN"):
                    continue
                # Batch 2 ships a whole rewritten module (variant_file).
                # Batch 1 ships an anchor splice, which is materialised here
                # with gate_proposal's own splice(), so the file the loop
                # synthesizes is built the same way the gate built the one it
                # proved.
                tf = p.get("target_file") or f"rtl/{p['target_module']}.v"
                key = tf[len("rtl/"):] if tf.startswith("rtl/") else tf
                if key not in rtl_files:
                    record(iter=it, step="skip", proposal=p["id"],
                           reason=f"target {key} not in the file list")
                    continue
                vf = p.get("variant_file")
                if vf:
                    variant_abs = os.path.join(REPO, vf)
                else:
                    try:
                        src_txt = open(os.path.join(REPO, tf),
                                       encoding="utf-8").read()
                        spliced = gate_proposal.splice(src_txt, p)
                    except (KeyError, SystemExit) as e:
                        record(iter=it, step="skip", proposal=p["id"],
                               reason=f"splice failed: {e}")
                        continue
                    vd = os.path.join(a.workdir, "variants")
                    os.makedirs(vd, exist_ok=True)
                    variant_abs = os.path.join(
                        vd, f"{p['id']}_{os.path.basename(tf)}")
                    open(variant_abs, "w", encoding="utf-8").write(spliced)
                file_subs[key] = os.path.relpath(variant_abs, a.rtl_dir)
                pending = {"id": p["id"], "key": key, "clock": worst,
                           "prev_slack": slacks[worst]}
                accepted = True
                print(f"  APPLY {p['id']} provisionally -> re-measure, "
                      f"confirm or revert on {worst}")
                record(iter=it, step="apply", lever="rtl", proposal=p["id"],
                       clock=worst, prev_slack=slacks[worst],
                       status="provisional")
                break
            if not accepted:
                print("no proposal passed the gate.")
                record(iter=it, step="stop", reason="no_proposal_proven")
                break
            continue

        print(f"no lever for verdict {cls['verdict']}.")
        record(iter=it, step="stop", reason="no_lever", verdict=cls["verdict"])
        break

    # summary
    sp = os.path.join(a.workdir, "SUMMARY.md")
    with open(sp, "w", encoding="utf-8") as f:
        f.write("# SlackSmith closed-loop run\n\n")
        f.write(f"engine `{a.engine}`, sdc `{os.path.basename(a.sdc)}`, "
                f"{len(history)} iterations, "
                f"{round(time.time()-t0,1)}s\n\n")
        f.write("| iteration | " + " | ".join(a.clocks) + " |\n")
        f.write("|---" * (len(a.clocks) + 1) + "|\n")
        for it, s in history:
            f.write(f"| {it} | " +
                    " | ".join(str(s.get(c)) for c in a.clocks) + " |\n")
        f.write("\nFull decision log with the evidence for every routing "
                "choice: `decisions.jsonl`.\n")
    print(f"\nwrote {sp}\nwrote {log_path}")


if __name__ == "__main__":
    main()
