#!/usr/bin/env python3
"""R86: the derived port list must equal the one hand-written entry we trust.

`tools/slacksmith.py` has carried exactly one per-module gate wiring entry,
for `aes_key_mem`, written by hand and exercised by every aes_key_mem gate in
this repository. `tools/gate_proposal.derive_ports` now reads ports from the
elaborator instead. Before it is trusted on a module nobody wrote a table for,
it has to reproduce the table for the module somebody did.

    python3 experiments/invariant_obligation/check_ports.py
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, "tools"))
import gate_proposal  # noqa: E402

YOSYS = os.environ.get("OSS_CAD_BIN", os.path.expanduser("~/tools/oss-cad-suite/bin")) + "/yosys"

# The trusted entry, copied from tools/slacksmith.py's gate wiring table.
TABLE = {
    "inputs": "key:256,keylen:1,init:1,round:4,new_sboxw:32",
    "outputs": "round_key:128,ready:1,sboxw:32",
    "clk": "clk",
    "rst": "reset_n",
}


def spec(pairs):
    return ",".join("%s:%d" % p for p in pairs)


def main():
    got = gate_proposal.derive_ports(YOSYS, os.path.join(HERE, "rtl/aes/aes_key_mem.v"), "aes_key_mem")
    if got is None:
        print("R86 MISSED: derive_ports returned nothing for aes_key_mem")
        return 1
    ins, outs, clk, rst = got
    rows = [
        ("inputs", TABLE["inputs"], spec(ins)),
        ("outputs", TABLE["outputs"], spec(outs)),
        ("clock", TABLE["clk"], str(clk)),
        ("reset", TABLE["rst"], str(rst)),
    ]
    ok = True
    for name, want, have in rows:
        same = want == have
        ok &= same
        print("%-8s %s\n         table:   %s\n         derived: %s" % (name, "MATCH" if same else "DIFFERS", want, have))
    print()
    print("R86 %s" % ("CONFIRMED: derived ports equal the trusted table exactly" if ok else "MISSED: stop, the derivation is wrong"))

    got = gate_proposal.derive_ports(YOSYS, os.path.join(HERE, "experiments/depth_tv80/rtl/tv80.v"), "tv80_mcode")
    if got is not None:
        ins, outs, clk, rst = got
        print("\ntv80_mcode, for the record: %d inputs, %d outputs, clock=%s, reset=%s" % (len(ins), len(outs), clk, rst))
        print("  inputs: %s" % spec(ins))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
