// Synchronizer depth reduced from two flops to one, "to save a cycle of
// latency". Under a single-clock abstraction this is a latency change and
// nothing more. In the real design it removes the metastability guard on an
// asynchronous crossing. A functional equivalence checker has no notion of
// metastability and will simply report a latency difference or, with the
// right k, no difference worth reporting.
module sb_cdc (input wire clk_dst, input wire rst_n, input wire flag_src,
               output wire flag_dst);
  reg s1;
  always @(posedge clk_dst or negedge rst_n)
    if (!rst_n) s1 <= 1'b0;
    else        s1 <= flag_src;
  assign flag_dst = s1;
endmodule
