// M3 -- pipeline register one bit too narrow, dropping the product MSB.
// A plausible width slip when introducing a new register. Fires on any
// product >= 2^15, which random 8-bit operands hit often.
// Expected to be caught by everything -- included so the matrix has a row where
// simulation does its job.
module mac_opt #(parameter W = 8) (
    input  wire clk, input wire rst,
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire [2*W-1:0] c,
    output reg  [2*W-1:0] y
);
    reg [2*W-2:0] mul_q;      // BUG: 15 bits, should be 16
    reg [2*W-1:0] c_q;
    always @(posedge clk) begin
        if (rst) begin mul_q <= 0; c_q <= 0; y <= 0; end
        else begin
            mul_q <= a * b;
            c_q   <= c;
            y     <= mul_q + c_q;
        end
    end
endmodule
