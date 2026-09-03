// CORRECT operator sharing, k=0: one multiplier feeding both arms. Every
// checker should accept this. It is here so that a checker which rejects
// everything cannot score well.
module sb_sel (input wire clk, input wire rst_n, input wire sel,
               input wire [7:0] a, input wire [7:0] b, input wire [15:0] c,
               output reg [15:0] y);
  wire [15:0] prod = a * b;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) y <= 16'h0;
    else        y <= sel ? (prod + c) : (prod - c);
endmodule
