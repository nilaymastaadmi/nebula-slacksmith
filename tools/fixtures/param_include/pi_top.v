// Fixture: the parent that overrides pi_child's included parameter.
module pi_top (input [15:0] a, output [15:0] y);
  pi_child #(.W(16)) u_child (.a(a), .y(y));
endmodule
