#!/usr/bin/env python3
"""
cdc_check.py -- G7, the clock-domain-crossing gate.

Registered in experiments/cdc_gate/PREREGISTRATION.md BEFORE this file existed.

G0 to G6 all answer questions about function. A CDC defect is not a function
defect, which is exactly why both SlackBench CDC cases defeat every checker in
REPORT section 7.4: the pair really is functionally equivalent, and the bug is
still there. This gate answers two questions equivalence checking cannot state.

  1. SYNCHRONIZER DEPTH, structural. How many back-to-back flops in the
     destination domain sit between the crossing and its first use? Fewer than
     two is a missing metastability guard.

  2. HAMMING SAFETY, temporal. For a multi-bit crossing, does the SOURCE
     register change at most one bit per cycle? This is the property gray
     coding exists to provide, and checking the property rather than the
     encoding means a design that achieves it another way passes, while one
     that gray-codes on the wrong side of the boundary fails. Discharged with
     SymbiYosys, because it is a statement about consecutive states and
     therefore something formal can answer and equivalence cannot.

Operates on Yosys-elaborated RTL, not the mapped netlist: clock domains and
register boundaries are unambiguous before technology mapping and are not
after it.

    python3 tools/cdc_check.py --top bench_top rtl/*.v rtl/aes/*.v
    python3 tools/cdc_check.py --top sb_cdc --async-input flag_src \
        experiments/slackbench/cases/CDC-1/gate.v

Verdicts: SAFE, DEPTH_n (n < 2), MULTIBIT_UNSAFE, UNCLASSIFIED.
UNCLASSIFIED is first-class and is reported apart from a violation, on the
same principle as CANNOT in SlackBench: a crossing the gate cannot reason
about must never be silently called safe.
"""
import argparse, json, os, re, subprocess, sys, tempfile

OSS = os.environ.get("OSS_CAD_BIN", os.path.expanduser("~/tools/oss-cad-suite/bin"))
YOSYS = os.path.join(OSS, "yosys")
SBY = os.path.join(OSS, "sby")

# Any cell type carrying a state element. Everything else is combinational for
# the purposes of walking backward from a flop's D pin.
SEQ = re.compile(r"\$(_)?(a|s|ald|sr)?dffe?(_[NPS01]+)?$|\$_?dlatch|\$mem|\$adlatch|\$dffsr")


def is_seq(t):
    return bool(SEQ.search(t)) or "dff" in t.lower() or "latch" in t.lower()


# --------------------------------------------------------------------------
# elaborate
# --------------------------------------------------------------------------
def elaborate(files, top, workdir):
    out = os.path.join(workdir, "design.json")
    script = "; ".join(
        ["read_verilog %s" % " ".join(files),
         "prep -top %s" % top,
         "write_json %s" % out])
    r = subprocess.run([YOSYS, "-p", script], capture_output=True, text=True)
    log = os.path.join(workdir, "yosys.log")
    open(log, "w", encoding="utf-8").write(r.stdout + r.stderr)
    if r.returncode != 0 or not os.path.exists(out):
        sys.stderr.write("yosys failed, see %s\n" % log)
        sys.stderr.write((r.stdout + r.stderr)[-2500:] + "\n")
        sys.exit(2)
    return json.load(open(out, encoding="utf-8"))


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------
class Design:
    def __init__(self, mod):
        self.mod = mod
        self.driver = {}        # bit -> (cell name, cell dict, output port)
        self.flops = {}         # cell name -> dict(clk, d, q, width, type)
        self.bitname = {}       # bit -> a readable net name
        self.portdir = {}       # port name -> direction

        for pname, p in mod.get("ports", {}).items():
            self.portdir[pname] = p["direction"]

        for nname, n in mod.get("netnames", {}).items():
            if nname.startswith("$"):
                continue
            for i, b in enumerate(n["bits"]):
                if isinstance(b, int):
                    self.bitname.setdefault(b, (nname, i))

        for cname, c in mod.get("cells", {}).items():
            conn = c["connections"]
            outs = []
            if is_seq(c["type"]):
                q = conn.get("Q", [])
                clk = conn.get("CLK", conn.get("C", []))
                self.flops[cname] = {
                    "clk": clk[0] if clk else None,
                    "d": conn.get("D", []),
                    "q": q, "width": len(q), "type": c["type"],
                }
                outs = [("Q", q)]
            else:
                # a cell's outputs are the connections we cannot otherwise
                # attribute; port_directions is present in Yosys JSON
                pd = c.get("port_directions", {})
                for port, bits in conn.items():
                    if pd.get(port) == "output":
                        outs.append((port, bits))
                if not outs and "Y" in conn:
                    outs = [("Y", conn["Y"])]
            for port, bits in outs:
                for b in bits:
                    if isinstance(b, int):
                        self.driver[b] = (cname, c, port)

    def net_bits(self, name):
        n = self.mod.get("netnames", {}).get(name)
        if n is None:
            n = self.mod.get("netnames", {}).get("\\" + name)
        return [b for b in n["bits"] if isinstance(b, int)] if n else []

    def name_of(self, bit):
        n = self.bitname.get(bit)
        return "%s[%d]" % n if n and n[1] is not None else (n[0] if n else "bit%s" % bit)

    def base_name(self, bit):
        n = self.bitname.get(bit)
        return n[0] if n else "bit%s" % bit

    def clock_name(self, bit):
        if bit is None:
            return "(none)"
        return self.base_name(bit)

    # walk backward from a set of bits through combinational logic only,
    # collecting the flops and primary inputs that feed them
    def sources(self, bits, limit=4000):
        seen, stack, flops, inputs = set(), list(bits), set(), set()
        steps = 0
        while stack and steps < limit:
            steps += 1
            b = stack.pop()
            if not isinstance(b, int) or b in seen:
                continue
            seen.add(b)
            drv = self.driver.get(b)
            if drv is None:
                nm = self.bitname.get(b)
                if nm and self.portdir.get(nm[0]) == "input":
                    inputs.add(nm[0])
                continue
            cname, c, _ = drv
            if cname in self.flops:
                flops.add(cname)
                continue
            for port, cbits in c["connections"].items():
                pd = c.get("port_directions", {})
                if pd and pd.get(port) == "output":
                    continue
                stack.extend([x for x in cbits if isinstance(x, int)])
        return flops, inputs, (steps >= limit)


