set -u
# Phase 3 of experiments/drrtl_transfer/PREREGISTRATION.md: split the
# physical lever into buffer-only and sizing-only. Same 15 in-scope designs,
# same netlist A, same per-design period the scored run derived, three levers.
cd /mnt/c/Users/toshn/Projects/slacksmith-benchmark
export PATH=$HOME/tools/oss-cad-suite/bin:$PATH
Y=$HOME/tools/oss-cad-suite/bin/yosys
STA=$HOME/tools/OpenSTA/build/sta
LIB=$HOME/sta_work/sky130hd_tt.lib
DR=${1:-/mnt/c/Users/toshn/Projects/Dr_RTL}
W=$HOME/drrtl_run
P3=experiments/drrtl_transfer/phase3; mkdir -p $P3/results
DU=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure; print(remeasure.dont_use_flags('$LIB'))")
[ $(echo $DU | wc -w) -ge 2 ] || { echo "FATAL: empty dont_use"; exit 3; }
HEAD='+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put'
BUF_ONLY="$HEAD;buffer,-N,16"
SIZE_ONLY="$HEAD;upsize;dnsize"

synth () {  # $1 src $2 ext $3 top $4 out $5 abc-script
  local rv="read_verilog"; [ "$2" = "sv" ] && rv="read_verilog -sv"
  $Y -p "$rv $1; hierarchy -check -top $3; synth -top $3; dfflibmap -liberty $LIB; abc -liberty $LIB $DU -script $5; opt_clean -purge; write_verilog -noattr $4; stat" > $4.log 2>&1
  [ -s "$4" ] || { echo "  synth FAILED: $4"; return 1; }
  sed -i -E 's/^(\s*(input|output|inout|wire|reg))\s+signed\s+/\1 /' $4
}
sta_r2r () {  # $1 netlist $2 top $3 clk $4 period $5 out
  cat > $5.tcl <<EOF
read_liberty $LIB
read_verilog $1
link_design $2
create_clock -name clk -period $4 [get_ports $3]
puts "---CLOCK:clk---"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -digits 3
EOF
  $STA -no_init -no_splash -exit $5.tcl > $5 2>&1
  grep -qE 'syntax error' $5 && { echo READ_FAIL; return; }
  grep -E "(-?[0-9.]+)[[:space:]]+slack \((MET|VIOLATED)\)" $5 | tail -1 | awk '{print $1}'
}

# in-scope designs and their scored periods
python3 - <<'PY' > $W/phase3_designs.tsv
import csv, json
rows = list(csv.reader(open("experiments/drrtl_transfer/results/summary.tsv"), delimiter="\t")); h = rows[0]
d = json.load(open("/mnt/c/Users/toshn/Projects/Dr_RTL/syn_flow/design_all.json"))
for r in rows[1:]:
    r = r + [""]*(len(h)-len(r)); rec = dict(zip(h, r))
    try: float(rec["slack_A"])
    except ValueError: continue
    top, clk, rst, ext = d[rec["design"]]
    print("\t".join([rec["design"], top, clk, ext, rec["period_ns"], rec["slack_A"], rec["slack_B"], rec["verdict"]]))
PY

printf "design\tverdict\tperiod\tslack_A\tslack_both\tslack_buf\tslack_size\tgain_both\tgain_buf\tgain_size\tcells_buf\tcells_size\n" > $P3/results/summary.tsv
while IFS=$'\t' read -r name top clk ext per sa sb verdict; do
  src=$DR/rtl_dataset/$name.v0.$ext; d=$W/$name
  echo "=== $name ($verdict) period=$per ==="
  synth $src $ext $top $d/Bbuf.v "$BUF_ONLY"   || continue
  synth $src $ext $top $d/Bsize.v "$SIZE_ONLY" || continue
  s_buf=$(sta_r2r $d/Bbuf.v $top $clk $per $d/tight_Bbuf.rpt)
  s_size=$(sta_r2r $d/Bsize.v $top $clk $per $d/tight_Bsize.rpt)
  cb=$(grep -cE "sky130_fd_sc_hd__" $d/Bbuf.v); cs=$(grep -cE "sky130_fd_sc_hd__" $d/Bsize.v)
  g_both=$(python3 -c "print(round(($sb)-($sa),3))"); g_buf=$(python3 -c "print(round(($s_buf)-($sa),3))"); g_size=$(python3 -c "print(round(($s_size)-($sa),3))")
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" $name $verdict $per $sa $sb $s_buf $s_size $g_both $g_buf $g_size $cb $cs >> $P3/results/summary.tsv
  echo "  A=$sa  both=$sb (+$g_both)  buf=$s_buf (+$g_buf)  size=$s_size (+$g_size)"
  mkdir -p $P3/results/$name; cp $d/tight_Bbuf.rpt $d/tight_Bsize.rpt $P3/results/$name/ 2>/dev/null
done < $W/phase3_designs.tsv
echo; cat $P3/results/summary.tsv
