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

WHERE RTL TRANSFORMS COME FROM: --proposer.

  frozen   (default) Draw from a directory of proposals frozen before any gate
           ran. Every run committed before 2026-09-05 used this, and it stays
           the default so those runs still replay.

  handoff  GENERATE one against the state the design is in at that iteration.
           The loop halts, writes a request, and resumes when a response file
           appears.

  cli      The same, automated through `claude -p`. COMMITTED UNEXERCISED: the
           OAuth session on the development machine is expired, and reporting
           it as working is a void condition in the registration.

The earlier claim here was that generating mid-run would break the anti-tuning
rule. It does not. Pre-registration forbids the EXPERIMENTER changing the
hypothesis, the prompt or the scoring after seeing results; it does not forbid
the SYSTEM producing a proposal in response to a measurement. That distinction
is argued in experiments/online_proposer/PREREGISTRATION.md.

What the online proposer is NOT given: any counterexample, and any G4 verdict.
Feeding refutations back is batch 3, registered and then deferred on
2026-09-02 because that idea is already published for RTL generation and
repair. This changes WHEN the proposer sees the design state, not whether it
is told about its own failures.

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
import proposer

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
{prewrite}
{repair}
{reports}
write_verilog {outnet}
exit
"""


def lec_check(a, gold, gate, workdir):
    """G6: is the netlist repair_design produced the same logic it was given?

    Returns the verdict dict from tools/lec_check.py, or None if the check
    was not applicable. Until 2026-09-03 the physical lever was taken on
    trust because four attempts to verify it had failed; it costs 38 s.
    """
    if not (os.path.exists(gold) and os.path.exists(gate)):
        return {"verdict": "ERROR", "reason": "netlist pair not written"}
    r = sh([sys.executable, os.path.join(HERE, "lec_check.py"),
            "--gold", gold, "--gate", gate, "--liberty", a.liberty,
            "--top", a.top, "--workdir", os.path.join(workdir, "lec"),
            "--yosys-bin", a.yosys_bin])
    try:
        return json.loads(r.stdout[r.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return {"verdict": "ERROR", "reason": "unparsable lec_check output",
                "stderr": r.stderr[-400:]}


def measure_openroad(a, netlist, workdir, tag, do_repair):
    d = os.path.join(workdir, tag)
    os.makedirs(d, exist_ok=True)
    repair = ("repair_design\ndetailed_placement\nestimate_parasitics -placement"
              if do_repair else "")
    prenet = os.path.join(d, "prerepair.v")
    prewrite = f"write_verilog {prenet}" if do_repair else ""
    reports = "\n".join(
        f'puts "---CLOCK:{c}---"\n'
        f'report_checks -path_delay max -to [get_clocks {c}] '
        f'-group_count 1 -digits 3 -fields {{fanout}}' for c in a.clocks)
    tcl = OR_TCL.format(plat=a.platform, lib=a.liberty, net=netlist, top=a.top,
                        sdc=a.sdc, repair=repair, prewrite=prewrite,
                        reports=reports, outnet=os.path.join(d, "out.v"))
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
    outnet = os.path.join(d, "out.v")
    lec = lec_check(a, prenet, outnet, d) if (do_repair and not a.no_lec) else None
    return slacks, reports_by_clk, outnet, lec


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


def g7_check(a, prop, rtl_files, file_subs, workdir, tag):
    """G7 as a differential CDC gate: did this transform make a crossing worse?

    Returns {"G7": verdict, ...}. Verdicts:
      PASS       no violation the original did not already have
      REJECT     the variant introduces a CDC violation
      SKIPPED    the target module has no clock crossings to break
      ERROR      the gate could not run, which is never a pass
    """
    mod = prop.get("target_module")
    key = next((f for f in rtl_files
                if os.path.basename(f) == "%s.v" % mod), None)
    if key is None:
        return {"G7": "SKIPPED", "why": "module not in the file list"}

    def run(subs, label):
        files = [os.path.join(a.rtl_dir, subs.get(f, f)) for f in rtl_files]
        wd = os.path.join(workdir, "g7", tag, label)
        os.makedirs(wd, exist_ok=True)
        cmd = [sys.executable, os.path.join(HERE, "cdc_check.py"),
               "--top", mod, "--workdir", wd,
               "--json", os.path.join(wd, "crossings.json"),
               "--hamming", "--ham-module", mod,
               "--ham-timeout", str(min(a.gate_timeout, 300))]
        if a.sdc:
            cmd += ["--sdc", a.sdc]
        cmd += files
        r = sh(cmd)
        open(os.path.join(wd, "cdc.log"), "w", encoding="utf-8").write(
            r.stdout + r.stderr)
        jp = os.path.join(wd, "crossings.json")
        if not os.path.exists(jp):
            return None, (r.stdout + r.stderr)[-400:]
        return json.load(open(jp, encoding="utf-8")).get("crossings", []), None

    gold, err = run({}, "gold")
    if gold is None:
        return {"G7": "ERROR", "why": "gate could not run on the original: %s" % err}
    if not gold:
        return {"G7": "SKIPPED", "why": "%s has no clock crossings" % mod}

    var, err = run(file_subs, "variant")
    if var is None:
        return {"G7": "ERROR", "why": "gate could not run on the variant: %s" % err}

    def bad(rows):
        return sorted("%s:%s" % (c["verdict"], ",".join(c.get("sources", [])))
                      for c in rows
                      if c["verdict"].startswith("DEPTH")
                      or c["verdict"].endswith("UNSAFE"))

    gb, vb = bad(gold), bad(var)
    introduced = [x for x in vb if x not in gb]
    if introduced:
        return {"G7": "REJECT", "introduced": introduced,
                "why": "the transform introduces %d CDC violation(s) the "
                       "original does not have" % len(introduced)}
    return {"G7": "PASS", "crossings": len(gold),
            "why": "no CDC violation introduced across %d crossing(s)" % len(gold)}


# -------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rtl-dir", default=os.path.join(REPO, "rtl"))
    ap.add_argument("--top", default="bench_top")
    ap.add_argument("--sdc", required=True)
    ap.add_argument("--liberty", required=True)
    ap.add_argument("--sta-bin", default=os.environ.get("STA_BIN", os.path.expanduser("~/tools/OpenSTA/build/sta")))
    ap.add_argument("--yosys-bin", default=os.environ.get("OSS_CAD_BIN", os.path.expanduser("~/tools/oss-cad-suite/bin")) + "/yosys")
    ap.add_argument("--openroad-bin", default=os.environ.get("OPENROAD_BIN", os.path.expanduser("~/or_env/bin/openroad")))
    ap.add_argument("--platform", default=os.environ.get("ORFS_PLATFORM", os.path.expanduser("~/orfs/flow/platforms/sky130hd")))
    ap.add_argument("--clock", action="append", dest="clocks", required=True)
    ap.add_argument("--proposals", action="append", default=[],
                    help="directory of frozen proposals; repeatable")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--engine", choices=["sta", "openroad"], default="sta")
    ap.add_argument("--proposer", choices=["frozen", "handoff", "cli"],
                    default="frozen",
                    help="where RTL transforms come from. frozen selects from "
                         "committed JSON; handoff and cli GENERATE one against "
                         "the state the design is in at that iteration. See "
                         "experiments/online_proposer/PREREGISTRATION.md")
    ap.add_argument("--claude-bin", default="claude",
                    help="claude CLI for --proposer cli (untested, see NOTES)")
    ap.add_argument("--force-lever", choices=["rtl", "physical"], default=None,
                    help="override the router for one iteration. The corrected "
                         "classifier never routes to rtl on this benchmark "
                         "(REPORT 7.3), so exercising the generative path needs "
                         "this. Logged as lever_forced; see the online_proposer "
                         "registration, amendment 1.")
    ap.add_argument("--max-online", type=int, default=6,
                    help="cap on generated proposals, so a run cannot become "
                         "keep asking until something passes")
    ap.add_argument("--max-iters", type=int, default=6)
    ap.add_argument("--gate-timeout", type=int, default=420)
    ap.add_argument("--lever-policy", choices=["blunt", "verdict"], default="blunt",
                    help="blunt: buffer+size at once (every run before 2026-09-03); "
                         "verdict: the classifier picks the component")
    ap.add_argument("--no-lec", action="store_true",
                    help="skip G6, the equivalence check on repair_design's output. "
                         "Off by default: a physical step whose logic is unverified "
                         "is not a result (experiments/openroad_repair/).")
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
    # Mutable so the RTL-lever block can increment it; the cap it enforces is
    # what stops an online run becoming "keep asking until something passes".
    online_count = [0]
    # The variant currently CONFIRMED for each source file. Revert restores
    # from here rather than dropping the substitution, because dropping it
    # throws away every earlier accepted transform on the same file. The
    # online run lost a confirmed +1.878 ns exactly that way; see
    # experiments/online_proposer/NOTES.md.
    confirmed_subs = {}
    slack_history = []
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
            slacks, reports, net, lec = measure_openroad(
                a, net, a.workdir, f"it{it}_or", physical_applied)
            if lec:
                v = lec.get("verdict")
                print(f"  G6 lec: {v} ({lec.get('compare_points')} compare points, "
                      f"{lec.get('unproven')} unproven)")
                record(iter=it, step="g6_lec", **lec)
                if v != "PROVEN":
                    # A physical step whose logic we cannot vouch for is not a
                    # result. Same rule the RTL lever has always had.
                    print(f"  STOP: repair_design output is {v}. A timing number "
                          f"from a netlist we cannot prove equivalent is not a result.")
                    record(iter=it, step="stop", reason=f"G6_{v}")
                    break

        shown = "  ".join(f"{c}={slacks[c]}" for c in a.clocks)
        print(f"measure: {shown}")
        slack_history.append((it, slacks[min(slacks, key=lambda k: slacks[k])]))
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
                    key = pending["key"]
                    restored = confirmed_subs.get(key)
                    if restored is None:
                        file_subs.pop(key, None)
                    else:
                        # An earlier transform on this same file was already
                        # confirmed. Go back to THAT, not to pristine source.
                        file_subs[key] = restored
                    why = ("total violation not improved" if a.g5 == "total"
                           else "no improvement")
                    print(f"  REVERT {pending['id']}: {pending['clock']} "
                          f"{before} -> {now}, {why}. G4 passed, G5 did not."
                          + (f" Restored the confirmed variant of {key}."
                             if restored else ""))
                    record(iter=it, step="revert", proposal=pending["id"],
                           clock=pending["clock"], before=before, after=now,
                           restored_confirmed=bool(restored),
                           reason=("G5_total_no_improvement" if a.g5 == "total"
                                   else "G5_no_improvement"))
                    pending = None
                    continue
                if pending["key"] in file_subs:
                    confirmed_subs[pending["key"]] = file_subs[pending["key"]]
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
        routed = route(cls["verdict"])
        # The corrected classifier never routes to rtl on this benchmark
        # (REPORT 7.3), so exercising the generative path needs an override.
        # It is recorded as lever_forced and printed in capitals, because a
        # forced run reported as the router's own choice is the misreport the
        # online_proposer registration exists to prevent.
        lever = a.force_lever or routed
        forced = bool(a.force_lever and a.force_lever != routed)
        print(f"classify {worst}: {cls['verdict']} "
              f"(fanout share {cls.get('fanout_delay_share')}) -> {routed}")
        if forced:
            print(f"  LEVER FORCED to {lever}: the router chose {routed}. "
                  f"Disclosed per online_proposer amendment 1.")
        record(iter=it, step="classify", clock=worst, verdict=cls["verdict"],
               fanout_delay_share=cls.get("fanout_delay_share"),
               path_delay_ns=cls.get("path_delay_ns"),
               cells_on_path=cls.get("cells_on_path"),
               top_cells=cls.get("top_cells"), lever=lever,
               routed_lever=routed, lever_forced=forced)

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

            if a.proposer == "frozen":
                props = [p for p in load_proposals(a.proposals)
                         if p["id"] not in tried
                         and p.get("target_module") in on_path]
                if not props:
                    print(f"no untried proposal targets the binding modules "
                          f"{sorted(on_path)}.")
                    record(iter=it, step="stop", reason="no_proposal_on_path",
                           binding_modules=sorted(on_path))
                    break
            else:
                # ONLINE. Generate against the state the design is in right
                # now, then gate it with exactly the same machinery a frozen
                # proposal gets. The proposer is given no counterexample and no
                # G4 verdict; that exclusion is the batch-3 boundary and it is
                # enforced by what build_ctx puts in the context, not by
                # convention.
                if online_count[0] >= a.max_online:
                    print(f"online proposal cap reached "
                          f"({a.max_online}); stopping.")
                    record(iter=it, step="stop", reason="online_cap_reached",
                           cap=a.max_online)
                    break
                if not on_path:
                    record(iter=it, step="stop", reason="no_binding_module")
                    break
                module = sorted(on_path)[0]
                # BENCH_TOP_FILES carries real relative paths, and the AES
                # sources are vendored under rtl/aes/. Looking for
                # rtl/<module>.v misses every one of them.
                key = next((f for f in rtl_files
                            if os.path.basename(f) == f"{module}.v"), None)
                if key is None:
                    record(iter=it, step="stop",
                           reason="module_not_in_file_list", module=module,
                           looked_for=f"{module}.v")
                    break
                src_path = os.path.join(a.rtl_dir, file_subs.get(key, key))
                if not os.path.exists(src_path):
                    record(iter=it, step="stop", reason="no_source_for_module",
                           module=module, path=src_path)
                    break
                pid = f"O{online_count[0] + 1}"
                ctx = {
                    "iteration": it, "clock": worst, "slack": slacks[worst],
                    "history": slack_history, "verdict": cls.get("verdict"),
                    "fanout_delay_share": cls.get("fanout_delay_share"),
                    "path_delay_ns": cls.get("path_delay_ns"),
                    "cells_on_path": cls.get("cells_on_path"),
                    "top_cells": cls.get("top_cells"),
                    "module": module,
                    "target_file": f"rtl/{key}",
                    "module_source": open(src_path, encoding="utf-8").read(),
                    "timing_report": (reports.get(worst) or "")[:6000],
                    "proposal_id": pid,
                }
                online_count[0] += 1
                record(iter=it, step="propose", proposal=pid, module=module,
                       backend=a.proposer, clock=worst, slack=slacks[worst])
                props, perr = proposer.propose(ctx, a, a.workdir)
                if perr or not props:
                    print(f"  online proposer returned nothing usable: {perr}")
                    record(iter=it, step="propose_failed", proposal=pid,
                           reason=perr or "empty")
                    break
                print(f"  online proposal {pid}: {props[0].get('def_id')} "
                      f"(declared k={props[0].get('latency_delta_k')})")
            accepted = False
            for p in props:
                tried.add(p["id"])
                g = gate(a, p, a.workdir, p["id"])
                v = str(g.get("G4", "?"))
                print(f"  gate {p['id']} ({g.get('def_id')}): "
                      f"G3={g.get('G3')} G4={v}")
                # Only PROVEN is accepted. UNRESOLVED is NOT a pass.
                if not v.startswith("PROVEN"):
                    record(iter=it, step="gate", proposal=p["id"],
                           def_id=g.get("def_id"),
                           declared_k=g.get("declared_k"), G1=g.get("G1"),
                           G2=g.get("G2"), G3=g.get("G3"), G4=v)
                    continue

                # G7. A transform can pass G4 and still break a clock crossing:
                # SlackBench CDC-1 is functionally a latency change and CDC-2
                # is functionally identical, and both are defects. Equivalence
                # cannot state the question, so it gets its own gate.
                tf_g7 = p.get("target_file") or ""
                key_g7 = (tf_g7[len("rtl/"):] if tf_g7.startswith("rtl/")
                          else tf_g7)
                vf_g7 = p.get("variant_file")
                subs7 = dict(file_subs)
                if vf_g7 and key_g7:
                    subs7[key_g7] = os.path.relpath(
                        os.path.join(REPO, vf_g7), a.rtl_dir)
                g7 = g7_check(a, p, rtl_files, subs7, a.workdir, p["id"])
                print(f"  G7 {p['id']}: {g7['G7']} ({g7.get('why')})")
                record(iter=it, step="gate", proposal=p["id"],
                       def_id=g.get("def_id"), declared_k=g.get("declared_k"),
                       G1=g.get("G1"), G2=g.get("G2"), G3=g.get("G3"), G4=v,
                       G7=g7["G7"], G7_why=g7.get("why"),
                       G7_introduced=g7.get("introduced"))
                if g7["G7"] in ("REJECT", "ERROR"):
                    # ERROR is not a pass, on the same principle UNRESOLVED is
                    # not a pass at G4.
                    print(f"  REJECT {p['id']} at G7.")
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