# --------------------------------------------------------------------------
# synchronizer depth
# --------------------------------------------------------------------------
def sync_depth(dsn, first_flop, domain_clk):
    """Count back-to-back flops in the destination domain starting at
    first_flop, requiring each stage's D to be exactly the previous stage's Q
    with no combinational logic in between."""
    depth, cur, guard = 1, first_flop, 0
    while guard < 16:
        guard += 1
        q = dsn.flops[cur]["q"]
        nxt = None
        for cname, f in dsn.flops.items():
            if cname == cur or f["clk"] != domain_clk:
                continue
            if list(f["d"]) == list(q):          # direct Q -> D, no logic
                nxt = cname
                break
        if nxt is None:
            return depth
        depth += 1
        cur = nxt
    return depth


# --------------------------------------------------------------------------
# Hamming safety, discharged formally
# --------------------------------------------------------------------------
HAM_SBY = """[options]
mode bmc
depth {depth}

[engines]
smtbmc boolector

[script]
read -formal {srcs}
prep -top {top}
chformal -assert -early

[files]
{files}
"""

# The property, injected into the module that owns the crossing net.
#
# Wrapping the design and reaching in as dut.<net> does not work: Yosys treats
# the hierarchical reference as an implicitly declared wire and a `.*` port
# connection needs every port redeclared in the wrapper. Instrumenting the
# source is what commercial CDC tools do anyway, and the instrumented file is
# written into the work directory so the property that was actually checked can
# be read rather than taken on trust.
HAM_PROP = """
  // ---- injected by tools/cdc_check.py: G7 Hamming safety ------------------
  // The property gray coding exists to provide: the value that physically
  // crosses the domain boundary changes at most one bit per cycle. Checking
  // the PROPERTY, not the encoding, so a design that achieves it another way
  // passes and one that encodes on the wrong side of the boundary fails.
  //
  // The boot counter is not decoration. A proof engine starts from an
  // ARBITRARY state, so without it cdc_prev_r begins as garbage and the first
  // comparison refutes every design including correct ones. It holds reset
  // asserted for two cycles, releases it for the rest of the trace, and arms
  // the assertion only once the design has settled.
  reg [{hi}:0] cdc_prev_r;
  reg [3:0]    cdc_boot_r;
  initial      cdc_boot_r = 4'd0;
  always @(posedge {clk}) begin
    if (cdc_boot_r != 4'd15) cdc_boot_r <= cdc_boot_r + 4'd1;
    cdc_prev_r <= {sig};
  end
{assume_rst}
  wire [{hi}:0] cdc_diff = {sig} ^ cdc_prev_r;
  // x & (x-1) == 0 is true exactly when at most one bit of x is set
  always @(posedge {clk})
    if (cdc_boot_r >= 4'd4)
      assert ((cdc_diff & (cdc_diff - 1)) == 0);
  // -------------------------------------------------------------------------
"""


