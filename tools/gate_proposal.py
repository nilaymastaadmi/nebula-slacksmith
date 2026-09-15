#!/usr/bin/env python3
"""
gate_proposal.py -- run a registered LLM proposal through gates G1 to G4.

Implements the protocol fixed in experiments/llm_proposer/PREREGISTRATION.md.
Gates run in order and stop at the first failure; every outcome is recorded,
including failures, which are the point of the experiment rather than an
inconvenience.

  G1 parse       Yosys reads the spliced module.
  G2 elaborate   synth completes; cells, flops and latches recorded.
  G3 precondition declared-latency consistency: a proposal declaring k=0 must
                 not change the flop count, and one declaring k>0 must
                 increase it. This is mechanical and it is a real check: it
                 catches a transform whose declared type does not match what
                 it actually did, which is exactly the case where the wrong
                 obligation would be generated and a wrong answer trusted.
                 Latch-free is also required.
  G4 formal      the obligation implied by the DECLARED tier: k=0 gets direct
                 output equivalence, k>0 gets a k-padded miter against a gold
                 design whose outputs are delayed by k. Run through
                 tools/run_proof.py with the standard engine portfolio.

G5 (timing) is run separately with tools/remeasure.py, only for proposals
that survive G4, because timing a refuted transform measures nothing.

Usage:
  python3 tools/gate_proposal.py --proposal experiments/llm_proposer/proposals/P1.json \\
      --rtl rtl/rv32i_core.v --workdir ~/gates/P1 [--depth 20] [--timeout 300]
"""
import argparse, glob, io, json, os, re, subprocess, sys

CORE_OUTPUTS = [
    ("imem_addr", 32), ("dmem_addr", 32), ("dmem_wdata", 32),
    ("dmem_wstrb", 4), ("dmem_we", 1), ("retire_pc", 32),
    ("retire_insn", 32), ("retire_rd", 5), ("retire_val", 32),
    ("retire_we", 1), ("halted", 1),
]


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


CLOCK_NAMES = re.compile(r"^(clk|clock|wb_clk_i|clk_i|i_clk)$", re.I)
RESET_NAMES = re.compile(r"^(rst|rst_n|reset|reset_n|rstn|resetn|arst_n|wb_rst_i|rst_i|i_rst)$", re.I)


def derive_ports(yosys, rtl, module):
    """The module's real interface, read from the elaborator, not from a table.

    Added 2026-09-13 (experiments/invariant_obligation/, defect 1). Until then
    a module with no --outputs fell back to CORE_OUTPUTS, the RV32I core's
    port list. That was invisible on every design this gate had seen, because
    rv32i_core IS that interface and aes_key_mem was always given explicit
    ports. On external IP it built a miter instantiating ports like `halted`
    and `retire_insn` on a Z80 microcode decoder and an I2C bit controller,
    which failed elaboration, which the gate then reported as UNRESOLVED. The
    two proposals it dropped were the only two, across both depth-dominated
    designs, that attacked the path's actual depth.

    Yosys reads the port list, so every Verilog declaration style, parameter
    defaults and non-ANSI ports are handled by the tool that will elaborate
    the miter anyway. Returns (data_inputs, outputs, clk, rst); clk and rst
    are None for a module that has none, which a combinational module does not.
    """
    import tempfile
    tmp = tempfile.mkdtemp(prefix="ports_")
    jpath = os.path.join(tmp, "ports.json")
    r = sh([yosys, "-q", "-p",
            "read_verilog %s; hierarchy -top %s; proc; write_json %s"
            % (rtl, module, jpath)])
    if r.returncode != 0 or not os.path.exists(jpath):
        return None
    mods = json.load(open(jpath, encoding="utf-8"))["modules"]
    m = mods.get(module) or next(
        (v for k, v in mods.items() if k.split("\\")[-1] == module), None)
    if m is None:
        return None
    ins, outs, clk, rst = [], [], None, None
    for name, port in m["ports"].items():
        width = len(port["bits"])
        if port["direction"] == "input":
            if width == 1 and clk is None and CLOCK_NAMES.match(name):
                clk = name
            elif width == 1 and rst is None and RESET_NAMES.match(name):
                rst = name
            else:
                ins.append((name, width))
        elif port["direction"] == "output":
            outs.append((name, width))
    return ins, outs, clk, rst


