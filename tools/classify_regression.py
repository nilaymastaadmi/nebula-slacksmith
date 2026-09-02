#!/usr/bin/env python3
"""Regression for tools/classify_path.py against OpenSTA's own fanout column.

    python3 tools/classify_regression.py

Fixtures in experiments/classifier_regression/: a gzipped mapped netlist plus
two reports of the same path, one written with `-fields {fanout}` (ground
truth for every cell's leaf-pin fanout) and one without (what every loop run
before 2026-09-03 gave the classifier).

Why this exists. On 2026-09-03 the loop's own log showed a 6.762 ns and2_1 at
"fanout 1" and a 1.952 ns a21oi_1 at "fanout 0". OpenSTA reports 387 and 59.
The netlist parser charged a submodule connection only when its text equalled
a net name, so `.sboxw(tmp_sboxw)` (whole bus) and
`.imem_data({imem_data[2], imem_data[2], ...})` (one bit fanned into 20 port
bits) were charged nothing, and both paths were classified DEPTH_DOMINATED at
share 0.000. Both are MIXED.

What must hold:
  1. With the fanout report, the verdict and share are as recorded here.
  2. Without it (netlist only), the verdict is the same and every cell at or
     above FANOUT_HI has the same fanout as OpenSTA reports. Cells below
     FANOUT_HI may still disagree where a net leaves a module through an
     output port (loads resolved downward only); those are printed, not
     failed, and the count is recorded.
"""
import gzip, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import classify_path as cp  # noqa: E402

FIX = os.path.join(HERE, "..", "experiments", "classifier_regression")

# (netlist.gz, report stem, top, expected verdict, expected share,
#  expected top-cell fanout). Expected values are OpenSTA's, read from the
# fanout report, so the netlist-only path is being checked against the tool
# that timed the path, not against itself.
CASES = [
    ("v3_bufonly_it4.v.gz", "v3_bufonly_it4_clk_e", "bench_top", "MIXED", 0.2864, 59),
    ("v3_bufsize_it3.v.gz", "v3_bufsize_it3_clk_a", "bench_top", "MIXED", 0.4277, 387),
    # Dr. RTL designs (experiments/drrtl_transfer/): output-port cases, where
    # the driven net's loads sit in the parent module.
    ("drrtl_tv80_A.v.gz", "drrtl_tv80_A", "tv80s", "MIXED", 0.3684, 34),
    ("drrtl_DSP_A.v.gz", "drrtl_DSP_A", "DSP", "DEPTH_DOMINATED", 0.1101, 53),
    ("drrtl_cpu_pipe_A.v.gz", "drrtl_cpu_pipe_A", "dcpu16_cpu", "DEPTH_DOMINATED", 0.18, 78),
]


def main():
    tmp = tempfile.mkdtemp(prefix="classify_reg_")
    failures = 0
    for gz, stem, top, want_v, want_share, want_fo in CASES:
        net = os.path.join(tmp, gz[:-3])
        with gzip.open(os.path.join(FIX, gz), "rb") as fi, open(net, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        with_f = open(os.path.join(FIX, stem + ".fanout.rpt"), encoding="utf-8").read()
        without = open(os.path.join(FIX, stem + ".rpt"), encoding="utf-8").read()

        a = cp.classify(with_f, net, top)
        b = cp.classify(without, net, top)
        print(f"== {stem}")
        print(f"   report column : {a['verdict']} share={a['fanout_delay_share']} "
              f"top fanout={a['top_cells'][0]['fanout']} source={a['fanout_source']}")
        print(f"   netlist only  : {b['verdict']} share={b['fanout_delay_share']} "
              f"top fanout={b['top_cells'][0]['fanout']} source={b['fanout_source']}")

        ok = (a["verdict"] == want_v and abs(a["fanout_delay_share"] - want_share) < 1e-4
              and a["top_cells"][0]["fanout"] == want_fo)
        ok = ok and b["verdict"] == want_v and b["top_cells"][0]["fanout"] == want_fo

        # per-cell comparison on the netlist-only result
        rows, _s, _m = cp.parse_path(with_f)
        mods = cp.parse_netlist(net)
        low_dis, hi_dis = [], []
        for r in rows:
            if r["report_fanout"] is None:
                continue
            fo, _owner = cp.resolve_fanout(mods, top, r["inst"])
            if fo != r["report_fanout"]:
                (hi_dis if r["report_fanout"] >= cp.FANOUT_HI else low_dis).append(
                    (r["inst"].split("/")[-1], r["cell"], r["incr"], r["report_fanout"], fo))
        print(f"   cells checked {sum(1 for r in rows if r['report_fanout'] is not None)}, "
              f"disagreements at or above fanout {cp.FANOUT_HI}: {len(hi_dis)}, "
              f"below: {len(low_dis)}")
        for d in hi_dis + low_dis:
            print(f"      {d[0]:<10} {d[1]:<28} {d[2]:>6} ns  sta={d[3]} netlist={d[4]}")
        ok = ok and not hi_dis
        print(f"   {'PASS' if ok else 'FAIL'}")
        failures += 0 if ok else 1
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{len(CASES) - failures} of {len(CASES)} fixtures pass")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
