// CORRECT re-encoding to one-hot, k=0. The observable behaviour of `busy` is
// identical; only the state encoding changed. Combinational equivalence
// checking matches state elements one for one and there are now three flops
// where there were two, so a naive checker rejects a correct transform.
// This is the mapped-state obligation's reason for existing.
module sb_fsm (input wire clk, input wire rst_n, input wire go,
               output wire busy);
  localparam IDLE = 3'b001, RUN = 3'b010, DONE = 3'b100;
  reg [2:0] st;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) st <= IDLE;
    else case (st)
      IDLE: if (go) st <= RUN;
      RUN:  st <= DONE;
      DONE: st <= IDLE;
      default: st <= IDLE;
    endcase
  assign busy = (st != IDLE);
endmodule
