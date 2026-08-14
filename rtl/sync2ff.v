// ---------------------------------------------------------------------------
// sync2ff - two-flop synchronizer for single-bit (or gray-coded multi-bit)
//           signals crossing into the `clk` domain.
//
// Used for every single-bit control crossing in this design, and as the
// pointer synchronizer inside async_fifo (where the input is gray coded, so
// synchronizing the bits independently is safe).
//
// Async active-low reset, reset value parameterizable.
// ---------------------------------------------------------------------------
module sync2ff #(
    parameter WIDTH   = 1,
    parameter RST_VAL = 1'b0
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire [WIDTH-1:0] d,
    output wire [WIDTH-1:0] q
);

    reg [WIDTH-1:0] meta_r;
    reg [WIDTH-1:0] sync_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            meta_r <= {WIDTH{RST_VAL}};
            sync_r <= {WIDTH{RST_VAL}};
        end else begin
            meta_r <= d;
            sync_r <= meta_r;
        end
    end

    assign q = sync_r;

endmodule
