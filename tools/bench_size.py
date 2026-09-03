#!/usr/bin/env python3
"""Print the benchmark's real size from a committed mapped netlist.

DEMO.md beat 1 used to count lines of one RTL file while the narrator said
"55,413 standard cells", which the command did not show. This prints the
numbers the narrator says, from a netlist fixture in the repository.

Counting is hierarchy-aware. A hierarchical netlist writes each module's
body once no matter how many times it is instantiated, and this benchmark
instantiates AES twice, so counting `sky130_fd_sc_hd__` occurrences in the
file text undercounts the design. That mistake is already on this project's
record (28,844 text occurrences against 55,413 instantiated cells) and this
tool does not repeat it: cells are counted per module and multiplied out
through the instance tree from the top.

    python3 tools/bench_size.py
"""
import gzip, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import classify_path as cp  # noqa: E402

FIX = os.path.join(REPO, "experiments", "classifier_regression",
                   "v3_bufsize_it3.v.gz")
FLOPS = ("__dfrtp", "__dfstp", "__dfxtp", "__edfxtp", "__dlrtp", "__sdfrtp")


def counts(mods, top, memo=None):
    """(total cells, total flops) instantiated under `top`."""
    memo = {} if memo is None else memo
    if top in memo:
        return memo[top]
    md = mods.get(top)
    if md is None:
        return (0, 0)
    memo[top] = (0, 0)          # guard against cycles
    cells = len(md["cells"])
    flops = sum(1 for t in md["cells"].values() if any(k in t for k in FLOPS))
    for _inst, mtype in md["subs"].items():
        c, f = counts(mods, mtype, memo)
        cells += c
        flops += f
    memo[top] = (cells, flops)
    return memo[top]


def main():
    tmp = tempfile.mkdtemp(prefix="bench_size_")
    net = os.path.join(tmp, "mapped.v")
    with gzip.open(FIX, "rb") as fi, open(net, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    mods = cp.parse_netlist(net)
    cells, flops = counts(mods, "bench_top")
    text_cells = sum(len(m["cells"]) for m in mods.values())

    rtl = os.path.join(REPO, "rtl")
    files = [os.path.join(r, f) for r, _d, fs in os.walk(rtl) for f in fs
             if f.endswith((".v", ".vh"))]
    rtl_lines = sum(sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
                    for p in files)
    sdc = open(os.path.join(REPO, "sdc", "bench_top_v3.sdc"), encoding="utf-8").read()
    clocks = len(re.findall(r"^\s*create_clock", sdc, re.M))
    gen = len(re.findall(r"^\s*create_generated_clock", sdc, re.M))

    print(f"{cells:>7,} standard cells instantiated under bench_top")
    print(f"{flops:>7,} flip-flops")
    print(f"{text_cells:>7,} cells written in the netlist text across "
          f"{len(mods)} modules (each module body once; AES is instantiated twice)")
    print(f"{clocks:>7} clock domains, {gen} in-RTL generated clocks, "
          f"including odd /3 and /5")
    print(f"{rtl_lines:>7,} lines of RTL across {len(files)} files")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
