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
import argparse, json, os, re, subprocess, sys

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


def stats(yosys, path, top, workdir, tag):
    log = os.path.join(workdir, f"{tag}.synth.log")
    r = sh([yosys, "-p", f"read_verilog {path}; hierarchy -check -top {top}; synth -top {top}; stat"])
    with open(log, "w", encoding="utf-8") as f:
        f.write(r.stdout + r.stderr)
    if r.returncode != 0:
        return None, log
    txt = r.stdout
    cells = re.findall(r"^\s+(\d+)\s+cells\s*$", txt, re.M)
    dff = sum(int(n) for n in re.findall(r"^\s+(\d+)\s+\$_(?:S?DFF|DFFE)[_A-Z0-9]*\s*$", txt, re.M))
    latch = len([1 for m in re.finditer(r"DLATCH", txt) if "Executing" not in m.string[max(0, m.start()-60):m.start()]])
    return {"cells": int(cells[-1]) if cells else None, "dff": dff, "latch_lines": latch}, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proposal", required=True)
    ap.add_argument("--rtl", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--yosys", default=os.path.expanduser("~/tools/oss-cad-suite/bin/yosys"))
    ap.add_argument("--depth", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--repo", default=".")
    a = ap.parse_args()

    wd = os.path.expanduser(a.workdir)
    os.makedirs(wd, exist_ok=True)
    p = json.load(open(a.proposal, encoding="utf-8"))
    src = open(a.rtl, encoding="utf-8").read()
    res = {"id": p["id"], "def_id": p["def_id"], "declared_k": p["latency_delta_k"]}

    gold = os.path.join(wd, "gold.v")
    gate = os.path.join(wd, "gate.v")
    open(gold, "w", encoding="utf-8").write(src.replace("module rv32i_core", "module rv32i_core_gold", 1))
    open(gate, "w", encoding="utf-8").write(splice(src, p).replace("module rv32i_core", "module rv32i_core_gate", 1))

    # ---- G1 / G2
    gs, _ = stats(a.yosys, gold, "rv32i_core_gold", wd, "gold")
    ts, tlog = stats(a.yosys, gate, "rv32i_core_gate", wd, "gate")
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
    k = p["latency_delta_k"]
    d = ts["dff"] - gs["dff"]
    if k == 0 and d != 0:
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
    if k == 0:
        eqy_cfg = os.path.join(wd, "prop.eqy")
        open(eqy_cfg, "w", encoding="utf-8").write(
            "[gold]\nread_verilog gold.v\nprep -top rv32i_core_gold\n\n"
            "[gate]\nread_verilog gate.v\nrename rv32i_core_gate rv32i_core_gold\n"
            "prep -top rv32i_core_gold\n\n"
            "[strategy sat]\nuse sat\ndepth 5\n")
        eqy = os.path.expanduser("~/tools/oss-cad-suite/bin/eqy")
        r = sh([eqy, "-f", "prop.eqy"], cwd=wd, timeout=a.timeout)
        out = r.stdout + r.stderr
        open(os.path.join(wd, "g4.log"), "w", encoding="utf-8").write(out)
        res["G4_tool"] = "eqy"
        m = re.search(r"Successfully proved designs equivalent", out)
        f = re.search(r"Failed to prove equivalence for (\d+)/(\d+) partitions", out)
        if m:
            res["G4"] = "PROVEN"
        elif f:
            res["G4"] = f"REFUTED ({f.group(1)}/{f.group(2)} partitions unproven)"
        else:
            res["G4"] = "UNRESOLVED"
        print(json.dumps(res, indent=2))
        return

    outs = CORE_OUTPUTS
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
        pipe_blk = ("    always @(posedge clk or negedge rst_n) begin\n"
                    "        if (!rst_n) begin\n"
                    + "\n".join(f"            gp_{n} <= 0;" for n, _ in outs) +
                    "\n        end else begin\n" + "\n".join(pipe) + "\n        end\n    end\n")
    prime = ("    reg [3:0] pr;\n"
             "    always @(posedge clk or negedge rst_n)\n"
             f"        if (!rst_n) pr <= 0; else if (pr < {max(k,1)}) pr <= pr + 1;\n"
             f"    wire primed = (pr >= {max(k,1)});\n")
    miter = f"""// generated by tools/gate_proposal.py for {p['id']} ({p['def_id']}), declared k={k}
module miter_prop (
    input wire clk, input wire rst_n,
    input wire [31:0] imem_data, input wire [31:0] dmem_rdata
);
{chr(10).join(decl)}

    rv32i_core_gold u_g (
        .clk(clk), .rst_n(rst_n), .imem_data(imem_data), .dmem_rdata(dmem_rdata),
{chr(10).join(inst_g)[:-1]}
    );
    rv32i_core_gate u_t (
        .clk(clk), .rst_n(rst_n), .imem_data(imem_data), .dmem_rdata(dmem_rdata),
{chr(10).join(inst_t)[:-1]}
    );

{pipe_blk}{prime}
`ifdef FORMAL
    initial assume (!rst_n);
    always @(posedge clk) begin
        if (rst_n && primed) begin
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
