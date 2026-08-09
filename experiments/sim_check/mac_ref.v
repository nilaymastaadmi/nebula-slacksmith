// Golden reference: single-cycle MAC.
// The whole (a*b)+c path is combinational, registered once at the output.
// Latency = 1 cycle. This is the design *before* the transform.
module mac_ref #(
    parameter W = 8
) (
    input  wire            clk,
    input  wire            rst,
    input  wire [W-1:0]    a,
    input  wire [W-1:0]    b,
    input  wire [2*W-1:0]  c,
    output reg  [2*W-1:0]  y
);
    always @(posedge clk) begin
        if (rst) y <= {(2*W){1'b0}};
        else     y <= (a * b) + c;
    end
endmodule
