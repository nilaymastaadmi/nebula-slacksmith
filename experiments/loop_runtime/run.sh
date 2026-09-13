#!/bin/bash
# Beat 2's closed loop, N = 5, wall and CPU time per run. See PROTOCOL.md.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
cd "$REPO"
OUT=experiments/loop_runtime/results
mkdir -p "$OUT"
TSV=$OUT/runs.tsv
printf "run\tstart_utc\twall_s\tuser_s\tsys_s\tload1_before\tload1_after\tnproc\tcloses\n" > "$TSV"
for i in 1 2 3 4 5; do
  W=$SLACKSMITH_WORK/loop_runtime/run$i
  rm -rf "$W"
  LB=$(cut -d' ' -f1 /proc/loadavg)
  ps -eo pcpu,etime,comm --sort=-pcpu | head -6 > "$OUT/ps_before_run$i.txt"
  S=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  /usr/bin/time -f "%e %U %S" -o "$OUT/time_run$i.txt" \
    python3 -u tools/slacksmith.py \
      --sdc sdc/bench_top_v2.sdc \
      --liberty "$LIBERTY" \
      --sta-bin "$STA_BIN" \
      --clock clk_a --clock clk_b --clock clk_e \
      --workdir "$W" --engine sta > "$OUT/run$i.log" 2>&1
  LA=$(cut -d' ' -f1 /proc/loadavg)
  read -r WALL USR SYS < <(tail -1 "$OUT/time_run$i.txt")
  if grep -q "ALL REPORTED GROUPS MEET" "$OUT/run$i.log"; then C=yes; else C=no; fi
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$i" "$S" "$WALL" "$USR" "$SYS" "$LB" "$LA" "$(nproc)" "$C" >> "$TSV"
  echo "run $i: wall $WALL s, cpu $USR+$SYS s, load $LB -> $LA, closes $C"
done
python3 - "$TSV" > "$OUT/summary.txt" <<'PY'
import csv, statistics, sys
rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8"), delimiter="\t"))
wall = [float(r["wall_s"]) for r in rows]
cpu = [float(r["user_s"]) + float(r["sys_s"]) for r in rows]
closed = sum(1 for r in rows if r["closes"] == "yes")
print("runs %d, closed %d of %d" % (len(rows), closed, len(rows)))
print("wall s: median %.1f, min %.1f, max %.1f" % (statistics.median(wall), min(wall), max(wall)))
print("cpu s (user+sys): median %.1f, min %.1f, max %.1f" % (statistics.median(cpu), min(cpu), max(cpu)))
print("load1 before: " + ", ".join(r["load1_before"] for r in rows) + "; nproc " + rows[0]["nproc"])
PY
cat "$OUT/summary.txt"
