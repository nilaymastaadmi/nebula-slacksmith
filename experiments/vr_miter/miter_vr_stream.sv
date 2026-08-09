// EXPERIMENT B -- the RIGHT obligation for a back-pressured interface.
//
// Stream equivalence: the two designs agree on the *sequence* of output values,
// with no constraint at all on when each value appears.
//
// Method: both designs are fed in lockstep at the transaction level (a transfer
// happens only when both are ready, so they accept identical input sequences).
// Output transactions are counted independently. An `anyconst` index nsel picks
// an arbitrary transaction; each side latches its nsel-th output; once both have
// produced it, they must be equal.
//
// EXPECTED RESULT: PASS -- on the same design pair that miter_vr_naive rejects.

module miter_vr_stream #(
    parameter W = 8
) (
    input wire            clk,
    input wire            rst,
    input wire            in_valid_raw,
    input wire [W-1:0]    a,
    input wire [W-1:0]    b,
    input wire [2*W-1:0]  c,
    input wire            out_ready
);
    localparam DW = 2*W;

    wire ref_ready, opt_ready;
    wire ref_ov,    opt_ov;
    wire [DW-1:0] ref_y, opt_y;

    // Lockstep input: a transfer occurs only when BOTH designs can accept, so
    // the two see identical input sequences. This is the environment contract,
    // stated rather than assumed silently.
    wire in_valid = in_valid_raw && ref_ready && opt_ready;

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

    wire ref_fire = ref_ov && out_ready;
    wire opt_fire = opt_ov && out_ready;

    // symbolic transaction index
    (* anyconst *) reg [3:0] nsel;

    reg [3:0]     ref_cnt, opt_cnt;
    reg [DW-1:0]  ref_lat, opt_lat;
    reg           ref_got, opt_got;

    always @(posedge clk) begin
        if (rst) begin
            ref_cnt <= 4'd0; opt_cnt <= 4'd0;
            ref_got <= 1'b0; opt_got <= 1'b0;
            ref_lat <= {DW{1'b0}}; opt_lat <= {DW{1'b0}};
        end else begin
            if (ref_fire) begin
                if (ref_cnt == nsel && !ref_got) begin ref_lat <= ref_y; ref_got <= 1'b1; end
                ref_cnt <= ref_cnt + 4'd1;
            end
            if (opt_fire) begin
                if (opt_cnt == nsel && !opt_got) begin opt_lat <= opt_y; opt_got <= 1'b1; end
                opt_cnt <= opt_cnt + 4'd1;
            end
        end
    end

`ifdef FORMAL
    initial assume (rst);

    // Stream equivalence: the nsel-th output of each side must match, whenever
    // each happens to arrive.
    always @(posedge clk) begin
        if (!rst && ref_got && opt_got)
            assert (ref_lat == opt_lat);
    end
`endif
endmodule
