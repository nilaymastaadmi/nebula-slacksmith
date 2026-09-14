// Fixture for tools/param_guard_regression.sh (2026-09-14). W is
// declared in pi_params.vh, so no parameter declaration appears in this module
// body, and pi_top.v overrides it. The guard must refuse this module.
module pi_child (a, y);
  `include "pi_params.vh"
  input  [W-1:0] a;
  output [W-1:0] y;
  assign y = a;
endmodule
