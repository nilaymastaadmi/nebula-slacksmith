// WRONG two-stage pipeline cut, k=+1. `c` is NOT pipelined, so stage 2 adds
// the CURRENT c to the PREVIOUS product. This is the classic pipelining bug
// and it is invisible to any testbench that holds c constant.
module sb_mac (input wire clk, input wire rst_n,
               input wire [7:0] a, input wire [7:0] b, input wire [15:0] c,
               output reg [15:0] y);
  reg [15:0] p;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin p <= 16'h0; y <= 16'h0; end
    else begin p <= a * b; y <= p + c; end
endmodule
