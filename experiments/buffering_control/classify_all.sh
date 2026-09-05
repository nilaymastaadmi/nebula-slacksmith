set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=$HOME/bufexp
C=$HOME/classify

echo "=================== CLASSIFIER, hierarchy-aware fanout ==================="
echo "--- 1. AES key-memory path, clk_b, UNBUFFERED netlist ---"
python3 tools/classify_path.py --report $C/aes_clkb.rpt --netlist $W/A.v
echo
echo "--- 2. same group after the buffering pass, original SDC ---"
python3 tools/classify_path.py --report $C/aes_clkb_buf.rpt --netlist $W/B.v
echo
echo "--- 3. core-level rv32i_core ALU path (batch 1's target) ---"
python3 tools/classify_path.py --report $C/core.rpt --netlist $C/core.v --top rv32i_core
echo
echo "--- 4. BUFFERED netlist, periods/6, clk_b ---"
python3 tools/classify_path.py --report $C/tight_clk_b.rpt --netlist $W/B.v
echo
echo "--- 5. BUFFERED netlist, periods/6, clk_a ---"
python3 tools/classify_path.py --report $C/tight_clk_a.rpt --netlist $W/B.v

echo
echo "=================== H2: max fanout inside aes_key_mem ==================="
python3 - <<'PY'
import os, sys
sys.path.insert(0, "tools")
from classify_path import parse_netlist

def stats(path, label):
    if not os.path.exists(path):
        print(f"{label:30} MISSING"); return None
    mods = parse_netlist(path)
    km = next((mods[n] for n in mods if "aes_key_mem" in n), None)
    if km is None:
        print(f"{label:30} aes_key_mem module not present"); return None
    vals = sorted(km["loads"].values(), reverse=True)
    if not vals:
        print(f"{label:30} no loads"); return None
    over = sum(1 for v in vals if v >= 32)
    print(f"{label:30} max={vals[0]:>5}  2nd={vals[1]:>5}  nets>=32={over:>4}  "
          f"cells={len(km['cells'])}")
    return vals[0]

h = os.path.expanduser("~")
base = stats(f"{h}/g5_aes/baseline/baseline_mapped.v", "baseline (gold key_mem)")
for p in ["A1", "A4", "A5"]:
    v = stats(f"{h}/g5_aes/{p}/variant/variant_mapped.v", f"{p} variant")
    if base and v:
        print(f"{'':30} -> max fanout {(v-base)/base*100:+.1f}% vs baseline")
PY
