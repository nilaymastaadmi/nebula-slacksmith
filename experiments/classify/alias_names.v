// Genuinely elastic, but spelled differently: vld/rdy rather than valid/ready.
// Tests that the lexical pass is not tied to one house style.
module alias_names #(
    parameter W = 8
) (
    input  wire            clk,
    input  wire            rst,
    input  wire            i_vld,
    output wire            i_rdy,
    input  wire [W-1:0]    a,
    input  wire [W-1:0]    b,
    input  wire [2*W-1:0]  c,
    output reg             o_vld,
    input  wire            o_rdy,
    output reg  [2*W-1:0]  y
);
    assign i_rdy = !o_vld || o_rdy;

    always @(posedge clk) begin
        if (rst) begin
            o_vld <= 1'b0;
            y     <= {(2*W){1'b0}};
        end else if (i_vld && i_rdy) begin
            o_vld <= 1'b1;
            y     <= (a * b) + c;
        end else if (o_rdy) begin
            o_vld <= 1'b0;
        end
    end
endmodule
