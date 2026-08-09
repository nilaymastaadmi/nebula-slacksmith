// Optimised: same function, two stages, valid/ready with back-pressure.
// Stage 1 registers the multiply; stage 2 does the add.
//
// This is stream-equivalent to mac_vr_ref -- the same sequence of accepted
// inputs produces the same sequence of emitted outputs. It is NOT equivalent
// under any fixed cycle offset, because under back-pressure the two pipelines
// hold different numbers of in-flight transactions.
module mac_vr_opt #(
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
    reg            s1_valid;
    reg [2*W-1:0]  mul_q;
    reg [2*W-1:0]  c_q;

    wire s2_ready = !out_valid || out_ready;
    wire s1_ready = !s1_valid  || s2_ready;
    assign in_ready = s1_ready;

    always @(posedge clk) begin
        if (rst) begin
            s1_valid  <= 1'b0;
            out_valid <= 1'b0;
            mul_q     <= {(2*W){1'b0}};
            c_q       <= {(2*W){1'b0}};
            y         <= {(2*W){1'b0}};
        end else begin
            if (s1_ready) begin
                s1_valid <= in_valid;
                if (in_valid) begin
                    mul_q <= a * b;
                    c_q   <= c;
                end
            end
            if (s2_ready) begin
                out_valid <= s1_valid;
                if (s1_valid) y <= mul_q + c_q;
            end
        end
    end
endmodule
