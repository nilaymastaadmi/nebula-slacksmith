// Latency-tolerant miter: mac_opt (latency 1+K) against mac_ref (latency 1)
// padded with K matched output registers.
//
//   Obligation:   for all t >= t0 :  opt.y[t+K] == ref.y[t]
//   Realised as:  opt.y == delay_K(ref.y), asserted once both sides are primed.
//
// Two things are ASSUMED rather than proved, and both are stated explicitly
// because that distinction is the whole point of the exercise:
//
//   1. Reset alignment. The `primed` guard holds the assertion off for the
//      first LAT cycles after reset, when neither pipeline carries meaningful
//      data. Without it the property is trivially false at t=0.
//   2. Rigid interface. mac_ref/mac_opt have no valid/ready handshake and
//      never stall, so a fixed K-cycle offset is a sound obligation. On a
//      back-pressured interface it is NOT -- that case needs stream
//      equivalence instead, and this miter would be the wrong proof.

module miter #(
    parameter W = 8,
    parameter K = 1                    // cycles added by the transform
) (
    input wire            clk,
    input wire            rst,
    input wire [W-1:0]    a,
    input wire [W-1:0]    b,
    input wire [2*W-1:0]  c
);
    localparam DW  = 2*W;
    localparam LAT = 1 + K;            // mac_ref latency (1) + K padding regs

    wire [DW-1:0] y_ref;
    wire [DW-1:0] y_opt;

    mac_ref #(.W(W)) u_ref (
        .clk(clk), .rst(rst), .a(a), .b(b), .c(c), .y(y_ref)
    );

    mac_opt #(.W(W)) u_opt (
        .clk(clk), .rst(rst), .a(a), .b(b), .c(c), .y(y_opt)
    );

    // ---- pad the golden design with K matched output registers ----
    // K=0 is the latency-preserving case and must degenerate to a wire, not
    // to a zero-depth array -- [0:-1] is an invalid range and will not elaborate.
    wire [DW-1:0] y_ref_padded;
    generate
        if (K == 0) begin : g_nopad
            assign y_ref_padded = y_ref;
        end else begin : g_pad
            reg [DW-1:0] ref_pipe [0:K-1];
            integer i;
            always @(posedge clk) begin
                if (rst) begin
                    for (i = 0; i < K; i = i + 1)
                        ref_pipe[i] <= {DW{1'b0}};
                end else begin
                    ref_pipe[0] <= y_ref;
                    for (i = 1; i < K; i = i + 1)
                        ref_pipe[i] <= ref_pipe[i-1];
                end
            end
            assign y_ref_padded = ref_pipe[K-1];
        end
    endgenerate

    // ---- reset alignment: saturating count of cycles since reset released ----
    reg [7:0] prime;
    always @(posedge clk) begin
        if (rst)              prime <= 8'd0;
        else if (prime < LAT) prime <= prime + 8'd1;
    end
    wire primed = (prime >= LAT);

`ifdef FORMAL
    // Start every trace in reset. NOTE: this constrains the BMC base case only.
    // The k-induction step begins from an arbitrary state, which is exactly why
    // the `prove` task may fail where `bmc` passes -- see NOTES.md.
    initial assume (rst);

    // The proof obligation.
    always @(posedge clk) begin
        if (!rst && primed)
            assert (y_opt == y_ref_padded);
    end
`endif

endmodule
