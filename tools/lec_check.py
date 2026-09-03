#!/usr/bin/env python3
"""G6: prove two gate-level netlists logically equivalent.

    python3 tools/lec_check.py --gold prerepair.v --gate repaired.v \
        --liberty ~/sta_work/sky130hd_tt.lib --top bench_top --workdir ~/lec

Prints a JSON verdict and exits 0 only on PROVEN.

WHY THIS EXISTS. Until 2026-09-03 this project gated RTL transforms with a
formal obligation and took physical steps on trust, because four attempts to
verify OpenROAD's `repair_design` had failed. All four failed for mundane
reasons (see experiments/openroad_repair/NOTES.md); the check actually costs
38 seconds. With this, every step the loop takes carries a proof.

THE GUARD THAT MATTERS. `equiv_make` pairs wires by NAME. Hand it two
netlists from different name domains and it silently produces almost no
equivalence points, then cheerfully proves all of them. That is exactly how
attempt 1 "succeeded" at 86 points on a 55K-cell design while checking
essentially nothing. So a verdict of PROVEN additionally requires the
compare-point count to be at least --min-points, and the count is always
reported. A LEC that checks nothing must not be allowed to look like a pass.
"""
import argparse, json, os, re, subprocess, sys

SCRIPT = """read_liberty -ignore_miss_func -ignore_miss_dir {lib}
read_verilog {gold}
splitnets -ports
hierarchy -top {top}
flatten
rename -top gold
design -stash gold

read_liberty -ignore_miss_func -ignore_miss_dir {lib}
read_verilog {gate}
splitnets -ports
hierarchy -top {top}
flatten
rename -top gate
design -stash gate

design -copy-from gold -as gold gold
design -copy-from gate -as gate gate

equiv_make gold gate equiv
prep -flatten -top equiv
# Yosys' SAT backend has no model for an async flop, and every flop in this
# benchmark has an async reset. Applied to the merged module, so gold and
# gate are transformed identically and the comparison stays sound.
async2sync
equiv_struct
equiv_simple -seq {seq}
equiv_induct -seq {induct}
equiv_status
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--liberty", required=True)
    ap.add_argument("--top", default="bench_top")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--yosys-bin", default=os.path.expanduser("~/tools/oss-cad-suite/bin/yosys"))
    ap.add_argument("--seq", type=int, default=10)
    ap.add_argument("--induct", type=int, default=4)
    ap.add_argument("--min-points", type=int, default=100,
                    help="fewer compare points than this is reported SUSPECT, never PROVEN")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()

    os.makedirs(a.workdir, exist_ok=True)
    for p in (a.gold, a.gate, a.liberty):
        if not os.path.exists(os.path.expanduser(p)):
            print(json.dumps({"verdict": "ERROR", "reason": f"missing input {p}"}))
            sys.exit(2)

    ys = os.path.join(a.workdir, "lec.ys")
    log = os.path.join(a.workdir, "lec.log")
    open(ys, "w").write(SCRIPT.format(
        lib=os.path.expanduser(a.liberty), gold=os.path.expanduser(a.gold),
        gate=os.path.expanduser(a.gate), top=a.top, seq=a.seq, induct=a.induct))

    try:
        r = subprocess.run([a.yosys_bin, "-s", ys], capture_output=True,
                           text=True, timeout=a.timeout)
        out = r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        print(json.dumps({"verdict": "TIMEOUT", "seconds": a.timeout}))
        sys.exit(3)
    open(log, "w", encoding="utf-8", errors="replace").write(out)

    m = re.findall(r"Found (\d+) \$equiv cells in \S+:\s*\n\s*Of those cells (\d+) "
                   r"are proven and (\d+) are unproven", out)
    proven_line = "Equivalence successfully proven!" in out
    if not m:
        res = {"verdict": "ERROR", "reason": "no equiv_status summary found",
               "tail": out[-600:]}
        print(json.dumps(res)); sys.exit(2)

    total, proven, unproven = (int(x) for x in m[-1])
    res = {"gold": a.gold, "gate": a.gate, "compare_points": total,
           "proven": proven, "unproven": unproven,
           "yosys_says_proven": proven_line, "log": log}

    if unproven or not proven_line:
        res["verdict"] = "NOT_PROVEN"
    elif total < a.min_points:
        # The attempt-1 failure mode: a name-domain mismatch yields a handful
        # of points and proves them all. That is not a check.
        res["verdict"] = "SUSPECT"
        res["reason"] = (f"only {total} compare points, below --min-points "
                         f"{a.min_points}; likely a name-domain mismatch, "
                         f"not a real equivalence check")
    else:
        res["verdict"] = "PROVEN"

    print(json.dumps(res, indent=1))
    sys.exit(0 if res["verdict"] == "PROVEN" else 1)


if __name__ == "__main__":
    main()
