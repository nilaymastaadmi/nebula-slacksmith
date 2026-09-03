// Three-state FSM, binary encoded.
module sb_fsm (input wire clk, input wire rst_n, input wire go,
               output wire busy);
  localparam IDLE = 2'd0, RUN = 2'd1, DONE = 2'd2;
  reg [1:0] st;
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
