// Fixture: the same included parameter, never overridden anywhere here. Its
// header default is the circuit, so the guard must not refuse it.
module pi_lone (a, y);
  `include "pi_params.vh"
  input  [W-1:0] a;
  output [W-1:0] y;
  assign y = ~a;
endmodule
