// WRONG on exactly one (a,b) pair out of 65,536, k=0. Expected hits in
// 20,000 uniform random vectors is 0.3, so escaping random simulation is the
// likely outcome rather than bad luck.
module sb_mac (input wire clk, input wire rst_n,
               input wire [7:0] a, input wire [7:0] b, input wire [15:0] c,
               output reg [15:0] y);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) y <= 16'h0;
    else        y <= (a == 8'hA5 && b == 8'h3C) ? 16'hDEAD : a * b + c;
endmodule