def _strip_comments(text):
    """Remove comments, keeping every newline so reported line numbers hold."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def param_override(rtl, module):
    """Where `module` is instantiated with its parameters overridden, or None.

    Added 2026-09-13 (gate defect 3). Every obligation below
    elaborates the target with `prep -top` / `hierarchy -top`, which uses the
    module's HEADER DEFAULTS. A module the design instantiates with a `#(`
    override is then proven about a circuit the design does not contain:
    tv80_mcode's header default is Mode = 0, and the design passes Mode = 1
    down through tv80_core (experiments/invariant_obligation/, defect 3). That is the one gate defect whose failure is a false
    PROVEN, so until parameters are threaded into every branch the gate
    refuses. The search covers the target file, its directory and the parent
    directory, non-recursively; a missed parent elsewhere is possible, and a
    commented-out match is removed first. Refusing on a false match is the
    safe direction.
    """
    src = _strip_comments(open(rtl, encoding="utf-8", errors="replace").read())
    m = re.search(r"^\s*module\s+" + re.escape(module) + r"\b(.*?)^\s*endmodule\b",
                  src, re.M | re.S)
    # A parameter can also arrive through an `include inside the module body,
    # where the word never appears in this file (2026-09-14): treat
    # the include as a declaration and let the override search decide.
    if m is None or not re.search(r"(?<!local)\bparameter\b|`include\b", m.group(1)):
        return None
    here = os.path.dirname(os.path.abspath(rtl))
    files = []
    for d in (here, os.path.dirname(here)):
        for ext in ("*.v", "*.sv", "*.vh", "*.svh"):
            files.extend(sorted(glob.glob(os.path.join(d, ext))))
    inst = re.compile(r"^[ \t]*" + re.escape(module) + r"\s*#\s*\(", re.M)
    for f in files:
        try:
            text = _strip_comments(open(f, encoding="utf-8", errors="replace").read())
        except OSError:
            continue
        hit = inst.search(text) or re.search(r"^[ \t]*defparam\b", text, re.M)
        if hit:
            line = text.count("\n", 0, hit.start()) + 1
            return "%s:%d" % (os.path.relpath(f), line)
    return None


def splice(src, p):
    a, b = p["anchor_start"], p["anchor_end"]
    i = src.find(a)
    j = src.find(b, i)
    if i < 0 or j < 0:
        raise SystemExit("anchor not found; proposal does not apply to this RTL")
    return src[:i] + p["replacement"] + "\n" + src[j:]


def sv_flag(path):
    """' -sv' when the source uses SystemVerilog constructs. Phase 4 of the
    transfer study fed this harness a .sv design (aes) and both variants
    failed G1 before any solver ran, because plain read_verilog rejects
    always_comb / always_ff / logic. A harness that cannot read the input is
    not a verdict on the transform, so the flag is derived from the text."""
    try:
        t = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""
    return " -sv" if re.search(r"\b(always_comb|always_ff|logic)\b", t) else ""


def stats(yosys, path, top, workdir, tag):
    log = os.path.join(workdir, f"{tag}.synth.log")
    r = sh([yosys, "-p", f"read_verilog{sv_flag(path)} {path}; hierarchy -check -top {top}; synth -top {top}; stat"])
    with open(log, "w", encoding="utf-8") as f:
        f.write(r.stdout + r.stderr)
    if r.returncode != 0:
        return None, log
    txt = r.stdout
    cells = re.findall(r"^\s+(\d+)\s+cells\s*$", txt, re.M)
    dff = sum(int(n) for n in re.findall(r"^\s+(\d+)\s+\$_(?:S?DFF|DFFE)[_A-Z0-9]*\s*$", txt, re.M))
    latch = len([1 for m in re.finditer(r"DLATCH", txt) if "Executing" not in m.string[max(0, m.start()-60):m.start()]])
    return {"cells": int(cells[-1]) if cells else None, "dff": dff, "latch_lines": latch}, log


# A transform can leave latency unchanged and still change the flop count.
# Retiming moves a register across combinational logic; re-encoding a state
# register widens it. Both are k=0 with dff_delta != 0.
#
# Until 2026-09-11 G3's rule was k==0 => dff_delta==0 with no exception, so
# both were rejected before the branch they declared was ever consulted. That
# is why no proposal in this repository has ever been a retiming or an FSM
# re-encoding: tools/proposer_prompt.md advertised branch 4 (mapped-state,
# "you re-encoded state, e.g. binary to one-hot") as available, and a proposer
# that followed the template and declared it was guaranteed a G3 rejection.
# The project's own one-hot result (experiments/fsm_reencode/) is hand-built
# with its own miter for exactly this reason, and measuring it through the
# unmodified gate returns FAIL(declared k=0 but flop count changed by +12).
#
# Both classes are discharged by the SEQUENTIAL miter rather than by EQY.
# EQY pairs internal nets by name and proves each partition, which needs a
# flop correspondence; neither class has one. That is not a theoretical
# objection: experiments/g7_in_loop measured EQY rejecting 15 of 43 partitions
# on a variant its own I/O miter proves equivalent to depth 20, because the
# nets had changed meaning. The miter compares interfaces, which is the
# question these two classes actually pose.
STATE_REMAP_BRANCHES = {4, 5}   # 4 mapped-state, 5 retiming


def declared_branch(p, def_id):
    """Branch number the proposal declares, or None.

    Read from obligation_branch's leading digit where there is one, because
    the template asks for '4 (mapped-state equivalence)'. Batch 2 spells the
    field as a name instead of a number, so those are mapped explicitly; an
    unrecognised spelling returns None and routes on k alone, which is what
    every proposal written before this change did.
    """
    raw = str(p.get("obligation_branch", ""))
    m = re.match(r"\s*(\d+)", raw)
    if m:
        return int(m.group(1))
    name = (raw + " " + str(def_id or "")).lower()
    if "mapped" in name or "reencode" in name or "re_encode" in name:
        return 4
    if "retime" in name or "retiming" in name:
        return 5
    if "k_padded" in name:
        return 2
    if "eqy" in name or "combinational" in name:
        return 1
    return None


def failing_depth(wd, tag="miter_prop"):
    """Step at which BMC found the counterexample, or None.

    A refutation found at step 3 is only as trustworthy as the harness is at
    step 3, so that is the depth the null control has to cover. Running the
    control to the proposal's full depth and then PDR to convergence answers a
    harder question than the one asked, and on rv32i_core (2,048 flops) it
    answers nothing at all: both engines time out and a real refutation is
    downgraded to uncorroborated for no reason (R19).
    """
    for name in ("%s_bmc.raw.log" % tag, "%s_prove.raw.log" % tag):
        path = os.path.join(wd, name)
        if not os.path.isfile(path):
            continue
        try:
            txt = io.open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        m = re.findall(r"failed assertion \S+ at \S+ step (\d+)", txt)
        if m:
            return min(int(x) for x in m)
    return None


def null_control(a, wd, mod, nc, res, outs=None, tag="nullctl", depth=None):
    """Run the miter with the gate replaced by the gold, renamed.

    Returns False if the null control also fails, meaning the miter cannot
    distinguish this module from itself and no refutation from it is
    trustworthy. Returns True if gold-vs-gold proves. Returns None if the
    control itself could not be decided, which is reported as inconclusive
    rather than silently treated as a pass.

    ALWAYS built at k=0, whatever the proposal declares: the question is
    whether the harness can tell the module from itself, which is about state
    initialisation and not about latency. Built at the proposal's own k it
    compared gold-delayed against gold-undelayed and failed for every k>0
    proposal, which prediction R10 in experiments/missing_classes caught.
    """
    nwd = os.path.join(wd, tag)
    os.makedirs(nwd, exist_ok=True)
    gold_src = io.open(os.path.join(wd, "gold.v"), encoding="utf-8").read()
    io.open(os.path.join(nwd, "gold.v"), "w", encoding="utf-8").write(gold_src)
    io.open(os.path.join(nwd, "gate.v"), "w", encoding="utf-8").write(
        gold_src.replace(mod + "_gold", mod + "_gate"))
    io.open(os.path.join(nwd, "miter_prop.sv"), "w", encoding="utf-8").write(
        build_miter(nc["p"], nc["def_id"], mod, nc["clk"], nc["rst"],
                    outs if outs is not None else nc["outs"], nc["ins"], 0,
                    nc.get("dut_clk", True), nc.get("dut_rst", True)))
    rp = os.path.join(os.path.abspath(a.repo), "tools", "run_proof.py")
    r = sh([sys.executable, rp, "--top", "miter_prop",
            "--file", "gold.v", "--file", "gate.v", "--file", "miter_prop.sv",
            "--workdir", nwd, "--tasks", "bmc,pdr",
            "--depth", str(depth if depth is not None else a.depth),
            "--timeout", str(a.null_timeout or a.timeout)]
           + (["--zero-init"] if a.zero_init else []))
    out = r.stdout + r.stderr
    io.open(os.path.join(nwd, "null.log"), "w", encoding="utf-8").write(out)
    nb = np = "?"
    for line in out.splitlines():
        if line.startswith("bmc:"):
            nb = line.split(":", 1)[1].strip()
        if line.startswith("pdr:"):
            np = line.split(":", 1)[1].strip()
    res["G4_null_bmc"], res["G4_null_pdr"] = nb, np
    res["_null_fail_output"] = None
    m = re.search(r"miter_prop\.eq_(\w+)", nb + " " + np)
    if m:
        res["_null_fail_output"] = m.group(1)
    if nb.startswith("FAIL") or np.startswith("FAIL"):
        return False
    if np.startswith("PROVEN"):
        return True
    # A control deliberately bounded at the counterexample's depth must be
    # judged by a bounded criterion. PDR is unbounded, so requiring it here
    # discarded a BMC PASS at exactly the depth the claim covers, which defeats
    # the point of bounding: the claim is "no spurious failure at or below the
    # depth where this refutation was found", and a BMC PASS to that depth IS
    # that claim. Requiring PDR left P5 uncorroborated for a reason unrelated
    # to P5.
    if depth is not None and nb.startswith("PASS"):
        return True
    return None

# NAME=VALUE pairs from --param, applied to both instances of every obligation.
# Added 2026-09-15 (experiments/survival_tv80/): the refusal below is right when
# the instantiated parameters are unknown, and wrong once they are supplied.
GATE_PARAMS = []


def _param_override_str():
    if not GATE_PARAMS:
        return ""
    return "#(" + ", ".join(".%s(%s)" % tuple(kv.split("=", 1)) for kv in GATE_PARAMS) + ") "


def build_miter(p, def_id, mod, clk, rst, outs, ins, k, dut_clk=True, dut_rst=True):
    """The miter text. One implementation, used by the gate and by its
    null control, so the two cannot drift apart. The control always calls
    this with k=0: it asks whether the harness can tell the module from
    itself, which is a question about state initialisation and not about
    latency. Calling it with the proposal's own k compared gold-delayed
    against gold-undelayed and failed for every k>0 proposal, which is how
    prediction R10 in experiments/missing_classes caught it.
    """
    decl, inst_g, inst_t, cmp_lines, pipe = [], [], [], [], []
    for n, w in outs:
        rng = "" if w == 1 else f"[{w-1}:0] "
        decl.append(f"    wire {rng}g_{n}, t_{n};")
        inst_g.append(f"        .{n}(g_{n}),")
        inst_t.append(f"        .{n}(t_{n}),")
        if k == 0:
            cmp_lines.append(f"            eq_{n}: assert (g_{n} == t_{n});")
        else:
            decl.append(f"    reg {rng}gp_{n};")
            pipe.append(f"            gp_{n} <= g_{n};")
            cmp_lines.append(f"            eq_{n}: assert (gp_{n} == t_{n});")
    pipe_blk = ""
    if k > 0:
        pipe_blk = ("    always @(posedge " + clk + " or negedge " + rst + ") begin\n"
                    "        if (!" + rst + ") begin\n"
                    + "\n".join(f"            gp_{n} <= 0;" for n, _ in outs) +
                    "\n        end else begin\n" + "\n".join(pipe) + "\n        end\n    end\n")
    prime = ("    reg [3:0] pr;\n"
             "    always @(posedge " + clk + " or negedge " + rst + ")\n"
             f"        if (!{rst}) pr <= 0; else if (pr < {max(k,1)}) pr <= pr + 1;\n"
             f"    wire primed = (pr >= {max(k,1)});\n")
    in_decl = "".join(
        "    input wire " + ("" if w == 1 else "[" + str(w - 1) + ":0] ") + n + "," + chr(10)
        for n, w in ins)
    in_conn = ", ".join("." + n + "(" + n + ")" for n, w in ins)
    # A combinational module has no clock or reset port. The miter keeps its
    # own clock for the formal harness; only the DUT connection is dropped.
    dut_cr = (f".{clk}({clk}), " if dut_clk else "") + (f".{rst}({rst}), " if dut_rst else "")
    miter = f"""// generated by tools/gate_proposal.py for {p['id']} ({def_id}), declared k={k}
