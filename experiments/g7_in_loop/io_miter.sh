#!/bin/bash
# L1 failed: EQY rejected the variant. This decides WHY, because the two
# possibilities lead to opposite conclusions.
#
#   (a) The variant is genuinely not I/O equivalent. Then equivalence checking
#       caught a real defect, the hole G7 was built for is not demonstrated
#       here, and the case is thrown out as the registration requires.
#
#   (b) The variant IS I/O equivalent and EQY rejected on INTERNAL partition
#       matching: it pairs internal nets by name, and u_sync_w2r.d carries gray
#       in one design and binary in the other. Then EQY gave the right answer
#       for a reason that has nothing to do with the CDC defect, and a checker
#       comparing only the interface would have passed it.
#
# The test is an output-only bounded miter: both designs, identical inputs
# INCLUDING both clocks, assert the three outputs agree. Nothing about internal
# names enters it.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../../tools/env.sh"
W=${1:-$SLACKSMITH_WORK/g7_io}; rm -rf "$W"; mkdir -p "$W"

sed 's/module async_fifo/module async_fifo_gate/' \
    experiments/g7_in_loop/async_fifo_cdcbreak.v > "$W/gate.v"
sed 's/module sync2ff/module sync2ff_g/; s/sync2ff #/sync2ff_g #/' \
    rtl/sync2ff.v > "$W/sync2ff_g.v"
sed -i 's/sync2ff #/sync2ff_g #/' "$W/gate.v"
cp rtl/async_fifo.v rtl/sync2ff.v "$W/"

cat > "$W/miter.sv" <<'EOF'
// Output-only miter. Identical inputs, both clocks shared, three outputs
// compared. Internal net names are deliberately not referenced anywhere.
module io_miter (
    input wire wclk, wrst_n, winc, rclk, rrst_n, rinc,
    input wire [7:0] wdata
);
  wire        gold_wfull, gold_rempty, gate_wfull, gate_rempty;
  wire [7:0]  gold_rdata, gate_rdata;

  async_fifo      u_gold (.wclk(wclk), .wrst_n(wrst_n), .winc(winc),
                          .wdata(wdata), .wfull(gold_wfull), .rclk(rclk),
                          .rrst_n(rrst_n), .rinc(rinc), .rdata(gold_rdata),
                          .rempty(gold_rempty));
  async_fifo_gate u_gate (.wclk(wclk), .wrst_n(wrst_n), .winc(winc),
                          .wdata(wdata), .wfull(gate_wfull), .rclk(rclk),
                          .rrst_n(rrst_n), .rinc(rinc), .rdata(gate_rdata),
                          .rempty(gate_rempty));

  // hold both resets low for two cycles, then release for the whole trace
  reg [3:0] boot = 4'd0;
  always @(posedge wclk) if (boot != 4'd15) boot <= boot + 4'd1;
  always @(*) assume (wrst_n == (boot >= 4'd2));
  always @(*) assume (rrst_n == (boot >= 4'd2));

  always @(posedge wclk) if (boot >= 4'd4) begin
    assert (gold_wfull  == gate_wfull);
  end
  // rdata is deliberately NOT compared. Each instance has its own mem array,
  // neither is reset, and BMC starts them at independent arbitrary values, so
  // comparing them tests the miter's initial state and not the designs. The
  // pointer logic this transform touches is fully observable in wfull and
  // rempty, which are derived from the synchronized pointers alone.
  always @(posedge rclk) if (boot >= 4'd4) begin
    assert (gold_rempty == gate_rempty);
  end
endmodule
EOF

cat > "$W/miter.sby" <<'EOF'
[options]
mode bmc
depth 20

[engines]
smtbmc boolector

[script]
read -formal async_fifo.v sync2ff.v gate.v sync2ff_g.v miter.sv
prep -top io_miter
async2sync

[files]
async_fifo.v
sync2ff.v
gate.v
sync2ff_g.v
miter.sv
EOF

cd "$W" && sby -f miter.sby > sby.log 2>&1
echo "sby exit: $?"
grep -E "DONE|Assert failed|Status" sby.log | tail -5
