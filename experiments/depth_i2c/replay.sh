#!/bin/bash
# Amendment 1 replay: every phase-1 proposal through the REPAIRED loop as a
# frozen proposal, identical design, SDC and flags, no --force-lever. The
# replay verdict is the verdict. Not a fourth sample.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/depth_i2c; R=$D/results
for run in $R/run*/; do
  run=${run%/}; n=$(basename $run)
  [ -f $run/online_variants/O1.json ] || { echo "$n: no proposal"; continue; }
  RP=$run/replay; mkdir -p $RP
  python3 - "$run" "$RP" "$D" <<'PY'
import json, os, sys
sys.path.insert(0, "tools")
import proposer
run, rp, d = sys.argv[1:4]
p = json.load(open(os.path.join(run, "online_variants", "O1.json"), encoding="utf-8"))
full = open(os.path.join(d, "rtl", "i2c.v"), encoding="utf-8").read()
spliced = proposer.splice_module(full, p["target_module"], p["variant_source"])
text = spliced if spliced is not None else p["variant_source"]
vf = os.path.join(rp, "O1_i2c.v")
open(vf, "w", encoding="utf-8", newline="\n").write(text)
q = {k: v for k, v in p.items() if not k.startswith("_") and k != "variant_source"}
q["variant_file"] = vf.replace(os.sep, "/")
q["target_file"] = os.path.join(d, "rtl", "i2c.v").replace(os.sep, "/")
q["replay_of"] = os.path.basename(run)
json.dump(q, open(os.path.join(rp, "O1.json"), "w", encoding="utf-8"), indent=1)
print(f"{run}: spliced={spliced is not None} -> {vf}")
PY
  W=$SLACKSMITH_WORK/depth_i2c/replay_$n; rm -rf "$W"; mkdir -p "$W"
  echo "################ replay $n, $(date -u +%H:%M:%S) UTC ################"
  python3 -u tools/slacksmith.py \
    --rtl-dir $D/rtl --rtl-files $D/rtl_files.txt --top i2c_master_top \
    --sdc $D/i2c.sdc --liberty "$LIBERTY" --sta-bin "$STA_BIN" \
    --clock wb_clk_i --engine sta \
    --proposer frozen --proposals $RP \
    --max-iters 2 --g5 total \
    --workdir "$W" 2>&1 | tee $RP/replay.log
  echo "exit: ${PIPESTATUS[0]}" | tee -a $RP/replay.log
  cp "$W"/decisions.jsonl $RP/ 2>/dev/null
  if [ -d "$W/gates" ]; then
    (cd "$W/gates" && find . -type f \( -name '*.json' -o -name 'g4.log' -o -name '*.raw.log' -o -name '*.synth.log' -o -name 'miter_prop.sv' -o -name '*.eqy' \) \
      | while read -r f; do mkdir -p "$REPO/$RP/gates/$(dirname "$f")"; cp "$f" "$REPO/$RP/gates/$f"; done)
  fi
done
echo; echo "=== replay verdicts ==="
grep -h '"step": "gate"\|"step": "confirm"\|"step": "revert"\|"step": "apply"\|"step": "skip"' $R/run*/replay/decisions.jsonl 2>/dev/null | cut -c1-260
