#!/usr/bin/env python3
"""Arms A to E of experiments/flatten_control/PREREGISTRATION.md.

Runs from WSL:
    python3 experiments/flatten_control/run.py --workdir ~/flatexp

Uses tools/remeasure.synth_bench_top (the loop's own synthesis path) so the
only differences between arms are the two registered switches. Every arm is
timed under sdc/bench_top_v3.sdc with report_checks -fields {fanout} and
classified by tools/classify_path.py. Writes results/summary.tsv and one
report per arm and clock into results/.
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
import remeasure                      # noqa: E402
import classify_path                  # noqa: E402
from slacksmith import BUF_ONLY, BOTH, _HEAD  # noqa: E402

CLOCKS = ("clk_a", "clk_b", "clk_e")
# Amendment 1: -p buffers ABC's primary inputs, which is where flop outputs
# sit once dfflibmap has mapped the flops before abc runs.
BUF_P = _HEAD + ";buffer,-N,16,-p"
BOTH_P = _HEAD + ";buffer,-N,16,-p;upsize;dnsize"
ABC_LABEL = {None: "default", BUF_ONLY: "buffer_only", BOTH: "buffer_size",
             BUF_P: "buffer_pi", BOTH_P: "buffer_pi_size"}
ARMS = [
    ("A", False, None),
    ("B", False, BUF_ONLY),
    ("C", True, None),
    ("D", True, BUF_ONLY),
    ("E", True, BOTH),
    ("F", True, BUF_P),
    ("G", True, BOTH_P),
]


def time_arm(sta, liberty, net, sdc, outdir, tag):
    tcl = os.path.join(outdir, f"{tag}.tcl")
    lines = [f"read_liberty {liberty}", f"read_verilog {net}", "link_design bench_top",
             f"read_sdc {sdc}"]
    for c in CLOCKS:
        lines.append(f'puts "---CLOCK:{c}---"')
        lines.append(f"report_checks -path_delay max -to [get_clocks {c}] "
                     f"-group_path_count 1 -digits 3 -fields {{fanout}}")
    lines.append("exit")
    open(tcl, "w").write("\n".join(lines) + "\n")
    p = subprocess.run([sta, "-no_init", "-no_splash", "-exit", tcl],
                       capture_output=True, text=True)
    out = p.stdout + p.stderr
    reports = {}
    for c in CLOCKS:
        marker = f"---CLOCK:{c}---"
        if marker not in out:
            continue
        seg = out.split(marker, 1)[1]
        nxt = [out.split(marker, 1)[1].find(f"---CLOCK:{d}---") for d in CLOCKS
               if d != c and f"---CLOCK:{d}---" in seg]
        end = min([n for n in nxt if n >= 0], default=len(seg))
        reports[c] = seg[:end]
    return reports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--yosys-bin", default=os.path.expanduser("~/tools/oss-cad-suite/bin/yosys"))
    ap.add_argument("--sta-bin", default=os.path.expanduser("~/tools/OpenSTA/build/sta"))
    ap.add_argument("--liberty", default=os.path.expanduser("~/sta_work/sky130hd_tt.lib"))
    ap.add_argument("--sdc", default=os.path.join(REPO, "sdc", "bench_top_v3.sdc"))
    ap.add_argument("--arms", default="ABCDE")
    a = ap.parse_args()
    a.workdir = os.path.expanduser(a.workdir)
    os.makedirs(a.workdir, exist_ok=True)
    res = os.path.join(HERE, "results")
    os.makedirs(res, exist_ok=True)

    ndu = len(remeasure.dont_use_flags(a.liberty).split())
    if ndu < 2:
        sys.exit(f"FATAL: dont_use returned {ndu} flags, expected >= 2")
    print(f"dont_use flags: {ndu}")

    # A partial run (--arms FG) keeps the rows of arms it does not re-run.
    prev = os.path.join(res, "summary.json")
    rows = [r for r in (json.load(open(prev)) if os.path.exists(prev) else [])
            if r["arm"] not in a.arms]
    for arm, flat, abc in ARMS:
        if arm not in a.arms:
            continue
        d = os.path.join(a.workdir, arm)
        print(f"\n=== arm {arm}: flatten={flat} abc={'default' if abc is None else abc.split(';&put;')[-1]}")
        net = remeasure.synth_bench_top(a.yosys_bin, os.path.join(REPO, "rtl"),
                                        remeasure.BENCH_TOP_FILES, a.liberty, d,
                                        "mapped.v", abc_script=abc, flatten=flat)
        cells = sum(1 for l in open(net, encoding="utf-8", errors="replace")
                    if "sky130_fd_sc_hd__" in l)
        reports = time_arm(a.sta_bin, a.liberty, net, a.sdc, d, "q")
        for c in CLOCKS:
            rpt = reports.get(c, "")
            open(os.path.join(res, f"{arm}_{c}.rpt"), "w").write(rpt)
            cl = classify_path.classify(rpt, net, "bench_top")
            top = (cl.get("top_cells") or [{}])[0]
            rows_c, _s, _m = classify_path.parse_path(rpt)
            maxfo = max((r["report_fanout"] or 0) for r in rows_c) if rows_c else None
            row = dict(arm=arm, flatten=flat, abc=ABC_LABEL.get(abc, abc),
                       cells=cells, clock=c, slack=cl.get("slack_ns"), verdict=cl.get("verdict"),
                       share=cl.get("fanout_delay_share"), path_delay=cl.get("path_delay_ns"),
                       cells_on_path=cl.get("cells_on_path"), top_cell=top.get("cell"),
                       top_incr=top.get("incr_ns"), top_fanout=top.get("fanout"),
                       max_fanout_on_path=maxfo, fanout_source=cl.get("fanout_source"))
            rows.append(row)
            print(f"  {c}: slack {row['slack']}  {row['verdict']} share {row['share']}  "
                  f"top {row['top_cell']} {row['top_incr']} ns fanout {row['top_fanout']}  "
                  f"max fanout on path {maxfo}")

    rows.sort(key=lambda r: (r["arm"], CLOCKS.index(r["clock"])))
    keys = list(rows[0].keys())
    with open(os.path.join(res, "summary.tsv"), "w") as f:
        f.write("\t".join(keys) + "\n")
        for r in rows:
            f.write("\t".join(str(r[k]) for k in keys) + "\n")
    json.dump(rows, open(os.path.join(res, "summary.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(res, 'summary.tsv')}")


if __name__ == "__main__":
    main()
