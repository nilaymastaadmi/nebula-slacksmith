// The reset is dropped, "because the register is always written before it is
// read". It is not: with `we` held low, `status` reports whatever the flop
// powered up as. In four-state simulation that is `x`, and a testbench that
// compares with `==` will silently skip every such cycle, because `x == x`
// evaluates to `x` and `if (x)` takes the false branch.
module sb_stat (input wire clk, input wire rst_n, input wire we,
                input wire [7:0] d, output wire [7:0] status);
  reg [7:0] q;
  always @(posedge clk)
    if (we) q <= d;
  assign status = q;
endmodule
