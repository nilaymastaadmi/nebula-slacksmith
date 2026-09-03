// Accumulator with an enable. Adds `d` whenever en is high.
module sb_acc (input wire clk, input wire rst_n, input wire en,
               input wire [7:0] d, output reg [15:0] acc);
  always @(posedge clk or negedge rst_n)
    if (!rst_n)   acc <= 16'h0;
    else if (en)  acc <= acc + d;
endmodule
