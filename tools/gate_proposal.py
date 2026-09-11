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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", required=True)
    ap.add_argument("--rtl", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--yosys", default=os.environ.get("OSS_CAD_BIN", os.path.expanduser("~/tools/oss-cad-suite/bin")) + "/yosys")
    ap.add_argument("--depth", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--repo", default=".")
    # Batch 2 (experiments/llm_proposer_aes) targets a different module with
    # a different port list. Every default below is the batch-1 rv32i_core
    # setting, so batch 1 reproduces unchanged.
    ap.add_argument("--module", default="rv32i_core")
    ap.add_argument("--clk", default="clk")
    ap.add_argument("--rst", default="rst_n")
    ap.add_argument("--outputs", default=None)
    ap.add_argument("--inputs", default="imem_data:32,dmem_rdata:32")
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

    mod = a.module
    gold = os.path.join(wd, "gold.v")
    gate = os.path.join(wd, "gate.v")
    if p.get("variant_file"):
        # Batch 2 proposals are complete rewritten modules, not splices.
        gate_src = io.open(os.path.join(a.repo, p["variant_file"]), encoding="utf-8").read()
    else:
        gate_src = splice(src, p)
    def rename(text, suffix):
        # SystemVerilog allows `endmodule : name`; renaming only the header
        # leaves a mismatched end label and Yosys refuses to elaborate. Found
        # 2026-09-02 on the aes design of the Dr. RTL benchmark, where both
        # phase-4 variants failed G1 for this reason and not for any defect.
        text = text.replace("module " + mod, "module " + mod + suffix, 1)
        return re.sub(r"(endmodule\s*:\s*)" + re.escape(mod) + r"\b",
                      r"\g<1>" + mod + suffix, text)
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
    # Branch selection follows the DECLARED tier, which is the whole point of
    # the typed library. For k=0 with dff_delta==0 the two designs have a 1:1
    # flop correspondence, so the obligation is COMBINATIONAL equivalence and
    # EQY is the right (and far cheaper) tool: an earlier version of this
    # harness built a full sequential miter for every proposal and timed out
    # at 240s on both engines against 2,048 flops, which measured the harness
    # rather than the transform.
    if k == 0 and branch not in STATE_REMAP_BRANCHES:
        eqy_cfg = os.path.join(wd, "prop.eqy")
        svf = sv_flag(gold)
        open(eqy_cfg, "w", encoding="utf-8").write(
            "[gold]\nread_verilog" + svf + " gold.v\nprep -top " + mod + "_gold\n\n"
            "[gate]\nread_verilog" + svf + " gate.v\nrename " + mod + "_gate " + mod + "_gold\n"
            "prep -top " + mod + "_gold\n\n"
            "[strategy sat]\nuse sat\ndepth 5\n")
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

    outs = CORE_OUTPUTS if a.outputs is None else parse_ports(a.outputs)
    ins = parse_ports(a.inputs)
    clk, rst = a.clk, a.rst
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
    miter = f"""// generated by tools/gate_proposal.py for {p['id']} ({def_id}), declared k={k}
module miter_prop (
    input wire {clk}, input wire {rst},
{in_decl}    input wire _unused_tie
);
{chr(10).join(decl)}

    {mod}_gold u_g (
        .{clk}({clk}), .{rst}({rst}), {in_conn},
{chr(10).join(inst_g)[:-1]}
    );
    {mod}_gate u_t (
        .{clk}({clk}), .{rst}({rst}), {in_conn},
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
    mpath = os.path.join(wd, "miter_prop.sv")
    open(mpath, "w", encoding="utf-8").write(miter)

    rp = os.path.join(os.path.abspath(a.repo), "tools", "run_proof.py")
    r = sh([sys.executable, rp, "--top", "miter_prop",
            "--file", "gold.v", "--file", "gate.v", "--file", "miter_prop.sv",
            "--workdir", wd, "--tasks", "bmc,pdr",
            "--depth", str(a.depth), "--timeout", str(a.timeout)])
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
        res["G4"] = "REFUTED"
    else:
        res["G4"] = "UNRESOLVED"
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
