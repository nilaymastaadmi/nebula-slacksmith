// Two multipliers, one per arm of the mux.
module sb_sel (input wire clk, input wire rst_n, input wire sel,
               input wire [7:0] a, input wire [7:0] b, input wire [15:0] c,
               output reg [15:0] y);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) y <= 16'h0;
    else        y <= sel ? (a * b + c) : (a * b - c);
endmodule
