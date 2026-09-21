#!/usr/bin/env python3
"""Show the legality gate failing, through the harness's own code.

PREREGISTRATION.md: "one planted functional defect in a copy of a C2 netlist
must come back FAILED, and the unmodified copy PROVEN. If it cannot be made to
fail, every legality verdict in this study is VOID."

This imports run_arms.synth, run_arms.cec and run_arms.netinfo, so what is
tested is the code that produced the study's verdicts, not a separate probe.
Two defect classes, one per legality claim that can be wrong silently:

  functional  one gate swapped for a same-pin gate of a different function;
              the CEC gate must not return PROVEN
  interface   one output port renamed; the port signature must differ

Writes /results/cec_gate_test.json and exits non-zero on any wrong verdict.
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_arms as R  # noqa: E402

DESIGN = "DSP"            # development design; the probe showed 13 unproven points here
SWAPS = [("nand2_1", "nor2_1"), ("nor2_1", "nand2_1"), ("and2_0", "or2_0"),
         ("and2_1", "or2_1"), ("xor2_1", "xnor2_1")]


def main():
    R.init_worker()
    cfg = json.load(open("/designs/syn_flow/design_all.json"))
    top, clk, _rst, ext = cfg[DESIGN]
    src = f"/designs/rtl_dataset/{DESIGN}.v0.{ext}"
    wd = "/work/gate_test"
    shutil.rmtree(wd, ignore_errors=True)
    os.makedirs(wd)
    c0, c2 = os.path.join(wd, "c0.v"), os.path.join(wd, "c2.v")
    assert R.synth(src, ext, top, c0, None)[0] == "OK", "C0 synth failed"
    assert R.synth(src, ext, top, c2, R.HEAD + ";buffer,-N,16")[0] == "OK", "C2 synth failed"
    res = {"design": DESIGN, "harness": "run_arms.cec / run_arms.netinfo"}

    # Control: unmodified C2 must be PROVEN.
    res["control"] = R.cec(c0, c2, top, wd, "control")

    # Functional defect: first gate of a swappable type, exactly one line changed.
    txt = open(c2).read()
    for a, b in SWAPS:
        pat = re.compile(rf"^(\s*)sky130_fd_sc_hd__{a}(\s)", re.M)
        if pat.search(txt):
            bad = pat.sub(rf"\1sky130_fd_sc_hd__{b}\2", txt, count=1)
            break
    else:
        sys.exit("BROKEN: no swappable gate found in the C2 netlist")
    changed = sum(1 for x, y in zip(txt.splitlines(), bad.splitlines()) if x != y)
    assert changed == 1, f"planted {changed} lines, expected 1"
    badf = os.path.join(wd, "c2_functional_defect.v")
    open(badf, "w").write(bad)
    res["functional_defect"] = {"swap": f"{a}->{b}", "lines_changed": changed,
                                **R.cec(c0, badf, top, wd, "functional")}

    # Interface defect: rename the first output port everywhere in the module.
    ports0 = R.netinfo(c2, top, wd, "p0")["ports"]
    out = next(n for n, d, w in ports0 if d == "output")
    ren = re.sub(rf"\b{re.escape(out)}\b", out + "_renamed", txt)
    renf = os.path.join(wd, "c2_interface_defect.v")
    open(renf, "w").write(ren)
    ports1 = R.netinfo(renf, top, wd, "p1")["ports"]
    res["interface_defect"] = {"renamed": out, "signature_differs": ports0 != ports1}

    ok = (res["control"]["cec"] == "PROVEN"
          and res["functional_defect"]["cec"] != "PROVEN"
          and res["interface_defect"]["signature_differs"])
    res["gate_can_fail"] = ok
    os.makedirs("/results", exist_ok=True)
    json.dump(res, open("/results/cec_gate_test.json", "w"), indent=2, sort_keys=True)
    print(json.dumps(res, indent=2, sort_keys=True))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
