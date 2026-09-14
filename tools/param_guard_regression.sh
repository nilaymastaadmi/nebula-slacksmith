set -u
# Gate defect 3's guard: a module the design instantiates with a parameter
# override must come back CANNOT, and a module without parameters must not be
# touched by the guard. Kept out of verdict_regression.sh so the demo's beat 6
# screen, which replays that script, is unchanged.
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
cd "$REPO"

echo "--- tv80_mcode, tv80 run 1 O1 (expect CANNOT: parameter override) ---"
python3 tools/gate_proposal.py \
  --proposal experiments/depth_tv80/results/run1/online_variants/O1.json \
  --rtl experiments/depth_tv80/rtl/tv80.v --module tv80_mcode \
  --depth 20 --timeout 420 \
  --workdir "$SLACKSMITH_WORK/param_guard/tv80" --repo . 2>&1 \
  | grep -E '"id"|"G3"|"G4"'

echo "--- guard alone on the benchmark's gated modules (expect None for both) ---"
python3 - <<'PY'
import sys
sys.path.insert(0, "tools")
from gate_proposal import param_override
for rtl, mod in (("rtl/rv32i_core.v", "rv32i_core"), ("rtl/aes/aes_key_mem.v", "aes_key_mem")):
    print("%s: %s" % (mod, param_override(rtl, mod)))
PY

echo "--- parameters from an included header (expect a pi_top.v hit for pi_child, None for pi_lone) ---"
python3 - <<'PY'
import sys
sys.path.insert(0, "tools")
from gate_proposal import param_override
d = "tools/fixtures/param_include/"
for mod in ("pi_child", "pi_lone"):
    print("%s: %s" % (mod, param_override(d + mod + ".v", mod)))
PY
