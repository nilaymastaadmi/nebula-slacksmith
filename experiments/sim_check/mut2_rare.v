// M2 -- correct except on one narrow input combination.
//
// Triggers only when a==0xA5, b==0x3C and c[3:0]==0xF: roughly 1 in 10^6 of the
// input space. Random simulation will not find it in any reasonable vector
// count. Formal finds it immediately, because it searches rather than samples.
module mac_opt #(parameter W = 8) (
    input  wire clk, input wire rst,
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire [2*W-1:0] c,
    output reg  [2*W-1:0] y
);
    reg [2*W-1:0] mul_q, c_q;
    wire corner = (a == 8'hA5) && (b == 8'h3C) && (c[3:0] == 4'hF);
    always @(posedge clk) begin
        if (rst) begin mul_q <= 0; c_q <= 0; y <= 0; end
        else begin
            mul_q <= corner ? (a * b) ^ 16'h0040 : a * b;   // BUG on one corner
            c_q   <= c;
            y     <= mul_q + c_q;
        end
    end
endmodule
