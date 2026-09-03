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
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import remeasure
import gate_proposal
import classify_path
from classify_path import classify

REPO = os.path.dirname(HERE)

# The physical lever, split. Yosys ships buffer/upsize in its -liberty -constr
# script and not in the plain -liberty script, which is why this flow was not
# running it. Commas become spaces when abc parses a +script argument.
#
# experiments/drrtl_transfer/ phase 3 measured the two components on 15
# external designs: buffering alone is net harmful on depth-dominated paths
# (median -0.019 ns) and closes 4 of 5 fanout-dominated ones; sizing helps
# both, fanout paths 5x more. So --lever-policy verdict lets the classifier
# choose the component; --lever-policy blunt applies both, as every run
# before 2026-09-03 did.
_HEAD = "+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put"
BUF_ONLY = _HEAD + ";buffer,-N,16"
SIZE_ONLY = _HEAD + ";upsize;dnsize"
BOTH = _HEAD + ";buffer,-N,16;upsize;dnsize"
BUFFER_SCRIPT = BOTH   # name kept: experiments/closed_loop/context_control.py imports it


EXCEPTION_RE = re.compile(
    r"^\s*(set_false_path|set_multicycle_path|set_max_delay|set_min_delay|"
    r"set_disable_timing|set_case_analysis)\b", re.M)


def sdc_fingerprint(path):
    """(sha256, line count, {exception statement: count}) for an SDC file.

    G0, constraint integrity. Every gate from G1 to G5 checks the DESIGN, and
    none of them can see the constraints. experiments/sdc_integrity/ measured
    what that gap is worth: one `set_multicycle_path 2 -setup -from clk_e -to
    clk_e` takes clk_e from -0.319 VIOLATED to +4.860 MET on a byte-identical
    netlist, which is more than this project's best proven RTL transform. No
    equivalence checker can catch that, because the two designs are the same
    file. A slack number means nothing without the constraints it was measured
    under, so the loop records them and can be told to refuse a mismatch.
    """
    data = open(path, "rb").read()
    text = data.decode("utf-8", errors="replace")
    exc = {}
    for m in EXCEPTION_RE.finditer(text):
        exc[m.group(1)] = exc.get(m.group(1), 0) + 1
    return (hashlib.sha256(data).hexdigest(), len(text.splitlines()), exc)


def total_violation(slacks):
    """Sum over reported groups of min(worst slack, 0). 0 means all met."""
    return round(sum(min(v, 0.0) for v in slacks.values() if v is not None), 3)


def abc_script_for(phys, buffer_pi=False):
    """ABC script for the currently applied physical components, or None.

    buffer_pi adds -p to ABC's buffer command so flop outputs (primary
    inputs from ABC's point of view once dfflibmap has run) are buffered
    too; experiments/flatten_control/NOTES.md amendment 1, 2026-09-03.
    Without it the scripts are byte-identical to BUF_ONLY / BOTH."""
    buf = ";buffer,-N,16" + (",-p" if buffer_pi else "")
    if phys["buffer"] and phys["size"]:
        return _HEAD + buf + ";upsize;dnsize"
    if phys["buffer"]:
        return _HEAD + buf
    if phys["size"]:
        return SIZE_ONLY
    return None


