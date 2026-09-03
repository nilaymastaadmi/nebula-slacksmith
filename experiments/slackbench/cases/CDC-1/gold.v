// Single-bit level crossing with a proper two-flop synchronizer.
module sb_cdc (input wire clk_dst, input wire rst_n, input wire flag_src,
               output wire flag_dst);
  reg s1, s2;
  always @(posedge clk_dst or negedge rst_n)
    if (!rst_n) begin s1 <= 1'b0; s2 <= 1'b0; end
    else begin s1 <= flag_src; s2 <= s1; end
  assign flag_dst = s2;
endmodule
