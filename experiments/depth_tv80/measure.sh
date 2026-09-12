#!/bin/bash
# Phase 2 of experiments/depth_tv80/PREREGISTRATION.md: columns A, B and C for
# gold, the control, and every phase-1 proposal that reached PROVEN inside the
# loop. Extra variants may be passed as name:path (the declared handoff
# fallback); they are labelled by the name given.
#
#   A  synth; dfflibmap; abc                       unbuffered, zero-parasitic
#   B  A with abc -script buffer/upsize/dnsize     the loop's physical lever
#   C  A through OpenROAD place + repair_design    placement parasitics
#
# usage: bash experiments/depth_tv80/measure.sh [name:src.v ...]
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/depth_tv80; R=$D/results; mkdir -p $R
W=$SLACKSMITH_WORK/depth_tv80/measure; mkdir -p $W
Y=$OSS_CAD_BIN/yosys; STA=$STA_BIN; LIB=$LIBERTY; OR=$OPENROAD_BIN; P=$ORFS_PLATFORM
TOP=tv80s; SDC=$REPO/$D/tv80.sdc
DU=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure; print(remeasure.dont_use_flags('$LIB'))")
[ "$(echo $DU | wc -w)" -ge 2 ] || { echo "FATAL: dont_use flags empty"; exit 3; }
# Byte-identical to tools/slacksmith.py BOTH and experiments/drrtl_transfer/.
BUF='+strash;&get,-n;&fraig,-x;&put;scorr;dc2;dretime;strash;&get,-n;&dch,-f;&nf;&put;buffer,-N,16;upsize;dnsize'

python3 $D/make_control.py || { echo "FATAL: control drifted from its definition"; exit 4; }

synth () {  # $1 src  $2 out  $3 abc-script-or-empty
  local abc="abc -liberty $LIB $DU"; [ -n "$3" ] && abc="$abc -script $3"
  $Y -p "read_verilog $1; hierarchy -check -top $TOP; synth -top $TOP; dfflibmap -liberty $LIB; $abc; opt_clean -purge; write_verilog -noattr $2; stat" > $2.log 2>&1
  [ -s "$2" ] || { echo "  synth FAILED: $1 (see $2.log)"; return 1; }
  sed -i -E 's/^(\s*(input|output|inout|wire|reg))\s+signed\s+/\1 /' $2
}
sta_r2r () {  # $1 netlist  $2 out  -> slack
  cat > $2.tcl <<TCL
read_liberty $LIB
read_verilog $1
link_design $TOP
read_sdc $SDC
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -digits 3
TCL
  $STA -no_init -no_splash -exit $2.tcl > $2 2>&1
  grep -E "(-?[0-9.]+)[[:space:]]+slack \((MET|VIOLATED)\)" $2 | tail -1 | awk '{print $1}'
}
openroad_repair () {  # $1 netlist  $2 workdir  -> "before after area_before area_after"
  mkdir -p $2
  cat > $2/flow.tcl <<TCL
read_lef $P/lef/sky130_fd_sc_hd.tlef
read_lef $P/lef/sky130_fd_sc_hd_merged.lef
read_liberty $LIB
read_verilog $1
link_design $TOP
read_sdc $SDC
initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2.0 -site unithd
source $P/make_tracks.tcl
place_pins -hor_layers met3 -ver_layers met2
source $P/setRC.tcl
global_placement -density 0.60
estimate_parasitics -placement
puts "=====> BEFORE"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_count 1 -digits 3
report_design_area
repair_design
detailed_placement
estimate_parasitics -placement
puts "=====> AFTER"
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_count 1 -digits 3
report_design_area
exit
TCL
  $OR -no_init -exit $2/flow.tcl > $2/flow.log 2>&1
  local b a ab aa
  b=$(awk '/=====> BEFORE/{f=1} /=====> AFTER/{f=0} f && /slack \(/{print $1}' $2/flow.log | tail -1)
  a=$(awk '/=====> AFTER/{f=1} f && /slack \(/{print $1}' $2/flow.log | tail -1)
  ab=$(awk '/=====> BEFORE/{f=1} /=====> AFTER/{f=0} f && /Design area/{print $3}' $2/flow.log | tail -1)
  aa=$(awk '/=====> AFTER/{f=1} f && /Design area/{print $3}' $2/flow.log | tail -1)
  echo "${b:-NA} ${a:-NA} ${ab:-NA} ${aa:-NA}"
}

# Variants: gold, control, every in-loop PROVEN phase-1 proposal, then extras.
VARS="gold:$REPO/$D/rtl/tv80.v ctrl_rename:$REPO/$D/rtl_ctrl_rename/tv80.v ctrl_reorder:$REPO/$D/rtl_ctrl_reorder/tv80.v ctrl_flip:$REPO/$D/rtl_ctrl_flip/tv80.v"
PROVEN=$(python3 - "$R" <<'PY'
import glob, json, os, sys
R = sys.argv[1]
for dj in sorted(glob.glob(os.path.join(R, "run*", "decisions.jsonl"))):
    run = os.path.basename(os.path.dirname(dj))
    for line in open(dj):
        try: rec = json.loads(line)
        except Exception: continue
        if rec.get("step") == "gate" and rec.get("G4") == "PROVEN":
            pid = rec["proposal"]
            cands = glob.glob(os.path.join(R, run, "online_variants", pid + "_*.v"))
            if cands:
                print(f"{run}_{pid}_{rec.get('def_id','')}:{os.path.abspath(cands[0])}")
PY
)
VARS="$VARS $PROVEN $*"
echo "variants: $VARS"

OUT=$R/survival.tsv
printf "variant\tA_unbuffered\tB_abc_lever\tC_before_repair\tC_after_repair\tarea_before\tarea_after\tcells_A\tcells_B\n" > $OUT
for nv in $VARS; do
  name=${nv%%:*}; src=${nv#*:}
  [ -s "$src" ] || { echo "SKIP $name: missing $src"; continue; }
  d=$W/$name; mkdir -p $d
  echo "=== $name ==="
  synth "$src" $d/A.v ""     || continue
  synth "$src" $d/B.v "$BUF" || continue
  a=$(sta_r2r $d/A.v $d/A.rpt); b=$(sta_r2r $d/B.v $d/B.rpt)
  c=$(openroad_repair $d/A.v $d/or)
  ca=$(grep -cE '^\s*sky130_fd_sc_hd__' $d/A.v); cb=$(grep -cE '^\s*sky130_fd_sc_hd__' $d/B.v)
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$name" "$a" "$b" "$(echo $c | tr ' ' '\t')" "$ca" "$cb" | tee -a $OUT
  cp $d/or/flow.log $R/or_$name.log 2>/dev/null
done

# R60: gold through the OpenROAD flow a second time.
echo "=== gold_run2 (R60) ==="
c2=$(openroad_repair $W/gold/A.v $W/gold/or2)
printf "gold_run2\t\t\t%s\t\t\n" "$(echo $c2 | tr ' ' '\t')" | tee -a $OUT

echo; echo "=== survival table ==="; column -t -s $'\t' $OUT 2>/dev/null || cat $OUT
