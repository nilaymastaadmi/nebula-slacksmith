// Status register with a reset. `status` is defined from cycle zero.
module sb_stat (input wire clk, input wire rst_n, input wire we,
                input wire [7:0] d, output wire [7:0] status);
  reg [7:0] q;
  always @(posedge clk or negedge rst_n)
    if (!rst_n)   q <= 8'h00;
    else if (we)  q <= d;
  assign status = q;
endmodule
