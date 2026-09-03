// The gray encoder is moved to AFTER the synchronizer, on the argument that
// it is the same function either way. It is: gray(delay(x)) equals
// delay(gray(x)) because the encoder is combinational, so this pair is
// FUNCTIONALLY EQUIVALENT and every functional checker should say so.
//
// The bug is that the bus now crossing the boundary is raw binary. On
// 0111 to 1000 four bits change at once, and a receiver in another clock
// domain can latch any of sixteen intermediate values. Gray coding exists
// precisely so that a mid-transition sample yields the old or the new value
// and nothing else.
//
// No functional equivalence checker can see this, because nothing about the
// function changed. That is the point of the case.
module sb_ptr (input wire clk, input wire rst_n, input wire inc,
               output wire [3:0] ptr_sync);
  reg [3:0] bin;
  reg [3:0] s1, s2;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin bin <= 4'h0; s1 <= 4'h0; s2 <= 4'h0; end
    else begin
      if (inc) bin <= bin + 4'h1;
      s1 <= bin;
      s2 <= s1;
    end
  assign ptr_sync = s2 ^ (s2 >> 1);
endmodule
