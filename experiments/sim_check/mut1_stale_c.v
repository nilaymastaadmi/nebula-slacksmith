// M1 -- forgot to delay `c` alongside the multiply.
//
// THE classic pipelining bug, and the single most likely thing a model gets
// wrong when cutting a datapath: stage 2 adds the *current* c to a product
// computed from inputs one cycle older.
//
// Invisible to any testbench that holds c constant -- which is exactly what a
// directed test for a multiplier looks like.
module mac_opt #(parameter W = 8) (
    input  wire clk, input wire rst,
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire [2*W-1:0] c,
    output reg  [2*W-1:0] y
);
    reg [2*W-1:0] mul_q, c_q;
    always @(posedge clk) begin
        if (rst) begin mul_q <= 0; c_q <= 0; y <= 0; end
        else begin
            mul_q <= a * b;
            c_q   <= c;
            y     <= mul_q + c;      // BUG: should be c_q
        end
    end
endmodule
