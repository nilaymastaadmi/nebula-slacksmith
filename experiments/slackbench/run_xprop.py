#!/usr/bin/env python3
"""Run the XPROP addendum. Registered in PREREGISTRATION_xprop.md.

    python3 experiments/slackbench/run_xprop.py --workdir ~/sbx

Scored on its own and never folded into any Tier B number.

The two checkers that matter are the SAME simulation with the SAME stimulus
on the SAME design pair, differing only in the comparison operator. `==`
yields `x` when either side is unknown and `if (x)` takes the false branch,
so the mismatch is skipped. `!==` compares four-state and does not.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASE = os.path.join(HERE, "cases_xprop", "XPROP-1")

TB = """`timescale 1ns/1ps
module tb;
  reg clk = 0, rst_n = 0, we = 0;
  reg [7:0] d = 0;
  wire [7:0] s_gold, s_gate;
  integer i, seed = 32'h0C0FFEE, mismatches = 0, skipped = 0;
  always #5 clk = ~clk;
  sb_gold u_gold (.clk(clk), .rst_n(rst_n), .we(we), .d(d), .status(s_gold));
  sb_gate u_gate (.clk(clk), .rst_n(rst_n), .we(we), .d(d), .status(s_gate));
  initial begin
    #12 rst_n = 1;
    for (i = 0; i < 500; i = i + 1) begin
      @(negedge clk);
      // `we` stays LOW for the first 50 cycles, which is the window where the
      // un-reset register is still unknown. This is not a contrived stimulus:
      // it is simply not writing before reading.
      we = (i < 50) ? 1'b0 : ($random(seed) & 1);
      d  = $random(seed);
      @(posedge clk);
      #1;
      if ({cmp}) mismatches = mismatches + 1;
      if ((s_gold === s_gate) !== 1'b1 && (s_gold !== s_gate) !== 1'b1)
        skipped = skipped + 1;
    end
    $display("RESULT mismatches=%0d", mismatches);
    $finish;
  end
endmodule
"""


def run(a, cmp_expr, tag):
    wd = a.workdir
    os.makedirs(wd, exist_ok=True)
    # one module name each so both elaborate together
    for side, newname in (("gold", "sb_gold"), ("gate", "sb_gate")):
        src = open(os.path.join(CASE, f"{side}.v"), encoding="utf-8").read()
        open(os.path.join(wd, f"{side}.v"), "w").write(
            src.replace("module sb_stat", f"module {newname}"))
    tb = os.path.join(wd, f"tb_{tag}.v")
    open(tb, "w").write(TB.replace("{cmp}", cmp_expr))
    exe = os.path.join(wd, f"sim_{tag}")
    r = subprocess.run([a.iverilog, "-o", exe, "-s", "tb", tb,
                        os.path.join(wd, "gold.v"), os.path.join(wd, "gate.v")],
                       capture_output=True, text=True)
    if r.returncode:
        return "ERROR", (r.stdout + r.stderr)[-200:]
    r = subprocess.run([a.vvp, exe], capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    open(os.path.join(wd, f"{tag}.log"), "w").write(out)
    n = None
    for line in out.splitlines():
        if line.startswith("RESULT mismatches="):
            n = int(line.split("=")[1])
    if n is None:
        return "ERROR", out[-200:]
    return ("REJECT" if n else "ACCEPT"), f"{n} mismatching cycles of 500"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--iverilog", default=os.path.expanduser("~/tools/oss-cad-suite/bin/iverilog"))
    ap.add_argument("--vvp", default=os.path.expanduser("~/tools/oss-cad-suite/bin/vvp"))
    a = ap.parse_args()
    a.workdir = os.path.expanduser(a.workdir)

    rows = []
    for tag, cmp_expr, label in (
            ("eq", "s_gold != s_gate", "sim_eq, comparison with !=  (2-state)"),
            ("neq", "s_gold !== s_gate", "sim_neq, comparison with !== (4-state)")):
        v, detail = run(a, cmp_expr, tag)
        rows.append({"case": "XPROP-1", "checker": f"sim_{tag}",
                     "truth": "NOT_EQUIVALENT", "verdict": v, "detail": detail})
        print(f"  {label:<42} {v:<8} {detail}")

    res = os.path.join(HERE, "results")
    os.makedirs(res, exist_ok=True)
    json.dump(rows, open(os.path.join(res, "xprop.json"), "w"), indent=1)
    print(f"\nwrote {res}/xprop.json")
    print("X3: the two rows above used identical stimulus and an identical "
          "design pair. Any difference between them is the comparison operator.")


if __name__ == "__main__":
    main()