module miter_prop (
    input wire {clk}, input wire {rst},
{in_decl}    input wire _unused_tie
);
{chr(10).join(decl)}

    {mod}_gold {_param_override_str()}u_g (
        {dut_cr}{in_conn},
{chr(10).join(inst_g)[:-1]}
    );
    {mod}_gate {_param_override_str()}u_t (
        {dut_cr}{in_conn},
{chr(10).join(inst_t)[:-1]}
    );

{pipe_blk}{prime}
`ifdef FORMAL
    initial assume (!{rst});
    always @(posedge {clk}) begin
        if ({rst} && primed) begin
{chr(10).join(cmp_lines)}
        end
    end
`endif
endmodule
"""
    return miter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", required=True)
    ap.add_argument("--rtl", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--yosys", default=os.environ.get("OSS_CAD_BIN", os.path.expanduser("~/tools/oss-cad-suite/bin")) + "/yosys")
    ap.add_argument("--depth", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=300)
    # The null control is a separate budget from the proposal's own
    # proof. gold-vs-gold on rv32i_core (2,048 flops) does not close in
    # 300s, and an unclosed control is reported as INCONCLUSIVE, which
    # correctly downgrades the refutation it was meant to corroborate.
    # Raising it must not silently change any proposal verdict, so it is
    # its own flag rather than a bump to --timeout.
    ap.add_argument("--zero-init", action="store_true",
                    help="pass --zero-init to run_proof.py: both instances of the "
                         "miter start unreset storage in the same state. REQUIRED for "
                         "any module with an array the async reset cannot reach, and "
                         "the resulting verdict carries that assumption.")
    ap.add_argument("--null-timeout", type=int, default=None,
                    help="seconds for the gold-vs-gold control "
                         "(default: same as --timeout)")
    ap.add_argument("--repo", default=".")
    # Batch 2 (experiments/llm_proposer_aes) targets a different module with
    # a different port list. Every default below is the batch-1 rv32i_core
    # setting, so batch 1 reproduces unchanged.
    ap.add_argument("--param", action="append", default=[],
                    help="NAME=VALUE applied to gold and gate in every obligation; "
                         "lifts the parameter-override refusal only when supplied")
    ap.add_argument("--module", default="rv32i_core")
    ap.add_argument("--clk", default="clk")
    ap.add_argument("--rst", default="rst_n")
    ap.add_argument("--outputs", default=None)
    # None means "not supplied". rv32i_core keeps its historical default so
    # batch 1 reproduces unchanged; any other module has its ports derived.
    ap.add_argument("--inputs", default=None)
    a = ap.parse_args()

    wd = os.path.expanduser(a.workdir)
    os.makedirs(wd, exist_ok=True)
    p = json.load(open(a.proposal, encoding="utf-8"))
    src = open(a.rtl, encoding="utf-8").read()
    # Batch 2 JSONs use different key spellings. They are accepted here rather
    # than edited, because rewriting a frozen proposal file after the freeze
    # commit would weaken the freeze even though no gate has run yet.
    def_id = p.get("def_id") or p.get("transform_type")
    k = p.get("latency_delta_k", p.get("declared_latency_delta_k"))
    if k is None:
        raise SystemExit("proposal declares no latency delta")
    branch = declared_branch(p, def_id)
    res = {"id": p["id"], "def_id": def_id, "declared_k": k,
           "declared_branch": branch}
    if a.zero_init:
        res["assumption"] = ("unreset storage starts ZEROED and identical in "
                             "both instances (setundef -init -zero); every "
                             "verdict below is conditional on it")

    mod = a.module
    gold = os.path.join(wd, "gold.v")
    gate = os.path.join(wd, "gate.v")
    if p.get("variant_file"):
        # Batch 2 proposals are complete rewritten modules, not splices.
        vpath = os.path.join(a.repo, p["variant_file"])
        if not os.path.exists(vpath):
            # Nine committed proposals record variant_file relative to the
            # scratch directory they were written in (../../../../../../home/
            # ...), which resolves from the author's working tree and from no
            # clone at any other depth. Found 2026-09-13 by the fresh-clone
            # check. The frozen JSON is not edited; the committed copy beside
            # it, same file name, is used and the substitution is recorded.
            beside = os.path.join(os.path.dirname(a.proposal),
                                  os.path.basename(p["variant_file"]))
            if os.path.exists(beside):
                res["variant_file_resolved"] = beside
                vpath = beside
        gate_src = io.open(vpath, encoding="utf-8").read()
    else:
        gate_src = splice(src, p)
    def rename(text, suffix):
        """Suffix EVERY module the file declares, and every instantiation.

        Renaming only the target works when the file declares only the target,
        which is a property of this project's benchmark and not of Verilog.
        The first external design tried (i2c, three modules in one i2c.v) put
        both copies in one Yosys namespace and G4 died with
        `Re-definition of module i2c_master_byte_ctrl`.

        SystemVerilog also allows `endmodule : name`; renaming the header alone
        leaves a mismatched end label and Yosys refuses to elaborate, found
        2026-09-02 on the aes design of the Dr. RTL benchmark.
        """
        names = re.findall(r"^\s*module\s+(\w+)", text, re.M)
        for n in names:
            text = re.sub(r"^(\s*module\s+)" + re.escape(n) + r"\b",
                          r"\g<1>" + n + suffix, text, flags=re.M)
            text = re.sub(r"(endmodule\s*:\s*)" + re.escape(n) + r"\b",
                          r"\g<1>" + n + suffix, text)
            text = re.sub(r"^(\s*)" + re.escape(n)
                          + r"(\s+(?:#\s*\(|\w+\s*\())",
                          r"\g<1>" + n + suffix + r"\g<2>", text, flags=re.M)
        return text
    open(gold, "w", encoding="utf-8").write(rename(src, "_gold"))
    open(gate, "w", encoding="utf-8").write(rename(gate_src, "_gate"))

    # ---- G1 / G2
    gs, _ = stats(a.yosys, gold, mod + "_gold", wd, "gold")
    ts, tlog = stats(a.yosys, gate, mod + "_gate", wd, "gate")
    if ts is None:
        res.update(G1="FAIL", note=f"yosys could not read/elaborate; see {tlog}")
        print(json.dumps(res, indent=2)); return
    res["G1"] = "PASS"
    res["G2"] = "PASS" if ts["latch_lines"] == 0 else "FAIL(latches)"
    res["gold_cells"], res["gate_cells"] = gs["cells"], ts["cells"]
    res["gold_dff"], res["gate_dff"] = gs["dff"], ts["dff"]
    if res["G2"] != "PASS":
        print(json.dumps(res, indent=2)); return

    # ---- G3 declared-latency consistency
    d = ts["dff"] - gs["dff"]
    if k == 0 and branch in STATE_REMAP_BRANCHES:
        # Declared state remap or retiming: latency is unchanged, the flop
        # count is free, and the obligation moves to the sequential miter.
        res["G3"] = "PASS(state-remap: k=0, flop delta unconstrained)"
    elif k == 0 and d != 0:
        res["G3"] = f"FAIL(declared k=0 but flop count changed by {d:+d})"
    elif k > 0 and d <= 0:
        res["G3"] = f"FAIL(declared k={k} but flop count changed by {d:+d})"
    else:
        res["G3"] = "PASS"
    res["dff_delta"] = d
    if not res["G3"].startswith("PASS"):
        print(json.dumps(res, indent=2)); return

    # ---- G4 formal
    # Refuse before building any obligation if the design overrides the
    # target's parameters: every branch below elaborates header defaults.
    GATE_PARAMS[:] = a.param
    where = param_override(a.rtl, mod)
    if where and a.param:
        res["params"] = list(a.param)
        res["param_override_at"] = where
    elif where:
        res["G4"] = ("CANNOT (parameter override at instantiation, %s; the gate "
                     "elaborates header defaults)" % where)
        print(json.dumps(res, indent=2))
        return

    # Branch selection follows the DECLARED tier, which is the whole point of
    # the typed library. For k=0 with dff_delta==0 the two designs have a 1:1
    # flop correspondence, so the obligation is COMBINATIONAL equivalence and
    # EQY is the right (and far cheaper) tool: an earlier version of this
    # harness built a full sequential miter for every proposal and timed out
    # at 240s on both engines against 2,048 flops, which measured the harness
    # rather than the transform.
    if k == 0 and branch not in STATE_REMAP_BRANCHES:
        eqy_cfg = os.path.join(wd, "prop.eqy")
        chp = "".join("chparam -set %s %s %s_gold\n" % (kv.split("=", 1)[0], kv.split("=", 1)[1], mod)
                      for kv in a.param)
        svf = sv_flag(gold)
        open(eqy_cfg, "w", encoding="utf-8").write(
            "[gold]\nread_verilog" + svf + " gold.v\n" + chp + "prep -top " + mod + "_gold\n\n"
            + "[gate]\nread_verilog" + svf + " gate.v\nrename " + mod + "_gate " + mod + "_gold\n"
            + chp + "prep -top " + mod + "_gold\n\n"
            + "[strategy sat]\nuse sat\ndepth 5\n")
        eqy = os.environ.get("OSS_CAD_BIN", os.path.expanduser("~/tools/oss-cad-suite/bin")) + "/eqy"
        r = sh([eqy, "-f", "prop.eqy"], cwd=wd, timeout=a.timeout)
        out = r.stdout + r.stderr
        open(os.path.join(wd, "g4.log"), "w", encoding="utf-8").write(out)
        res["G4_tool"] = "eqy"
        m = re.search(r"Successfully proved designs equivalent", out)
        f = re.search(r"Failed to prove equivalence for (\d+)/(\d+) partitions", out)
        if m:
            res["G4"] = "PROVEN"
        elif f:
            # EQY says "Failed to prove equivalence" for BOTH a real
            # counterexample and a strategy that simply ran out of depth. Those
            # are different verdicts and conflating them reports UNRESOLVED as
            # REFUTED, which is the error this project cares most about.
            # Found 2026-08-31: batch 2's A2 was reported REFUTED when its
            # partition log said "Reached maximum number of time steps", while
            # all 128 tmp_round_key partitions it feeds had been PROVEN.
            # So the failing partitions are classified from their own logs.
            failed = re.findall(
                r"Failed to prove equivalence of partition (\S+)", out)
            bounded, refuted, unknown = [], [], []
            for part in failed:
                logs = glob.glob(os.path.join(
                    wd, "prop", "strategies", part, "*", "run.log"))
                txt = ""
                for lg in logs:
                    try:
                        with open(lg, encoding="utf-8", errors="replace") as fh:
                            txt += fh.read()
                    except OSError:
                        pass
                # Order matters, and so does the exact wording. Yosys prints
                # "SAT temporal induction proof finished - model found for
                # base case: FAIL!" for a real counterexample, and
                # "Reached maximum number of time steps -> proof failed."
                # followed by "Dumping SAT model to VCD file" for a bound.
                # BOTH mention a model, so the discriminator is "model found",
                # not "model". An earlier version of this check matched the
                # literal "model found: FAIL" and therefore missed P4's
                # "model found for base case: FAIL!", reporting a genuine
                # refutation as UNRESOLVED. That is the mirror image of the
                # bug this whole branch exists to fix, and it was caught by
                # re-running a proposal whose verdict was already known.
                if re.search(r"Assert failed|model found", txt):
                    refuted.append(part)
                elif "Reached maximum number of time steps" in txt:
                    bounded.append(part)
                else:
                    unknown.append(part)
            res["G4_failed_partitions"] = failed
            res["G4_counterexample"] = refuted
            res["G4_depth_exhausted"] = bounded
            if refuted:
                res["G4"] = (f"REFUTED ({len(refuted)} partition(s) with a "
                             f"counterexample, {f.group(2)} total)")
            elif bounded or unknown:
                res["G4"] = (f"UNRESOLVED ({len(bounded) + len(unknown)} "
                             f"partition(s) hit the strategy bound, no "
                             f"counterexample found)")
            else:
                res["G4"] = "UNRESOLVED"
        else:
            res["G4"] = "UNRESOLVED"
        print(json.dumps(res, indent=2))
        return

    def parse_ports(spec):
        out = []
        for tok in spec.split(","):
            tok = tok.strip()
            if tok:
                n, _, w = tok.partition(":")
                out.append((n, int(w) if w else 1))
        return out

    dut_clk = dut_rst = True
    if a.outputs is None and mod != "rv32i_core":
        derived = derive_ports(a.yosys, a.rtl, mod)
        if derived is None:
            res["G4"] = ("CANNOT (could not read the port list of %s from %s)"
                         % (mod, a.rtl))
            print(json.dumps(res, indent=2))
            return
        ins, outs, dclk, drst = derived
        res["G4_ports"] = "derived from source (%d inputs, %d outputs, clock=%s, reset=%s)" % (
            len(ins), len(outs), dclk, drst)
        # The miter always keeps its own clock and reset for the harness;
        # the DUT is wired only to the ones it actually has.
        dut_clk, dut_rst = dclk is not None, drst is not None
        clk, rst = dclk or a.clk, drst or a.rst
    else:
        outs = CORE_OUTPUTS if a.outputs is None else parse_ports(a.outputs)
        ins = parse_ports(a.inputs if a.inputs is not None
                          else "imem_data:32,dmem_rdata:32")
        clk, rst = a.clk, a.rst
    miter = build_miter(p, def_id, mod, clk, rst, outs, ins, k, dut_clk, dut_rst)
    mpath = os.path.join(wd, "miter_prop.sv")
    open(mpath, "w", encoding="utf-8").write(miter)

    rp = os.path.join(os.path.abspath(a.repo), "tools", "run_proof.py")
    r = sh([sys.executable, rp, "--top", "miter_prop",
            "--file", "gold.v", "--file", "gate.v", "--file", "miter_prop.sv",
            "--workdir", wd, "--tasks", "bmc,pdr",
            "--depth", str(a.depth), "--timeout", str(a.timeout)]
           + (["--zero-init"] if a.zero_init else []))
    out = r.stdout + r.stderr
    open(os.path.join(wd, "g4.log"), "w", encoding="utf-8").write(out)
    for line in out.splitlines():
        if line.startswith("bmc:"):
            res["G4_bmc"] = line.split(":", 1)[1].strip()
        if line.startswith("pdr:"):
            res["G4_pdr"] = line.split(":", 1)[1].strip()
    bmc, pdr = res.get("G4_bmc", "?"), res.get("G4_pdr", "?")
    if pdr.startswith("PROVEN"):
        res["G4"] = "PROVEN"
    elif bmc.startswith("FAIL") or pdr.startswith("FAIL"):
        # NULL CONTROL before any refutation is reported.
        #
        # Added 2026-09-11. O1 (retime_write_decode_forward on aes_key_mem)
        # came back REFUTED on eq_round_key in 1s. The witness gave the two
        # instances DIFFERENT arbitrary initial contents for key_mem, which
        # Yosys does not apply the module's async reset to, so round_key =
        # key_mem[round] differs at once. Re-running the same miter with the
        # gate replaced by the gold module renamed also FAILED in 1s: the
        # miter refutes this design against ITSELF. With eq_round_key removed
        # the same null control is PROVEN in 12s.
        #
        # A gate that cannot answer must say so rather than answer wrongly.
        # This is the verification-side twin of the timing-side null control
        # in REPORT §5 (swap a module for itself, expect 0.000 delta), and
        # CANNOT is already a first-class outcome in SlackBench.
        #
        # This is the third refutation this project's own harness has
        # manufactured. The other two are in REPORT §9.
        nc = {"p": p, "def_id": def_id, "clk": clk, "rst": rst,
              "dut_clk": dut_clk, "dut_rst": dut_rst,
              "outs": outs, "ins": ins}
        # Cover the counterexample's own depth, not the proposal's budget.
        cx = failing_depth(wd)
        ndepth = min(a.depth, cx + 2) if cx is not None else a.depth
        res["G4_counterexample_step"] = cx
        res["G4_null_depth"] = ndepth
        nl = null_control(a, wd, mod, nc, res, depth=ndepth)
        if nl is True:
            res["G4_null_control"] = "PASS (gold vs gold proves)"
            res["G4"] = "REFUTED"
        elif nl is None:
            res["G4_null_control"] = "INCONCLUSIVE (gold vs gold neither proved nor failed)"
            res["G4"] = ("REFUTED (null control inconclusive: the control did "
                         "not close, so this refutation is not corroborated)")
        else:
            # The control refutes, so SOME output cannot be decided by this
            # harness. Find which, by dropping the one it names and retrying,
            # instead of abandoning the whole module. A proof over the
            # surviving outputs is a real proof, restricted to them, and is
            # reported as partial so it can never be read as full equivalence.
            keep, dropped = list(outs), []
            for _ in range(len(outs)):
                bad = res.get("_null_fail_output")
                if bad is None or not any(n == bad for n, _ in keep):
                    break
                dropped.append(bad)
                keep = [(n, w) for n, w in keep if n != bad]
                if not keep:
                    break
                sub = null_control(a, wd, mod, nc, res, outs=keep,
                                   tag="nullctl_%d" % len(dropped),
                                   depth=ndepth)
                if sub is True:
                    break
                if sub is None:
                    res["G4_null_note"] = (
                        "control inconclusive after dropping %s" % ",".join(dropped))
                    break
            res["G4_undecidable_outputs"] = dropped
            res["G4_decidable_outputs"] = [n for n, _ in keep]
            if not keep:
                res["G4_null_control"] = "REFUTES on every output"
                res["G4"] = ("CANNOT (null control refutes on every output: the "
                             "miter cannot distinguish this module from itself)")
            else:
                # Re-run the real miter over the decidable outputs only.
                io.open(mpath, "w", encoding="utf-8").write(
                    build_miter(p, def_id, mod, clk, rst, keep, ins, k,
                                dut_clk, dut_rst))
                r2 = sh([sys.executable, rp, "--top", "miter_prop",
                         "--file", "gold.v", "--file", "gate.v",
                         "--file", "miter_prop.sv", "--workdir", wd,
                         "--tasks", "bmc,pdr", "--depth", str(a.depth),
                         "--timeout", str(a.timeout)]
                        + (["--zero-init"] if a.zero_init else []))
                o2 = r2.stdout + r2.stderr
                io.open(os.path.join(wd, "g4_partial.log"), "w",
                        encoding="utf-8").write(o2)
                b2 = p2 = "?"
                for line in o2.splitlines():
                    if line.startswith("bmc:"):
                        b2 = line.split(":", 1)[1].strip()
                    if line.startswith("pdr:"):
                        p2 = line.split(":", 1)[1].strip()
                res["G4_partial_bmc"], res["G4_partial_pdr"] = b2, p2
                res["G4_null_control"] = (
                    "REFUTES on %s; PASSES on %s"
                    % (",".join(dropped), ",".join(n for n, _ in keep)))
                suffix = (" (partial: %d of %d outputs; %s undecidable, "
                          "driven by state the reset does not reach)"
                          % (len(keep), len(outs), ",".join(dropped)))
                if p2.startswith("PROVEN"):
                    res["G4"] = "PROVEN" + suffix
                elif b2.startswith("FAIL") or p2.startswith("FAIL"):
                    res["G4"] = "REFUTED" + suffix
                else:
                    res["G4"] = "UNRESOLVED" + suffix
    elif bmc.startswith("ERROR") or pdr.startswith("ERROR"):
        # Added 2026-09-13 (experiments/invariant_obligation/, defect 2). An
        # engine that fails in elaboration never solved anything. Reporting it
        # as UNRESOLVED gave it the same verdict as a budget timeout, which is
        # how two never-gated proposals were recorded as undecidable. REPORT
        # section 9 names the same failure one branch over.
        res["G4"] = "CANNOT (engine error: %s)" % (bmc if bmc.startswith("ERROR") else pdr)[:160]
    else:
        res["G4"] = "UNRESOLVED"
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
