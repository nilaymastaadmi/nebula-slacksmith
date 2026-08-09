// Optimised: the (a*b)+c critical path is cut into two pipeline stages.
// Stage 1 registers the multiply; stage 2 does the add.
// `c` is delayed one cycle so it stays aligned with the multiply result.
//
// Latency = 2 cycles. This is the transform under test: one extra cycle
// bought in exchange for a shorter critical path. Combinational equivalence
// checking cannot validate this -- the register counts no longer correspond.
module mac_opt #(
    parameter W = 8
) (
    input  wire            clk,
    input  wire            rst,
    input  wire [W-1:0]    a,
    input  wire [W-1:0]    b,
    input  wire [2*W-1:0]  c,
    output reg  [2*W-1:0]  y
);
    reg [2*W-1:0] mul_q;
    reg [2*W-1:0] c_q;

    always @(posedge clk) begin
        if (rst) begin
            mul_q <= {(2*W){1'b0}};
            c_q   <= {(2*W){1'b0}};
            y     <= {(2*W){1'b0}};
        end else begin
            mul_q <= a * b;
            c_q   <= c;
            y     <= mul_q + c_q;
        end
    end
endmodule
