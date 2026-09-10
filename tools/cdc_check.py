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

Verdicts: SAFE, SYNCHRONOUS, DEPTH_n (n < 2), MULTIBIT, MULTIBIT_UNSAFE,
UNCLASSIFIED.

SYNCHRONOUS means the two clocks are one group per the SDC (a clock and what
create_generated_clock derives from it), so the crossing needs no synchronizer
and is not a CDC finding. Pass --sdc to get it; without it every distinct clock
net is its own domain, which made 8 of 16 findings on a correct design spurious.

MULTIBIT and UNCLASSIFIED are NOT passes and exit non-zero: the first means
Hamming safety has not been discharged, the second that the gate could not
reason about the crossing. Neither is ever silently called safe, on the same
principle as CANNOT in SlackBench.
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
    # flatten is not optional. `prep -top X` keeps the hierarchy, so on a
    # design of any size every flop sits inside a submodule, the top module
    # holds almost none, and a model that reads only the top sees zero flops
    # and reports a clean sheet. That happened on bench_top: 8,274 flops
    # reported as 0. Flattened RTL is still elaborated RTL and not mapped, so
    # the registered definition is unchanged.
    script = "; ".join(
        ["read_verilog %s" % " ".join(files),
         "prep -top %s" % top,
         "flatten",
         "opt_clean",
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

        # One net has many names after flatten: the port at this level plus
        # every submodule port it was tied to. Keep the one a human wrote here.
        def rank(name):
            return (0 if name in self.portdir else 1, name.count("."), len(name))

        for nname, n in mod.get("netnames", {}).items():
            if nname.startswith("$"):
                continue
            for i, b in enumerate(n["bits"]):
                if not isinstance(b, int):
                    continue
                cur = self.bitname.get(b)
                if cur is None or rank(nname) < rank(cur[0]):
                    self.bitname[b] = (nname, i)

        for cname, c in mod.get("cells", {}).items():
            conn = c["connections"]
            outs = []
            if is_seq(c["type"]):
                q = conn.get("Q", [])
                clk = conn.get("CLK", conn.get("C", []))
                arst = conn.get("ARST", conn.get("SRST", []))
                pol = c.get("parameters", {}).get(
                    "ARST_POLARITY", c.get("parameters", {}).get("SRST_POLARITY"))
                self.flops[cname] = {
                    "clk": clk[0] if clk else None,
                    "d": conn.get("D", []),
                    "q": q, "width": len(q), "type": c["type"],
                    "arst": arst[0] if arst else None,
                    # a Yosys polarity parameter is a bit string; "0" or a
                    # string of zeros means the reset is active low
                    "arst_active_high": bool(pol and set(str(pol)) != {"0"}),
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


def source_domain(dsn, bits):
    """Clock and reset of the flop that drives these bits, walking back through
    combinational logic. Returns (clock_name, reset_name, active_high) or
    (None, None, None) when it cannot be determined, which is reported rather
    than guessed."""
    flops, _, _ = dsn.sources(bits)
    if not flops:
        return None, None, None
    f = dsn.flops[sorted(flops)[0]]
    clk = dsn.clock_name(f["clk"]) if f["clk"] is not None else None
    rst = dsn.base_name(f["arst"]) if f["arst"] is not None else None
    return clk, rst, f["arst_active_high"]


# --------------------------------------------------------------------------
# clock groups, read from the SDC that G0 already fingerprints
# --------------------------------------------------------------------------
CREATE_CLK = re.compile(r"^\s*create_clock\b[^\n]*?-name\s+(\S+)", re.M)
GEN_CLK = re.compile(
    r"^\s*create_generated_clock\b(.*?)(?=^\s*create_|\Z)", re.M | re.S)
GEN_NAME = re.compile(r"-name\s+(\S+)")
GEN_SRC = re.compile(r"-source\s+\[\s*get_(?:ports|nets|pins)\s+([^\]\s]+)")


def sdc_clock_groups(path):
    """Map every clock to the root of its synchronous group.

    A clock and everything generated from it are SYNCHRONOUS: a crossing
    between them needs no synchronizer, and flagging it is the noise that made
    six of G7's sixteen findings on a correct design meaningless. The SDC is
    the authority for this and already declares it, so nothing new is asked of
    the user.

    Returns ({clock: group_root}, note) where note explains an empty result.
    """
    if not path or not os.path.exists(path):
        return {}, "no SDC given, so every distinct clock net is its own group"
    text = open(path, encoding="utf-8", errors="replace").read()
    # join backslash continuations: the generated-clock statements wrap
    text = re.sub(r"\\\s*\n\s*", " ", text)

    parent = {}
    for m in CREATE_CLK.finditer(text):
        parent.setdefault(m.group(1), None)
    for blk in GEN_CLK.finditer(text):
        body = blk.group(1)
        nm, src = GEN_NAME.search(body), GEN_SRC.search(body)
        if nm and src:
            parent[nm.group(1)] = src.group(1)

    def root(c, guard=0):
        while parent.get(c) and guard < 16:
            c, guard = parent[c], guard + 1
        return c

    groups = {c: root(c) for c in parent}
    if not groups:
        return {}, "SDC declared no clocks this parser recognised"
    derived = sum(1 for c, r in groups.items() if c != r)
    return groups, "%d clocks in %d synchronous group(s), %d derived" % (
        len(groups), len(set(groups.values())), derived)


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


def instrument(src_files, module, signal, width, clk, rst, outdir,
               active_high=False):
    """Write a copy of the sources with the Hamming property injected into
    `module`, before its endmodule. Returns the new file list, or None if the
    module could not be located."""
    os.makedirs(outdir, exist_ok=True)
    # Reset is driven by the boot counter rather than left free: a free
    # reset can assert mid-trace and slam the source register to zero from
    # an arbitrary value, which is a real counterexample to the wrong
    # question.
    # Reset is driven by the boot counter rather than left free: a free reset
    # can assert mid-trace and slam the source register to zero from an
    # arbitrary value, which is a real counterexample to the wrong question.
    # Polarity comes from the design, not from a convention about the name.
    if rst:
        rel = "(cdc_boot_r >= 4'd2)" if active_high is False else "(cdc_boot_r < 4'd2)"
        assume_rst = "  always @(*) assume (%s == %s);\n" % (rst, rel)
    else:
        assume_rst = ""
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


def hamming_check(files, module, signal, width, clk, rst, workdir, depth,
                  timeout, active_high=False):
    """Prove that `signal` inside `module` changes at most one bit per cycle."""
    wd = os.path.join(workdir, "ham_" + re.sub(r"\W+", "_", signal))
    os.makedirs(wd, exist_ok=True)
    # A dotted name is a flattened alias, not something that can be written
    # inside the module source. Emitting it produces an implicitly declared
    # wire and a property that quietly means nothing.
    for label, val in (("clock", clk), ("reset", rst)):
        if val and "." in val:
            return "ERROR", ("derived %s %r is a flattened alias, not an "
                             "identifier in %s" % (label, val, module))
    srcdir = os.path.join(wd, "src_instrumented")
    inst = instrument(files, module, signal, width, clk, rst, srcdir,
                      active_high)
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
    ap.add_argument("--sdc", default=None,
                    help="SDC to read clock groups from. A clock and anything "
                         "create_generated_clock derives from it are "
                         "SYNCHRONOUS, so a crossing between them is not a CDC "
                         "crossing. Without this every distinct clock net is "
                         "treated as its own domain, which is what made 6 of "
                         "16 findings on a correct design noise.")
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
    ap.add_argument("--rst", default=None,
                    help="override the reset derived from the design; "
                         "normally leave unset")
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

    print("top %s: %d register cells (%d bits), %d clock domain(s)" % (a.top, len(dsn.flops),
         sum(f["width"] for f in dsn.flops.values()), len(domains)))
    # A checker that found nothing to look at must never report a clean sheet.
    # Reporting "crossings: 0" for a design whose flops the model failed to
    # find is indistinguishable from reporting a correct design, and is how
    # this gate first "passed" bench_top.
    if not dsn.flops:
        sys.stderr.write(
            "REFUSING TO REPORT: no flops found in %s. The gate cannot say "
            "anything about a design it cannot see.\n" % a.top)
        sys.exit(3)
    for clk, fl in sorted(domains.items(), key=lambda kv: -len(kv[1])):
        print("   %-24s %d cells, %d bits" % (dsn.clock_name(clk), len(fl),
          sum(dsn.flops[x]["width"] for x in fl)))
    if a.async_input:
        print("   declared async inputs: %s" % ", ".join(a.async_input))

    groups, gnote = sdc_clock_groups(a.sdc)
    print("clock groups: %s" % gnote)
    if groups:
        by_root = {}
        for c, r in sorted(groups.items()):
            by_root.setdefault(r, []).append(c)
        for r, members in sorted(by_root.items()):
            others = [m for m in members if m != r]
            print("   %-12s synchronous with: %s" %
                  (r, ", ".join(others) if others else "(nothing)"))
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

    def same_group(x, y):
        """True when two clocks are synchronously related per the SDC."""
        if not groups:
            return False
        gx, gy = groups.get(x), groups.get(y)
        return gx is not None and gx == gy

    results = []
    for k, c in merged.items():
        if same_group(c["src_clock"], c["dest_clock"]):
            # Not a CDC crossing at all. A clock and its own divided version
            # share a source; the launch and capture edges are related, so no
            # synchronizer is required and none should be demanded.
            c["verdict"] = "SYNCHRONOUS"
            c["why"] = "%s and %s are one clock group per the SDC" % (
                c["src_clock"], c["dest_clock"])
            results.append(c)
            continue
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
                # Per crossing, from the design. A single global --ham-clock
                # checked async_fifo's rgray_r against wclk and returned a
                # confident REFUTED on a correct design.
                sclk, srst, ahigh = source_domain(dsn, declared.get(sig, set()))
                sclk = a.ham_clock or sclk or c["dest_clock"]
                srst = a.rst if a.rst else srst
                verdict, detail = hamming_check(
                    a.files, a.ham_module or a.top, sig, c["width"],
                    sclk, srst, wd, a.ham_depth, a.ham_timeout, ahigh)
                print("   %-18s clock=%-10s reset=%s" % (sig, sclk, srst))
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

    if groups:
        syn = n.get("SYNCHRONOUS", 0)
        if syn:
            print("%d crossing(s) are synchronous and are NOT CDC findings. "
                  "Without --sdc they would have been reported as violations."
                  % syn)

    violations = sum(v for k, v in n.items()
                     if k.startswith("DEPTH") or k.endswith("UNSAFE"))
    # MULTIBIT is not a pass. It means the crossing is multi-bit and its
    # Hamming safety has NOT been discharged, which happens whenever the run
    # omits --hamming. Exiting 0 on it would be the same confident-clean
    # verdict this gate has produced three times already from other causes.
    unchecked = n.get("MULTIBIT", 0) + n.get("UNCLASSIFIED", 0)
    if unchecked:
        print("%d crossing(s) are NOT CHECKED, not clean: %d multi-bit "
              "awaiting Hamming safety%s, %d unclassifiable. Re-run with "
              "--hamming to discharge them."
              % (unchecked, n.get("MULTIBIT", 0),
                 " (--hamming was not given)" if not a.hamming else "",
                 n.get("UNCLASSIFIED", 0)))
    bad = violations + unchecked
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
