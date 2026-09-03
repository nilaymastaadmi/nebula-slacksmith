set -u
# G6 on every repair_design pair this project reports, not just one.
# Each arm is re-run through the unchanged flow so its own prerepair.v and
# repaired.v exist in one name domain, then proved with tools/lec_check.py.
#
#   usage: bash experiments/openroad_repair/lec_all_arms.sh
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
RES=experiments/openroad_repair/lec_arms; mkdir -p $RES
OUT=$RES/summary.tsv
printf "arm\tnetlist\tsdc\tverdict\tcompare_points\tproven\tunproven\tseconds\n" > $OUT

arm () {  # $1 label  $2 netlist  $3 sdc
  echo "=============== $1"
  bash experiments/openroad_repair/run.sh "$2" "$3" > $RES/$1.or.log 2>&1
  if [ ! -s $HOME/or_repair/prerepair.v ] || [ ! -s $HOME/or_repair/repaired.v ]; then
    printf "%s\t%s\t%s\tNO_NETLIST\t\t\t\t\n" "$1" "$(basename $2)" "$(basename $3)" >> $OUT
    echo "  no netlist pair written"; return
  fi
  t0=$(date +%s)
  python3 tools/lec_check.py --gold $HOME/or_repair/prerepair.v \
      --gate $HOME/or_repair/repaired.v \
      --liberty $HOME/sta_work/sky130hd_tt.lib \
      --workdir $HOME/lec_$1 > $RES/$1.lec.json 2>&1
  t1=$(date +%s)
  python3 - "$1" "$2" "$3" $RES/$1.lec.json $((t1-t0)) >> $OUT <<'PY'
import json, os, sys
arm, net, sdc, p, secs = sys.argv[1:6]
try:
    d = json.load(open(p))
except Exception:
    d = {"verdict": "PARSE_FAIL"}
print("\t".join(str(x) for x in [arm, os.path.basename(net), os.path.basename(sdc),
      d.get("verdict"), d.get("compare_points",""), d.get("proven",""),
      d.get("unproven",""), secs]))
PY
  tail -1 $OUT
}

arm OR-C   $HOME/flatexp/C/mapped.v sdc/bench_top_v3.sdc
arm OR-E   $HOME/flatexp/E/mapped.v sdc/bench_top_v3.sdc
arm MF16-E $HOME/flatexp/E/mapped.v sdc/bench_top_v3_mf16.sdc
arm MF8-E  $HOME/flatexp/E/mapped.v sdc/bench_top_v3_mf8.sdc
arm MF32-E $HOME/flatexp/E/mapped.v sdc/bench_top_v3_mf32.sdc
arm MF16-C $HOME/flatexp/C/mapped.v sdc/bench_top_v3_mf16.sdc

echo
column -t -s $'\t' $OUT
