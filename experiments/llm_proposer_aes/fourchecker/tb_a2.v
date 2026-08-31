// Four-checker column for A2 (decode_duplication), which EQY refuted on the
// round_key partition. A2 splits key_mem [0:14] of 128 bits into four arrays
// of 32 bits, writes and reads them at the same index, and is equivalent by
// inspection. This drives gold and gate in lockstep and reports the first
// round index at which round_key differs, so the mechanism is measured rather
// than guessed at.
`timescale 1ns/1ps

module tb_a2;
  reg clk = 0, reset_n = 0, keylen = 0, init = 0;
  reg [255:0] key = 256'h0;
  reg [3:0]   round = 4'h0;
  reg [31:0]  new_sboxw = 32'h0;

  wire [127:0] rk_gold, rk_gate;
  wire         rdy_gold, rdy_gate;
  wire [31:0]  sbw_gold, sbw_gate;

  aes_key_mem_gold u_g (.clk(clk), .reset_n(reset_n), .key(key),
    .keylen(keylen), .init(init), .round(round), .round_key(rk_gold),
    .ready(rdy_gold), .sboxw(sbw_gold), .new_sboxw(new_sboxw));

  aes_key_mem_gate u_t (.clk(clk), .reset_n(reset_n), .key(key),
    .keylen(keylen), .init(init), .round(round), .round_key(rk_gate),
    .ready(rdy_gate), .sboxw(sbw_gate), .new_sboxw(new_sboxw));

  always #5 clk = ~clk;

  // The sbox is not instantiated here, so feed the requested word straight
  // back. Both designs see the identical stimulus, which is all the
  // comparison requires.
  always @* new_sboxw = sbw_gold;

  integer r, diffs;
  initial begin
    diffs = 0;
    key = 256'h000102030405060708090a0b0c0d0e0f_101112131415161718191a1b1c1d1e1f;
    repeat (4) @(posedge clk);
    reset_n = 1;
    repeat (2) @(posedge clk);
    init = 1; @(posedge clk); init = 0;
    // let key expansion finish
    repeat (60) @(posedge clk);

    for (r = 0; r < 16; r = r + 1) begin
      round = r[3:0];
      #1;
      if (rk_gold !== rk_gate) begin
        diffs = diffs + 1;
        $display("MISMATCH round=%0d", r);
        $display("   gold round_key = %032h", rk_gold);
        $display("   gate round_key = %032h", rk_gate);
      end else begin
        $display("match    round=%0d  round_key = %032h", r, rk_gold);
      end
      @(posedge clk);
    end

    $display("");
    if (diffs == 0)
      $display("RESULT: simulation MISSED the defect (0 mismatches over rounds 0-15)");
    else
      $display("RESULT: simulation CAUGHT the defect (%0d mismatching rounds)", diffs);
    $finish;
  end
endmodule
