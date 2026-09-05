set -u
# SECONDARY, POST-HOC pass. Added 2026-09-02 after the first two rows of the
# registered phase 1 (vending_machine, ticket_machine) came back with
# reg-to-reg requirements under 0.8 ns: their real logic is on I/O-facing
# paths the registered protocol excludes on purpose. This pass times ALL
# paths (in-to-reg, reg-to-out, in-to-out, reg-to-reg) with zero external
# delay and the declared reset false-pathed, then classifies the overall
# worst path. Same netlists, same 0.9x rule, same unchanged thresholds.
#
# It is reported as secondary and unregistered. It does not replace phase 1.
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
STA=$STA_BIN
LIB=$LIBERTY
DR=${1:-/mnt/c/Users/toshn/Projects/Dr_RTL}
W=$HOME/drrtl_run
RES=experiments/drrtl_transfer/results_allpaths; mkdir -p $RES

sta_all () {  # $1 netlist $2 top $3 clk $4 rst $5 period $6 out
  cat > $6.tcl <<EOF
read_liberty $LIB
read_verilog $1
link_design $2
create_clock -name clk -period $5 [get_ports $3]
set_false_path -from [get_ports $4]
# I/O paths are timed ONLY if the ports carry a delay constraint. Leaving them
# unconstrained does not mean "zero delay", it means "excluded", which is why
# the first version of this pass reproduced the reg-to-reg table exactly and
# timed nothing new. Zero external delay, stated explicitly.
set_input_delay  0 -clock clk [all_inputs -no_clocks]
set_output_delay 0 -clock clk [all_outputs]
puts "---CLOCK:clk---"
report_checks -path_delay max -group_path_count 1 -digits 3
EOF
  $STA -no_init -no_splash -exit $6.tcl > $6 2>&1
  if grep -qE 'syntax error' $6; then echo READ_FAIL; return; fi
  if grep -qE 'command failed' $6; then return; fi
  grep -E "(-?[0-9.]+)[[:space:]]+slack \((MET|VIOLATED)\)" $6 | tail -1 | awk '{print $1}'
}

hdr="design\ttop\trequired_ns\tperiod_ns\tslack_A\tslack_B\tdelta_B\tverdict\tfanout_share\tpath_delay\tcells_on_path\ttop_cell\ttop_incr\ttop_fanout\ttop_module"
printf "%b\n" "$hdr" > $RES/summary.tsv

while IFS=$'\t' read -r name top clk rst ext; do
  d=$W/$name
  [ -s $d/A.v ] && [ -s $d/B.v ] || { printf "%s\t%s\tNO_NETLIST\n" $name $top >> $RES/summary.tsv; continue; }
  echo "=== $name ==="
  s1=$(sta_all $d/A.v $top $clk $rst 1000 $d/io_loose.rpt)
  [ "$s1" = "READ_FAIL" ] && { printf "%s\t%s\tSTA_READ_FAIL\n" $name $top >> $RES/summary.tsv; continue; }
  [ -z "$s1" ] && { printf "%s\t%s\tNO_PATH\n" $name $top >> $RES/summary.tsv; continue; }
  req=$(python3 -c "print(round(1000.0 - ($s1), 3))")
  per=$(python3 -c "print(round(0.9 * ($req), 3))")
  sa=$(sta_all $d/A.v $top $clk $rst $per $d/io_A.rpt)
  sb=$(sta_all $d/B.v $top $clk $rst $per $d/io_B.rpt)
  dl=$(python3 -c "print(round(($sb) - ($sa), 3))" 2>/dev/null || echo "?")
  python3 tools/classify_path.py --report $d/io_A.rpt --netlist $d/A.v --top $top --json > $d/io_classify.json 2>/dev/null
  row=$(python3 - $d/io_classify.json <<'PY'
import json, sys
try: c = json.load(open(sys.argv[1]))
except Exception: print("UNPARSED\t?\t?\t?\t?\t?\t?\t?"); sys.exit()
t = (c.get("top_cells") or [{}])[0]
print("\t".join(str(x) for x in [c.get("verdict"), c.get("fanout_delay_share"),
      c.get("path_delay_ns"), c.get("cells_on_path"), t.get("cell"),
      t.get("incr_ns"), t.get("fanout"), t.get("module")]))
PY
)
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$name" "$top" "$req" "$per" "$sa" "$sb" "$dl" "$row" >> $RES/summary.tsv
  echo "  req=$req per=$per  A=$sa  B=$sb  delta=$dl  $(echo "$row" | cut -f1,2)"
  mkdir -p $RES/$name; cp $d/io_A.rpt $d/io_B.rpt $d/io_classify.json $RES/$name/ 2>/dev/null
done < $W/designs.tsv

echo; echo "=== all-paths summary ==="; cat $RES/summary.tsv
