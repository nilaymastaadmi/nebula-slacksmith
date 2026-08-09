// EXPERIMENT A -- the WRONG obligation, applied deliberately.
//
// This is the same k-padded miter that works on a rigid interface, pointed at a
// back-pressured one. It asserts that opt's output stream is ref's output stream
// delayed by a fixed K cycles.
//
// EXPECTED RESULT: FAIL.
//
// The failure is the point. mac_vr_opt is genuinely correct -- see
// miter_vr_stream.sv, which proves it. What fails is the *obligation*, because
// under back-pressure there is no fixed cycle offset between the two designs:
// they hold different numbers of in-flight transactions and drain at different
// rates. A tool that emits this obligation for a valid/ready interface reports
// a correct transform as broken.

module miter_vr_naive #(
    parameter W = 8,
    parameter K = 1
) (
    input wire            clk,
    input wire            rst,
    input wire            in_valid,
    input wire [W-1:0]    a,
    input wire [W-1:0]    b,
    input wire [2*W-1:0]  c,
    input wire            out_ready
);
    localparam DW  = 2*W;
    localparam LAT = 1 + K;

    wire ref_ready, opt_ready;
    wire ref_ov,    opt_ov;
    wire [DW-1:0] ref_y, opt_y;

    mac_vr_ref #(.W(W)) u_ref (
        .clk(clk), .rst(rst), .in_valid(in_valid), .in_ready(ref_ready),
        .a(a), .b(b), .c(c),
        .out_valid(ref_ov), .out_ready(out_ready), .y(ref_y)
    );

    mac_vr_opt #(.W(W)) u_opt (
        .clk(clk), .rst(rst), .in_valid(in_valid), .in_ready(opt_ready),
        .a(a), .b(b), .c(c),
        .out_valid(opt_ov), .out_ready(out_ready), .y(opt_y)
    );

    // pad the golden design with K matched output registers
    reg [DW-1:0] ref_pipe;
    reg          ref_ov_pipe;
    always @(posedge clk) begin
        if (rst) begin
            ref_pipe    <= {DW{1'b0}};
            ref_ov_pipe <= 1'b0;
        end else begin
            ref_pipe    <= ref_y;
            ref_ov_pipe <= ref_ov;
        end
    end

    reg [7:0] prime;
    always @(posedge clk) begin
        if (rst)              prime <= 8'd0;
        else if (prime < LAT) prime <= prime + 8'd1;
    end
    wire primed = (prime >= LAT);

`ifdef FORMAL
    initial assume (rst);

    // The fixed-offset obligation. Sound on a rigid interface, unsound here.
    always @(posedge clk) begin
        if (!rst && primed) begin
            assert (opt_ov == ref_ov_pipe);
            if (opt_ov) assert (opt_y == ref_pipe);
        end
    end
`endif
endmodule
