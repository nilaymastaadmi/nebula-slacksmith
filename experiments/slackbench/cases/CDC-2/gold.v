// Multi-bit pointer crossing. The pointer is GRAY encoded BEFORE it is
// synchronized, so the bus that actually crosses the domain boundary changes
// exactly one bit per increment.
module sb_ptr (input wire clk, input wire rst_n, input wire inc,
               output wire [3:0] ptr_sync);
  reg [3:0] bin;
  reg [3:0] s1, s2;
  wire [3:0] gray = bin ^ (bin >> 1);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin bin <= 4'h0; s1 <= 4'h0; s2 <= 4'h0; end
    else begin
      if (inc) bin <= bin + 4'h1;
      s1 <= gray;
      s2 <= s1;
    end
  assign ptr_sync = s2;
endmodule
