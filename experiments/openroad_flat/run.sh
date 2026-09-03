set -u
# repair_design on the flat netlists, per PREREGISTRATION.md.
# The flow is experiments/openroad_repair/run.sh with the netlist and SDC as
# arguments; nothing else differs. Arms OR-C (flat, no ABC buffering) and
# OR-E (flat, buffer+size).
#
#   usage: bash experiments/openroad_flat/run.sh
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
RES=experiments/openroad_flat/results; mkdir -p $RES

for arm in C E; do
  NET=$HOME/flatexp/$arm/mapped.v
  [ -s "$NET" ] || { echo "FATAL: $NET missing"; exit 2; }
  echo "=============== arm OR-$arm ($NET)"
  bash experiments/openroad_repair/run.sh "$NET" sdc/bench_top_v3.sdc
  cp $HOME/or_repair/flow.log $RES/OR_$arm.flow.log
  cp $HOME/or_repair/repaired.v $RES/OR_$arm.repaired.v 2>/dev/null
  gzip -9 -f $RES/OR_$arm.repaired.v 2>/dev/null
done

echo
echo "=== before/after per arm ==="
python3 - <<'PY'
import re, os
res = "experiments/openroad_flat/results"
rows = []
for arm in ("C", "E"):
    p = f"{res}/OR_{arm}.flow.log"
    if not os.path.exists(p):
        continue
    txt = open(p, encoding="utf-8", errors="replace").read()
    # two timing blocks: before and after repair_design
    parts = txt.split("=====> REPAIR_DESIGN")
    def slacks(seg):
        out = {}
        for c in ("clk_a", "clk_b", "clk_e"):
            m = re.split(rf"---CLOCK:{c}---", seg)
            if len(m) < 2:
                continue
            s = re.findall(r"([\-0-9.]+)\s+slack \((?:MET|VIOLATED)\)", m[1][:4000])
            if s:
                out[c] = float(s[0])
        return out
    before, after = slacks(parts[0]), slacks(parts[1]) if len(parts) > 1 else {}
    areas = re.findall(r"Design area (\d+) u\^2", txt)
    rows.append((arm, before, after, areas))
    print(f"OR-{arm}")
    for c in ("clk_a", "clk_b", "clk_e"):
        b, a = before.get(c), after.get(c)
        d = round(a - b, 3) if (a is not None and b is not None) else None
        print(f"   {c}: before {b}  after {a}  delta {d}")
    if len(areas) >= 2:
        ab, aa = int(areas[0]), int(areas[1])
        print(f"   area: {ab} -> {aa} u^2 ({100.0*(aa-ab)/ab:+.1f}%)")
PY
