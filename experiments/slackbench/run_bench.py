#!/usr/bin/env python3
"""SlackBench: run every checker on every case and print the confusion matrix.

    python3 experiments/slackbench/run_bench.py --workdir ~/sbench

Checkers scored, all on the same (gold, gate) pair:

  cec        `abc cec`, combinational equivalence
  dsec       `abc dsec`, sequential equivalence
  miter_k    the obligation SlackSmith's type router SELECTS for the case:
             k=0 gets a sequential miter under temporal induction, k!=0 gets
             a k-padded miter. This is the only checker told what k is.
  sim_lazy   simulation holding one operand constant, which is what a person
             writes for a datapath and what a model writes when asked
  sim_aggr   simulation with every input freshly random each cycle

A verdict is mapped to one of:
  ACCEPT  the checker says the pair is fine
  REJECT  the checker says the pair differs
  CANNOT  the checker cannot express the question (e.g. cec on a latency change)
  ERROR   the run broke

Scoring is a confusion matrix against MANIFEST ground truth, never one
number: a checker that answers REJECT to everything would otherwise win.
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases")


def sh(cmd, timeout=900, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        class R: returncode, stdout, stderr = 124, "", "TIMEOUT"
        return R()


def load_cases():
    out = []
    for name in sorted(os.listdir(CASES)):
        d = os.path.join(CASES, name)
        mp = os.path.join(d, "meta.json")
        if os.path.isdir(d) and os.path.exists(mp):
            m = json.load(open(mp))
            m["dir"] = d
            out.append(m)
    return out


# ------------------------------------------------------------------ aiger
def to_aiger(a, src, top, out, tag):
    """AIGER's backend accepts only plain $_DFF_P_, so async resets must be
    made synchronous and the flops legalized first. Without dfflegalize this
    fails with 'Unsupported cell type: $_DFF_PN0_' on every case here, since
    every design in the suite has an async reset."""
    r = sh([a.yosys, "-p",
            f"read_verilog {src}; prep -top {top}; async2sync; memory_map; "
            f"techmap; dfflegalize -cell $_DFF_P_ 0; abc -g AND; opt_clean; "
            f"write_aiger -zinit {out}"])
    ok = r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0
    return ok, r.stdout + r.stderr


def aig_stats(a, path):
    """(inputs, latches) so a CANNOT verdict is evidenced, not just asserted."""
    r = sh([a.abc, "-c", f"read {path}; print_stats"])
    m = re.search(r"i/o\s*=\s*(\d+)\s*/\s*(\d+)\s+lat\s*=\s*(\d+)",
                  re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr))
    return (int(m.group(1)), int(m.group(3))) if m else (None, None)


def check_cec(a, c, wd):
    g1, g2 = os.path.join(wd, "gold.aig"), os.path.join(wd, "gate.aig")
    ok1, l1 = to_aiger(a, os.path.join(c["dir"], "gold.v"), c["top"], g1, "gold")
    ok2, l2 = to_aiger(a, os.path.join(c["dir"], "gate.v"), c["top"], g2, "gate")
    if not (ok1 and ok2):
        return "ERROR", "aiger conversion failed"
    r = sh([a.abc, "-c", f"cec {g1} {g2}"])
    o = r.stdout + r.stderr
    if "Miter computation has failed" in o or "different number of latches" in o:
        i1, l1 = aig_stats(a, g1)
        i2, l2 = aig_stats(a, g2)
        return "CANNOT", (f"cannot build a miter: gold {l1} latches / {i1} inputs, "
                          f"gate {l2} / {i2}")
    if "Networks are equivalent" in o:
        return "ACCEPT", o.strip().splitlines()[-1][:90]
    if "NOT EQUIVALENT" in o or "are not equivalent" in o.lower():
        return "REJECT", o.strip().splitlines()[-1][:90]
    return "ERROR", o.strip()[-120:]


def check_dsec(a, c, wd):
    g1, g2 = os.path.join(wd, "gold.aig"), os.path.join(wd, "gate.aig")
    if not (os.path.exists(g1) and os.path.exists(g2)):
        return "ERROR", "no aiger"
    r = sh([a.abc, "-c", f"dsec {g1} {g2}"])
    o = r.stdout + r.stderr
    if "Networks are equivalent" in o:
        return "ACCEPT", o.strip().splitlines()[-1][:90]
    if "NOT EQUIVALENT" in o or "are not equivalent" in o.lower():
        return "REJECT", o.strip().splitlines()[-1][:90]
    if "Miter computation has failed" in o:
        i1, l1 = aig_stats(a, g1)
        i2, l2 = aig_stats(a, g2)
        return "CANNOT", (f"cannot build a miter: gold {l1} latches / {i1} inputs, "
                          f"gate {l2} / {i2}")
    if "Verification UNDECIDED" in o or "undecided" in o.lower():
        return "CANNOT", "dsec undecided"
    return "ERROR", o.strip()[-120:]


# ------------------------------------------------------------- miter with k
MITER = """module sb_miter (input wire clk, input wire rst_n{extra_in});
{decl_gold}
{decl_gate}
  gold_dut u_gold (.{clk}(clk), .{rst}(rst_n){conn_gold});
  gate_dut u_gate (.{clk}(clk), .{rst}(rst_n){conn_gate});
{delay}
  reg [7:0] warm;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) warm <= 8'h0; else if (warm < 8'hF0) warm <= warm + 8'h1;
  always @(posedge clk) if (rst_n && warm > 8'd{warmup}) begin
{asserts}
  end
endmodule
"""


def gen_miter(c, path):
    """k-padded miter: compare gold delayed by k against gate (k>0), or gate
    delayed by |k| against gold (k<0). k=0 compares directly."""
    k = int(c.get("k", 0))
    ins = c["inputs"]; outs = c["outputs"]
    extra_in = "".join(f",\n  input wire [{w-1}:0] {n}" if w > 1
                       else f",\n  input wire {n}" for n, w in ins.items())
    def wires(sfx):
        return "\n".join(f"  wire [{w-1}:0] {n}_{sfx};" if w > 1
                         else f"  wire {n}_{sfx};" for n, w in outs.items())
    def conn(sfx):
        s = "".join(f", .{n}({n})" for n in ins)
        s += "".join(f", .{n}({n}_{sfx})" for n in outs)
        return s
    delay, asserts = [], []
    for n, w in outs.items():
        decl = f"[{w-1}:0] " if w > 1 else ""
        if k > 0:
            for i in range(k):
                src = f"{n}_gold" if i == 0 else f"{n}_d{i-1}"
                delay.append(f"  reg {decl}{n}_d{i};")
                delay.append(f"  always @(posedge clk) {n}_d{i} <= {src};")
            asserts.append(f"    assert ({n}_d{k-1} == {n}_gate);")
        elif k < 0:
            for i in range(-k):
                src = f"{n}_gate" if i == 0 else f"{n}_e{i-1}"
                delay.append(f"  reg {decl}{n}_e{i};")
                delay.append(f"  always @(posedge clk) {n}_e{i} <= {src};")
            asserts.append(f"    assert ({n}_gold == {n}_e{-k-1});")
        else:
            asserts.append(f"    assert ({n}_gold == {n}_gate);")
    open(path, "w").write(MITER.format(
        extra_in=extra_in, decl_gold=wires("gold"), decl_gate=wires("gate"),
        top=c["top"], clk=c["clk"], rst=c["rst"],
        conn_gold=conn("gold"), conn_gate=conn("gate"),
        delay="\n".join(delay), warmup=abs(k) + 2,
        asserts="\n".join(asserts)))


# -------------------------------------------------------------- simulation
def run_traces(a, c, wd, lazy):
    """Run gold and gate separately under identical stimulus, then align by k."""
    tag = "lazy" if lazy else "aggr"
    outs = {}
    for side in ("gold", "gate"):
        tb = os.path.join(wd, f"tb1_{tag}_{side}.v")
        gen_tb1(c, tb)
        exe = os.path.join(wd, f"s_{tag}_{side}")
        r = sh([a.iverilog, "-o", exe, "-s", "tb", tb,
                os.path.join(c["dir"], f"{side}.v")])
        if r.returncode != 0:
            return None, (r.stdout + r.stderr)[-160:]
        r = sh([a.vvp, exe], timeout=600)
        if r.returncode != 0:
            return None, (r.stdout + r.stderr)[-160:]
        outs[side] = [l.split()[2:] for l in r.stdout.splitlines()
                      if l.startswith("CYC ")]
    return outs, None


TB1 = """`timescale 1ns/1ps
module tb;
  reg clk = 0, rst_n = 0;
  always #5 clk = ~clk;
{decl_in}
{decl_out}
  {top} dut (.{clk}(clk), .{rst}(rst_n){conn});
  integer i;
  integer seed = 32'h0C0FFEE;
  initial begin
    #12 rst_n = 1;
    for (i = 0; i < {n}; i = i + 1) begin
      @(negedge clk);
{drive}
      @(posedge clk);
      #1 $display("CYC %0d {fmt}", i{args});
    end
    $finish;
  end
endmodule
"""


def gen_tb1(c, path, lazy=False, n=None):
    ins = c["inputs"]; outs = c["outputs"]
    n = n or c.get("_n", 20000)
    names = list(ins)
    held = names[-1] if (c.get("_lazy") and len(names) > 1) else None
    decl_in = "\n".join(f"  reg [{w-1}:0] {x} = 0;" if w > 1 else f"  reg {x} = 0;"
                        for x, w in ins.items())
    decl_out = "\n".join(f"  wire [{w-1}:0] {o};" if w > 1 else f"  wire {o};"
                         for o, w in outs.items())
    conn = ("".join(f", .{x}({x})" for x in ins)
            + "".join(f", .{o}({o})" for o in outs))
    drive = []
    for x, w in ins.items():
        if x == held:
            drive.append(f"      {x} = {w}'d7;")
        else:
            drive.append(f"      {x} = $random(seed);")
    fmt = " ".join(["%0d"] * len(outs))
    args = "".join(f", {o}" for o in outs)
    open(path, "w").write(TB1.format(
        decl_in=decl_in, decl_out=decl_out, top=c["top"],
        clk=c["clk"], rst=c["rst"], conn=conn, n=n,
        drive="\n".join(drive), fmt=fmt, args=args))


def check_sim_pair(a, c, wd, lazy):
    c = dict(c); c["_lazy"] = lazy; c["_n"] = 20000
    tr, err = run_traces(a, c, wd, lazy)
    if tr is None:
        return "ERROR", err
    k = int(c.get("k", 0))
    g, t = tr["gold"], tr["gate"]
    lo = abs(k) + 2
    n = min(len(g), len(t)) - abs(k) - 2
    for i in range(lo, lo + max(n, 0)):
        gi, ti = (i, i + k) if k >= 0 else (i - k, i)
        if gi < len(g) and ti < len(t) and g[gi] != t[ti]:
            return "REJECT", f"differs at cycle {i}: {g[gi]} vs {t[ti]}"
    return "ACCEPT", f"{max(n,0)} cycles, no difference"


def check_miter(a, c, wd):
    """The obligation SlackSmith's type router SELECTS for this case: k=0 gets
    a plain sequential miter, k!=0 gets a k-padded one. Discharged formally by
    temporal induction, not by simulation. This is the only checker that is
    told what k is, which is the whole of SlackSmith's claim."""
    m = os.path.join(wd, "miter.v")
    gen_miter(c, m)
    top = c["top"]
    script = (
        f"read_verilog {os.path.join(c['dir'], 'gold.v')}; "
        f"rename {top} gold_dut; design -stash gold; "
        f"read_verilog {os.path.join(c['dir'], 'gate.v')}; "
        f"rename {top} gate_dut; design -stash gate; "
        f"design -copy-from gold -as gold_dut gold_dut; "
        f"design -copy-from gate -as gate_dut gate_dut; "
        f"read_verilog -formal {m}; "
        # `sat` operates on exactly one module, so the two instantiated DUTs
        # must be flattened into the miter first.
        f"prep -top sb_miter; flatten; async2sync; opt; "
        f"sat -tempinduct -prove-asserts -seq 8 -verify")
    r = sh([a.yosys, "-p", script], timeout=900)
    o = r.stdout + r.stderr
    open(os.path.join(wd, "miter.log"), "w", errors="replace").write(o)
    if "SUCCESS" in o and "Temporal induction successful" in o:
        return "ACCEPT", "temporal induction successful"
    if "SUCCESS" in o:
        return "ACCEPT", "sat proof succeeded"
    if "FAIL" in o or "Assert failed" in o:
        return "REJECT", "counterexample found by the padded miter"
    if r.returncode == 124:
        return "CANNOT", "timeout"
    return "ERROR", o.strip()[-140:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--yosys", default=os.path.expanduser("~/tools/oss-cad-suite/bin/yosys"))
    ap.add_argument("--abc", default=os.path.expanduser("~/tools/oss-cad-suite/bin/yosys-abc"))
    ap.add_argument("--iverilog", default=os.path.expanduser("~/tools/oss-cad-suite/bin/iverilog"))
    ap.add_argument("--vvp", default=os.path.expanduser("~/tools/oss-cad-suite/bin/vvp"))
    a = ap.parse_args()
    a.workdir = os.path.expanduser(a.workdir)

    checkers = [("cec", check_cec), ("dsec", check_dsec),
                ("sim_lazy", lambda A, C, W: check_sim_pair(A, C, W, True)),
                ("sim_aggr", lambda A, C, W: check_sim_pair(A, C, W, False)),
                ("miter_k", check_miter)]

    rows = []
    for c in load_cases():
        wd = os.path.join(a.workdir, c["case"])
        os.makedirs(wd, exist_ok=True)
        print(f"=== {c['case']} ({c['class']}, truth {c['ground_truth']}, k={c['k']})")
        for name, fn in checkers:
            verdict, detail = fn(a, c, wd)
            rows.append({"case": c["case"], "class": c["class"],
                         "truth": c["ground_truth"], "k": c["k"],
                         "checker": name, "verdict": verdict,
                         "detail": (detail or "")[:120],
                         "circular": name in c.get("circular_for", [])})
            print(f"    {name:<9} {verdict:<7} {(detail or '')[:70]}")

    res = os.path.join(HERE, "results")
    os.makedirs(res, exist_ok=True)
    json.dump(rows, open(os.path.join(res, "raw.json"), "w"), indent=1)
    with open(os.path.join(res, "raw.tsv"), "w") as f:
        f.write("case\tclass\ttruth\tk\tchecker\tverdict\tcircular\tdetail\n")
        for r in rows:
            f.write("\t".join(str(r[x]) for x in
                    ("case", "class", "truth", "k", "checker", "verdict",
                     "circular", "detail")) + "\n")
    print(f"\nwrote {res}/raw.tsv")


if __name__ == "__main__":
    main()
