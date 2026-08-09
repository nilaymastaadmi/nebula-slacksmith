// Golden reference, valid/ready handshake, single stage. Latency 1 transfer.
module mac_vr_ref #(
    parameter W = 8
) (
    input  wire            clk,
    input  wire            rst,
    input  wire            in_valid,
    output wire            in_ready,
    input  wire [W-1:0]    a,
    input  wire [W-1:0]    b,
    input  wire [2*W-1:0]  c,
    output reg             out_valid,
    input  wire            out_ready,
    output reg  [2*W-1:0]  y
);
    assign in_ready = !out_valid || out_ready;

    always @(posedge clk) begin
        if (rst) begin
            out_valid <= 1'b0;
            y         <= {(2*W){1'b0}};
        end else if (in_valid && in_ready) begin
            out_valid <= 1'b1;
            y         <= (a * b) + c;
        end else if (out_ready) begin
            out_valid <= 1'b0;
        end
    end
endmodule
