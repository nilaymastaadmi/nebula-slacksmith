// WRONG only on BACK-TO-BACK enables, k=0. It remembers the previous enable
// and skips the accumulate on the second of two consecutive high cycles. A
// testbench that pulses `en` with gaps, which is what a person writes,
// never exercises it.
module sb_acc (input wire clk, input wire rst_n, input wire en,
               input wire [7:0] d, output reg [15:0] acc);
  reg en_q;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin acc <= 16'h0; en_q <= 1'b0; end
    else begin
      en_q <= en;
      if (en && !en_q) acc <= acc + d;
    end
endmodule
