// A rigid interface wearing a costume.
//
// This module has a port called `out_ready` and a port called `out_valid`. A
// name-matching classifier calls it elastic and emits a stream-equivalence
// obligation for it.
//
// It is not elastic. `out_ready` is never read -- nothing in the module can be
// stalled by it. The correct obligation is the k-padded miter.
//
// This is the case that justifies the structural pass.
module costume_ready #(
    parameter W = 8
) (
    input  wire            clk,
    input  wire            rst,
    input  wire            in_valid,
    input  wire [W-1:0]    a,
    input  wire [W-1:0]    b,
    input  wire [2*W-1:0]  c,
    output reg             out_valid,
    input  wire            out_ready,   // declared, never used
    output reg  [2*W-1:0]  y
);
    always @(posedge clk) begin
        if (rst) begin
            out_valid <= 1'b0;
            y         <= {(2*W){1'b0}};
        end else begin
            out_valid <= in_valid;
            y         <= (a * b) + c;
        end
    end
endmodule
