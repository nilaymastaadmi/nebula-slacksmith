set -u
# Phase 1 of experiments/drrtl_transfer/PREREGISTRATION.md. Runs every design
# identically and writes results/summary.tsv. No design is skipped and no
# threshold is tuned; both are void conditions in the registration.
#
#   usage: bash experiments/drrtl_transfer/run_classify.sh [DRRTL_REPO_DIR]
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
Y=$HOME/tools/oss-cad-suite/bin/yosys
STA=$HOME/tools/OpenSTA/build/sta
LIB=$HOME/sta_work/sky130hd_tt.lib
DR=${1:-/mnt/c/Users/toshn/Projects/Dr_RTL}
RES=experiments/drrtl_transfer/results
W=$HOME/drrtl_run; mkdir -p $W $RES

# The lpflow/probe exclusion, asserted non-empty. A silently empty list
# reintroduced a 12.8 ns artifact into eight commits of this project once.
DU=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure; print(remeasure.dont_use_flags('$LIB'))")
NDU=$(echo $DU | wc -w)
[ "$NDU" -ge 2 ] || { echo "FATAL: dont_use returned $NDU flags"; exit 3; }
# The physical lever, byte-identical to experiments/buffering_control/.
BUF='+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put;buffer,-N,16;upsize;dnsize'
echo "dont_use flags: $NDU"

python3 - "$DR" <<'PY' > $W/designs.tsv
import json, sys
d = json.load(open(f"{sys.argv[1]}/syn_flow/design_all.json"))
for name, (top, clk, rst, ext) in d.items():
    print(f"{name}\t{top}\t{clk}\t{rst}\t{ext}")
PY

synth () {  # $1 name $2 src $3 ext $4 top $5 out $6 abc-script-or-empty
  local rv="read_verilog"; [ "$3" = "sv" ] && rv="read_verilog -sv"
  local abc="abc -liberty $LIB $DU"; [ -n "$6" ] && abc="$abc -script $6"
  $Y -p "$rv $2; hierarchy -check -top $4; synth -top $4; dfflibmap -liberty $LIB; $abc; opt_clean -purge; write_verilog -noattr $5; stat" \
     > $5.log 2>&1
  [ -s "$5" ] || { echo "  synth FAILED for $1"; return 1; }
  grep -cE "^\s+sky130_fd_sc_hd__" $5 >/dev/null || true
  return 0
}

sta_r2r () {  # $1 netlist $2 top $3 clkport $4 period $5 out
  cat > $5.tcl <<EOF
read_liberty $LIB
read_verilog $1
link_design $2
create_clock -name clk -period $4 [get_ports $3]
puts "---CLOCK:clk---"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -digits 3
EOF
  $STA -no_init -no_splash -exit $5.tcl > $5 2>&1
  # Dash FIRST inside the bracket. "[\-0-9.]" makes POSIX grep read a range
  # from backslash to zero and abort with "Invalid range end", which turned
  # every design into NO_PATH on the first run of this script.
  grep -E "(-?[0-9.]+)[[:space:]]+slack \((MET|VIOLATED)\)" $5 | tail -1 | awk '{print $1}'
}

hdr="design\ttop\tmapped_cells_A\tmapped_cells_B\trequired_ns\tperiod_ns\tslack_A\tslack_B\tdelta_B\tverdict\tfanout_share\tpath_delay\tcells_on_path\ttop_cell\ttop_incr\ttop_fanout\ttop_module"
printf "%b\n" "$hdr" > $RES/summary.tsv

while IFS=$'\t' read -r name top clk rst ext; do
  src=$DR/rtl_dataset/$name.v0.$ext
  d=$W/$name; mkdir -p $d
  echo "=== $name ($top) ==="
  synth $name $src $ext $top $d/A.v ""     || { printf "%s\t%s\tSYNTH_FAIL\n" $name $top >> $RES/summary.tsv; continue; }
  synth $name $src $ext $top $d/B.v "$BUF" || { printf "%s\t%s\tSYNTH_FAIL_B\n" $name $top >> $RES/summary.tsv; continue; }
  ca=$(grep -cE "sky130_fd_sc_hd__" $d/A.v); cb=$(grep -cE "sky130_fd_sc_hd__" $d/B.v)

  # pass 1: loose clock, measure the requirement
  s1=$(sta_r2r $d/A.v $top $clk 1000 $d/loose.rpt)
  if [ -z "$s1" ]; then
    echo "  NO reg-to-reg path"; printf "%s\t%s\t%s\t%s\tNO_PATH\n" $name $top $ca $cb >> $RES/summary.tsv; continue
  fi
  req=$(python3 -c "print(round(1000.0 - ($s1), 3))")
  per=$(python3 -c "print(round(0.9 * ($req), 3))")
  # pass 2: 0.9x requirement, same netlist
  sa=$(sta_r2r $d/A.v $top $clk $per $d/tight_A.rpt)
  sb=$(sta_r2r $d/B.v $top $clk $per $d/tight_B.rpt)
  dl=$(python3 -c "print(round(($sb) - ($sa), 3))" 2>/dev/null || echo "?")
  python3 tools/classify_path.py --report $d/tight_A.rpt --netlist $d/A.v --top $top --json > $d/classify.json 2>$d/classify.err
  row=$(python3 - $d/classify.json <<'PY'
import json, sys
try:
    c = json.load(open(sys.argv[1]))
except Exception as e:
    print("UNPARSED\t?\t?\t?\t?\t?\t?\t?"); sys.exit()
t = (c.get("top_cells") or [{}])[0]
print("\t".join(str(x) for x in [c.get("verdict"), c.get("fanout_delay_share"),
      c.get("path_delay_ns"), c.get("cells_on_path"), t.get("cell"),
      t.get("incr_ns"), t.get("fanout"), t.get("module")]))
PY
)
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$name" "$top" "$ca" "$cb" "$req" "$per" "$sa" "$sb" "$dl" "$row" >> $RES/summary.tsv
  echo "  req=$req per=$per  A=$sa  B=$sb  delta=$dl  $(echo "$row" | cut -f1,2)"
  mkdir -p $RES/$name; cp $d/tight_A.rpt $d/tight_B.rpt $d/classify.json $RES/$name/ 2>/dev/null
done < $W/designs.tsv

echo; echo "=== summary ==="; column -t -s $'\t' $RES/summary.tsv 2>/dev/null || cat $RES/summary.tsv
