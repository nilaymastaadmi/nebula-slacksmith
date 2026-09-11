#!/bin/bash
# Measure i2c_master_top's own requirement and freeze an SDC at 0.9x it, the
# same rule experiments/drrtl_transfer/ applied to all 20 designs. The target
# is set BEFORE the loop runs and is never revisited: choosing it after seeing
# where the path lands is a void condition in PREREGISTRATION.md.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
D=experiments/unforced
W=$SLACKSMITH_WORK/unforced_setup; rm -rf $W; mkdir -p $W
DU=$(python3 -c "import sys; sys.path.insert(0,'tools'); import remeasure; print(remeasure.dont_use_flags('$LIBERTY'))")
[ "$(echo $DU | wc -w)" -ge 2 ] || { echo "FATAL: dont_use empty"; exit 3; }

$OSS_CAD_BIN/yosys -p "read_verilog $D/rtl/i2c.v; hierarchy -check -top i2c_master_top; \
  synth -top i2c_master_top; dfflibmap -liberty $LIBERTY; \
  abc -liberty $LIBERTY $DU; opt_clean -purge; write_verilog -noattr $W/mapped.v; stat" > $W/synth.log 2>&1
grep -E "Number of cells|Chip area" $W/synth.log | tail -2
sed -i -E 's/^(\s*(input|output|inout|wire|reg))\s+signed\s+/\1 /' $W/mapped.v

# Loose clock first, so the reported slack gives the requirement directly.
cat > $W/meas.tcl <<TCL
read_liberty $LIBERTY
read_verilog $W/mapped.v
link_design i2c_master_top
create_clock -name wb_clk_i -period 100.0 [get_ports wb_clk_i]
report_checks -path_delay max -group_path_count 1 -digits 3
TCL
$STA_BIN -no_init -exit $W/meas.tcl > $W/meas.log 2>&1
REQ=$(python3 - <<'PY'
import re, os
txt = open(os.path.expanduser(os.environ["W"] + "/meas.log"), encoding="utf-8", errors="replace").read()
m = re.search(r"^\s*(-?[\d.]+)\s+slack", txt, re.M)
print("%.3f" % (100.0 - float(m.group(1))) if m else "ERR")
PY
)
echo "measured requirement: $REQ ns"
[ "$REQ" = "ERR" ] && { echo "FATAL: no slack line"; tail -20 $W/meas.log; exit 4; }
TGT=$(python3 -c "print('%.3f' % (float('$REQ') * 0.9))")
echo "target (0.9x): $TGT ns"
cat > $D/i2c.sdc <<SDC
# Frozen before the loop ran. 0.9x i2c_master_top's own measured requirement
# of $REQ ns, the same rule experiments/drrtl_transfer/ used for all 20
# designs. No timing exception is used anywhere in this file.
create_clock -name wb_clk_i -period $TGT [get_ports wb_clk_i]
set_input_delay  0.0 -clock wb_clk_i [all_inputs]
set_output_delay 0.0 -clock wb_clk_i [all_outputs]
SDC
cat $D/i2c.sdc