def instrument(src_files, module, signal, width, clk, rst, outdir):
    """Write a copy of the sources with the Hamming property injected into
    `module`, before its endmodule. Returns the new file list, or None if the
    module could not be located."""
    os.makedirs(outdir, exist_ok=True)
    # Reset is driven by the boot counter rather than left free: a free
    # reset can assert mid-trace and slam the source register to zero from
    # an arbitrary value, which is a real counterexample to the wrong
    # question.
    assume_rst = ("  always @(*) assume (%s == (cdc_boot_r >= 4'd2));\n" % rst
                  if rst else "")
    prop = HAM_PROP.format(hi=width - 1, sig=signal, clk=clk,
                           assume_rst=assume_rst)
    out, done = [], False
    for f in src_files:
        text = open(f, encoding="utf-8", errors="replace").read()
        m = re.search(r"^\s*module\s+%s\b" % re.escape(module), text, re.M)
        dst = os.path.join(outdir, os.path.basename(f))
        if m and not done:
            e = re.compile(r"^\s*endmodule", re.M).search(text, m.end())
            if e:
                text = text[:e.start()] + prop + text[e.start():]
                done = True
        open(dst, "w", encoding="utf-8", newline="\n").write(text)
        out.append(dst)
    return out if done else None


def hamming_check(files, module, signal, width, clk, rst, workdir, depth, timeout):
    """Prove that `signal` inside `module` changes at most one bit per cycle."""
    wd = os.path.join(workdir, "ham_" + re.sub(r"\W+", "_", signal))
    os.makedirs(wd, exist_ok=True)
    srcdir = os.path.join(wd, "src_instrumented")
    inst = instrument(files, module, signal, width, clk, rst, srcdir)
    if inst is None:
        return "ERROR", "could not find module %s to instrument" % module

    sby = HAM_SBY.format(depth=depth, top=module,
                         srcs=" ".join(os.path.basename(f) for f in inst),
                         files="\n".join(os.path.abspath(f) for f in inst))
    sf = os.path.join(wd, "ham.sby")
    open(sf, "w", encoding="utf-8", newline="\n").write(sby)

    try:
        r = subprocess.run([SBY, "-f", sf], cwd=wd, capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "no verdict in %ds" % timeout
    out = r.stdout + r.stderr
    open(os.path.join(wd, "sby.log"), "w", encoding="utf-8").write(out)
    if "DONE (PASS" in out:
        return "PROVEN", "no counterexample to depth %d" % depth
    if "DONE (FAIL" in out:
        step = ""
        m = re.search(r"Assert failed in \S+: (\S+)", out)
        t = re.search(r"trace step (\d+)", out) or re.search(r"step (\d+)", out)
        if t:
            step = ", first at step %s" % t.group(1)
        return "REFUTED", "counterexample%s, trace in %s/ham/engine_0/" % (step, wd)
    last = [l for l in out.strip().splitlines() if l.strip()]
    return "ERROR", last[-1] if last else "no output"


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--top", required=True)
    ap.add_argument("--async-input", action="append", default=[],
                    help="primary input to treat as an asynchronous source "
                         "(see PREREGISTRATION amendment 1)")
    ap.add_argument("--crossing", action="append", default=[],
                    help="any net, port or internal, driven by another clock "
                         "domain (see PREREGISTRATION amendment 2)")
    ap.add_argument("--workdir", default="~/cdc_gate")
    ap.add_argument("--hamming", action="store_true",
                    help="also discharge Hamming safety on multi-bit crossings")
    ap.add_argument("--ham-depth", type=int, default=12)
    ap.add_argument("--ham-module", default=None,
                    help="module that owns the crossing net (default: --top)")
    ap.add_argument("--ham-clock", default=None,
                    help="clock the crossing net is generated in "
                         "(default: the destination clock)")
    ap.add_argument("--ham-timeout", type=int, default=300)
    ap.add_argument("--rst", default="rst_n")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    wd = os.path.expanduser(a.workdir)
    os.makedirs(wd, exist_ok=True)
    d = elaborate(a.files, a.top, wd)
    mods = d["modules"]
    key = a.top if a.top in mods else ("\\" + a.top if "\\" + a.top in mods else None)
    if key is None:
        key = [k for k in mods if k.lstrip("\\") == a.top][0]
    dsn = Design(mods[key])

    domains = {}
    for cname, f in dsn.flops.items():
        domains.setdefault(f["clk"], []).append(cname)

    print("top %s: %d flops, %d clock domain(s)" % (a.top, len(dsn.flops), len(domains)))
    for clk, fl in sorted(domains.items(), key=lambda kv: -len(kv[1])):
        print("   %-24s %d flops" % (dsn.clock_name(clk), len(fl)))
    if a.async_input:
        print("   declared async inputs: %s" % ", ".join(a.async_input))
    print()

    # Amendment 2: an explicitly declared crossing net. Flops sampling it are
    # the first synchronizer stage. Needed because a single-clock case module
    # cannot express a crossing any other way, and declaring the wrong net is
    # how run 1 answered the wrong question correctly.
    declared = {}
    for netname in a.crossing:
        bits = dsn.net_bits(netname)
        if not bits:
            sys.stderr.write("no net named %s in %s\n" % (netname, a.top))
            sys.exit(2)
        declared[netname] = set(bits)

    crossings = []
    for cname, f in dsn.flops.items():
        dbits = set(b for b in f["d"] if isinstance(b, int))
        hit = [n for n, bits in declared.items() if dbits & bits]
        if hit:
            depth = sync_depth(dsn, cname, f["clk"])
            crossings.append({
                "dest_flop": cname, "dest_clock": dsn.clock_name(f["clk"]),
                "src_clock": "(declared crossing)", "sources": sorted(hit),
                "width": len(declared[hit[0]]), "depth": depth,
                "truncated": False,
            })
            continue
        dclk = f["clk"]
        srcs, inputs, truncated = dsn.sources(f["d"])
        foreign = [s for s in srcs if dsn.flops[s]["clk"] != dclk]
        async_in = [i for i in inputs if i in a.async_input]
        if not foreign and not async_in:
            continue
        depth = sync_depth(dsn, cname, dclk)
        src_desc = ([dsn.base_name(dsn.flops[s]["q"][0]) for s in foreign] or async_in)
        crossings.append({
            "dest_flop": cname,
            "dest_clock": dsn.clock_name(dclk),
            "src_clock": (dsn.clock_name(dsn.flops[foreign[0]]["clk"]) if foreign
                          else "(async input)"),
            "sources": sorted(set(src_desc)),
            "width": f["width"],
            "depth": depth,
            "truncated": truncated,
        })

    # collapse per-bit flops of one vector into one crossing record
    merged = {}
    for c in crossings:
        k = (tuple(c["sources"]), c["src_clock"], c["dest_clock"], c["depth"])
        m = merged.setdefault(k, dict(c, width=0, dest_flops=[]))
        m["width"] += max(1, c["width"])
        m["dest_flops"].append(c["dest_flop"])
        m["truncated"] = m["truncated"] or c["truncated"]

    results = []
    for k, c in merged.items():
        if c["truncated"]:
            v, why = "UNCLASSIFIED", "backward walk hit the traversal bound"
        elif c["depth"] < 2:
            v, why = "DEPTH_%d" % c["depth"], "fewer than two synchronizing flops"
        elif c["width"] > 1:
            v, why = "MULTIBIT", "needs Hamming safety on the source register"
        else:
            v, why = "SAFE", "single bit through %d flops" % c["depth"]
        c["verdict"], c["why"] = v, why
        results.append(c)

    results.sort(key=lambda c: (c["verdict"].startswith("SAFE"), c["dest_clock"]))

    print("%-14s %-11s %-11s %5s %5s  %s" %
          ("VERDICT", "SRC", "DST", "WIDTH", "DEPTH", "SOURCE"))
    for c in results:
        print("%-14s %-11s %-11s %5d %5d  %s" %
              (c["verdict"], c["src_clock"][:11], c["dest_clock"][:11],
               c["width"], c["depth"], ", ".join(c["sources"])[:44]))

    if a.hamming:
        print()
        for c in results:
            if c["verdict"] != "MULTIBIT":
                continue
            for sig in c["sources"]:
                verdict, detail = hamming_check(
                    a.files, a.ham_module or a.top, sig, c["width"],
                    a.ham_clock or c["dest_clock"], a.rst,
                    wd, a.ham_depth, a.ham_timeout)
                c["hamming"] = verdict
                c["hamming_detail"] = detail
                c["verdict"] = ("SAFE" if verdict == "PROVEN"
                                else "MULTIBIT_UNSAFE" if verdict == "REFUTED"
                                else "UNCLASSIFIED")
                print("hamming %-22s %-10s %s" % (sig, verdict, detail))

    n = {}
    for c in results:
        n[c["verdict"]] = n.get(c["verdict"], 0) + 1
    print()
    print("crossings: %d   %s" % (len(results),
          "   ".join("%s=%d" % kv for kv in sorted(n.items()))))

    if a.json:
        json.dump({"top": a.top, "crossings": results},
                  open(a.json, "w", encoding="utf-8"), indent=1)
        print("wrote", a.json)

    bad = sum(v for k, v in n.items() if k.startswith("DEPTH") or k.endswith("UNSAFE"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
