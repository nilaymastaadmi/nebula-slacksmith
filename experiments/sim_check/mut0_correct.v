// M0 -- the correct transform. Control row: everything should accept it.
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
            y     <= mul_q + c_q;
        end
    end
endmodule