def choose_physical(verdict, phys, tried, policy):
    """Which physical component to apply next, or None.

    blunt:   both components at once, once.
    verdict: FANOUT/MIXED -> buffer-only, then sizing.  DEPTH -> sizing only.
    A component that was applied and reverted is in `tried` and not retried.
    """
    if policy == "blunt":
        return None if (phys["buffer"] or phys["size"] or "both" in tried) else "both"
    order = ["buffer", "size"] if verdict in ("FANOUT_DOMINATED", "MIXED") else ["size"]
    for c in order:
        if not phys[c] and c not in tried:
            return c
    return None


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
        extra_yosys_top=a.top, abc_script=abc_script, flatten=a.flatten)
    slacks, out = remeasure.sta_slack(
        a.sta_bin, a.liberty, net, a.top, a.sdc, a.clocks, d)
    return slacks, split_reports(out, a.clocks), net, os.path.join(d, "mapped_attr.v")


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
        f'-group_count 1 -digits 3 -fields {{fanout}}' for c in a.clocks)
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
    ap.add_argument("--lever-policy", choices=["blunt", "verdict"], default="blunt",
                    help="blunt: buffer+size at once (every run before 2026-09-03); "
                         "verdict: the classifier picks the component")
    ap.add_argument("--expect-sdc-sha", default=None,
                    help="G0: refuse to run unless the SDC's sha256 starts with this. "
                         "A slack number is only meaningful under known constraints; "
                         "see experiments/sdc_integrity/.")
    ap.add_argument("--flatten", action="store_true",
                    help="synth -flatten before abc, so the buffering pass sees across "
                         "module ports (experiments/flatten_control/). Default off keeps "
                         "the hierarchical flow every run before 2026-09-03 used. On a "
                         "flat netlist the classifier cannot attribute cells to modules, "
                         "so the RTL lever cannot select a proposal.")
    ap.add_argument("--buffer-pi", action="store_true",
                    help="add -p to ABC's buffer command (buffer flop outputs too)")
    ap.add_argument("--g5", choices=["target", "total"], default="target",
                    help="target: a provisional step is kept if the group it targeted "
                         "improved (every run before 2026-09-03); total: kept only if "
                         "the sum over groups of min(worst slack, 0) strictly improved")
    a = ap.parse_args()
    if a.lever_policy == "verdict" and a.engine != "sta":
        ap.error("--lever-policy verdict splits the abc script; it is sta-only "
                 "(repair_design has no buffer/size split)")

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

    # G0: constraint integrity. See sdc_fingerprint().
    sdc_sha, sdc_lines, sdc_exc = sdc_fingerprint(a.sdc)
    print(f"G0 sdc: {os.path.basename(a.sdc)} sha256 {sdc_sha[:16]} "
          f"{sdc_lines} lines, timing exceptions {sdc_exc or 'none'}")
    if a.expect_sdc_sha and not sdc_sha.startswith(a.expect_sdc_sha):
        sys.exit(f"FATAL G0: sdc sha256 {sdc_sha} does not match the expected "
                 f"{a.expect_sdc_sha}. Refusing to report slack measured under "
                 f"constraints that are not the registered ones.")

    log_path = os.path.join(a.workdir, "decisions.jsonl")
    log = open(log_path, "a", encoding="utf-8")

    def record(**kw):
        kw["t"] = round(time.time() - t0, 1)
        log.write(json.dumps(kw) + "\n")
        log.flush()
        return kw

    t0 = time.time()
    # After t0: record() stamps every row with time.time() - t0.
    record(step="g0_sdc", sdc=os.path.basename(a.sdc), sha256=sdc_sha,
           lines=sdc_lines, timing_exceptions=sdc_exc)

    rtl_files = list(remeasure.BENCH_TOP_FILES)
    file_subs = {}          # original rtl file -> accepted variant path
    physical_applied = False
    tried = set()
    history = []
    # Any step, RTL or physical, is provisionally applied, then confirmed or
    # reverted on the NEXT measurement. Passing the formal gate means an RTL
    # transform is correct, not that it helps: batch 1 had 4 transforms
    # formally proven and 3 of them made timing worse. Physical steps get the
    # same bar since 2026-09-03: on cpu_fsm, sizing applied after buffering
    # gave back 7.2 ns (experiments/drrtl_transfer/ phase 3).
    pending = None
    phys = {"buffer": False, "size": False}   # applied physical components
    tried_phys = set()                          # components applied and reverted

    print(f"dont_use flags: {ndu}")
    print(f"engine: {a.engine}   clocks: {', '.join(a.clocks)}")

    for it in range(1, a.max_iters + 1):
        print(f"\n=== iteration {it} ===")
        files = [file_subs.get(f, f) for f in rtl_files]

        physical_applied = phys["buffer"] or phys["size"]
        abc = abc_script_for(phys, a.buffer_pi) if a.engine == "sta" else None
        slacks, reports, net, attr_net = measure_sta(a, files, a.workdir, f"it{it}", abc)

        if a.engine == "openroad":
            # repair_design is one pass; the split lever exists only for abc.
            slacks, reports, net = measure_openroad(
                a, net, a.workdir, f"it{it}_or", physical_applied)

        shown = "  ".join(f"{c}={slacks[c]}" for c in a.clocks)
        print(f"measure: {shown}")
        record(iter=it, step="measure", engine=a.engine, slacks=slacks,
               physical=dict(phys), lever_policy=a.lever_policy, g5=a.g5,
               flatten=a.flatten, buffer_pi=a.buffer_pi,
               total_violation=total_violation(slacks),
               rtl_applied=sorted(file_subs.values()))
        history.append((it, dict(slacks)))

        # G5 on whatever was applied last iteration, RTL or physical.
        if pending:
            now = slacks.get(pending["clock"])
            before = pending["prev_slack"]
            if a.g5 == "total":
                # PREREGISTRATION_g5_total.md: the step is kept only if the
                # sum over reported groups of min(worst slack, 0) strictly
                # improves. A gain on the targeted group that is paid for by
                # another group going from met to violating is a revert.
                t_before = total_violation(pending["prev_slacks"])
                t_after = total_violation(slacks)
                improved = t_after > t_before
                print(f"  G5 total: {t_before} -> {t_after} "
                      f"({'improved' if improved else 'not improved'})")
                record(iter=it, step="g5_total", total_before=t_before,
                       total_after=t_after, improved=improved)
            else:
                improved = now is not None and now > before
            if pending.get("kind") == "physical":
                comp = pending["component"]
                if not improved:
                    for c in (("buffer", "size") if comp == "both" else (comp,)):
                        phys[c] = False
                    tried_phys.add(comp)
                    why = ("total violation not improved" if a.g5 == "total"
                           else "no improvement")
                    print(f"  REVERT physical {comp}: {pending['clock']} "
                          f"{before} -> {now}, {why}.")
                    record(iter=it, step="revert", lever="physical", component=comp,
                           clock=pending["clock"], before=before, after=now,
                           reason=("G5_total_no_improvement" if a.g5 == "total"
                                   else "G5_no_improvement"))
                    pending = None
                    continue
                print(f"  CONFIRM physical {comp}: {pending['clock']} "
                      f"{before} -> {now} ({now - before:+.3f})")
                record(iter=it, step="confirm", lever="physical", component=comp,
                       clock=pending["clock"], before=before, after=now,
                       gain=round(now - before, 3))
                pending = None
            else:
                if not improved:
                    file_subs.pop(pending["key"], None)
                    why = ("total violation not improved" if a.g5 == "total"
                           else "no improvement")
                    print(f"  REVERT {pending['id']}: {pending['clock']} "
                          f"{before} -> {now}, {why}. G4 passed, G5 did not.")
                    record(iter=it, step="revert", proposal=pending["id"],
                           clock=pending["clock"], before=before, after=now,
                           reason=("G5_total_no_improvement" if a.g5 == "total"
                                   else "G5_no_improvement"))
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
        # On a flat netlist cell names carry no hierarchy, so module ownership
        # (which the RTL lever filters on) comes from Yosys src attributes.
        smap = None
        if a.flatten and os.path.exists(attr_net):
            smap = classify_path.src_module_map(
                attr_net, [os.path.join(a.rtl_dir, f) for f in rtl_files])
        cls = classify(reports[worst], net, top=a.top, src_map=smap)
        lever = route(cls["verdict"])
        print(f"classify {worst}: {cls['verdict']} "
              f"(fanout share {cls.get('fanout_delay_share')}) -> {lever}")
        record(iter=it, step="classify", clock=worst, verdict=cls["verdict"],
               fanout_delay_share=cls.get("fanout_delay_share"),
               path_delay_ns=cls.get("path_delay_ns"),
               cells_on_path=cls.get("cells_on_path"),
               top_cells=cls.get("top_cells"), lever=lever)

        if a.lever_policy == "verdict":
            # The classifier picks the component (registered 2026-09-03,
            # experiments/closed_loop/PREREGISTRATION_verdict_lever.md):
            # FANOUT/MIXED: buffer-only, then sizing, then stop.
            # DEPTH: sizing-only, then the RTL proposals.
            # Each step is provisional; the G5 block above reverts it.
            comp = choose_physical(cls["verdict"], phys, tried_phys, "verdict")
            if comp:
                phys[comp] = True
                print(f"apply: physical {comp} (provisional) -> "
                      f"abc {abc_script_for(phys, a.buffer_pi).split(';&put;')[-1]}")
                record(iter=it, step="apply", lever="physical", component=comp,
                       how=abc_script_for(phys, a.buffer_pi), provisional=True,
                       clock=worst, prev_slack=slacks[worst])
                pending = {"kind": "physical", "component": comp,
                           "clock": worst, "prev_slack": slacks[worst],
                           "prev_slacks": dict(slacks)}
                continue
            if lever == "physical":
                print("every physical component applied or reverted and the "
                      "group still violates. no lever left for it.")
                record(iter=it, step="stop", reason="physical_exhausted",
                       clock=worst, physical=dict(phys),
                       tried_physical=sorted(tried_phys))
                break
            # DEPTH with sizing already on: fall through to the RTL lever.

        elif lever == "physical":
            # blunt: the pre-2026-09-03 behaviour, kept so earlier runs
            # reproduce. One combined step, not provisional.
            if physical_applied:
                print("physical lever already applied and the group still "
                      "violates. no lever left for it.")
                record(iter=it, step="stop", reason="physical_exhausted",
                       clock=worst)
                break
            phys["buffer"] = phys["size"] = True
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
                           "prev_slack": slacks[worst],
                           "prev_slacks": dict(slacks)}
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
