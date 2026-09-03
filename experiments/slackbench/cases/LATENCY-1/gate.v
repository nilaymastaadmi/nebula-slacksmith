// CORRECT two-stage pipeline cut, k=+1. `c` is pipelined alongside the
// product so stage 2 adds the operand that belongs with it.
module sb_mac (input wire clk, input wire rst_n,
               input wire [7:0] a, input wire [7:0] b, input wire [15:0] c,
               output reg [15:0] y);
  reg [15:0] p, c_q;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin p <= 16'h0; c_q <= 16'h0; y <= 16'h0; end
    else begin p <= a * b; c_q <= c; y <= p + c_q; end
endmodule
