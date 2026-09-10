// ---------------------------------------------------------------------------
// async_fifo - gray-pointer dual-clock FIFO (Cummings style).
//
//   * Binary pointers are AW+1 bits wide; the extra MSB distinguishes
//     full from empty.
//   * The pointer that crosses domains is the GRAY encoding
//     (bin ^ (bin >> 1)), so exactly one bit changes per increment.
//   * Each pointer is synchronized into the opposite domain through a
//     two-flop synchronizer (sync2ff).
//   * full / empty are registered flags (computed from the *next* pointer
//     value), so they are glitch-free and never combinationally depend on
//     winc / rinc.  That guarantees no combinational loop when a consumer
//     drives `rinc = ~rempty`.
//
// The storage array is a plain reg array of 2**AW words (AW <= 8 keeps it
// under the 256-word limit).  See README "Deviations" for why the array
// itself is not reset.
//
// Every pointer / flag / synchronizer flop has an async active-low reset.
// ---------------------------------------------------------------------------
module async_fifo #(
    parameter DW = 8,
    parameter AW = 3          // depth = 2**AW, must be >= 2
) (
    // write side
    input  wire          wclk,
    input  wire          wrst_n,
    input  wire          winc,
    input  wire [DW-1:0] wdata,
    output wire          wfull,
    // read side
    input  wire          rclk,
    input  wire          rrst_n,
    input  wire          rinc,
    output wire [DW-1:0] rdata,
    output wire          rempty
);

    localparam DEPTH = (1 << AW);

    reg [DW-1:0] mem [0:DEPTH-1];

    // ---------------------------------------------------------------- write
    reg  [AW:0] wbin_r;
    // CDC VARIANT: the register that crosses now holds RAW BINARY.
    // Same width, same flop count, same cycle behaviour.
    reg  [AW:0] wcross_r;
    reg         wfull_r;

    wire        wen       = winc & ~wfull_r;
    wire [AW:0] wbin_nxt  = wbin_r + {{AW{1'b0}}, wen};
    wire [AW:0] wgray_nxt = wbin_nxt ^ (wbin_nxt >> 1);

    wire [AW:0] rcross_sync;  // RAW BINARY seen in the write domain
    wire [AW:0] rgray_sync = rcross_sync ^ (rcross_sync >> 1);

    // full when the next write gray pointer equals the synchronized read
    // gray pointer with its top two bits inverted
    wire wfull_nxt = (wgray_nxt == {~rgray_sync[AW:AW-1], rgray_sync[AW-2:0]});

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wbin_r  <= {(AW+1){1'b0}};
            wcross_r <= {(AW+1){1'b0}};
            wfull_r <= 1'b0;
        end else begin
            wbin_r  <= wbin_nxt;
            wcross_r <= wbin_nxt;
            wfull_r <= wfull_nxt;
        end
    end

    always @(posedge wclk) begin
        if (wen)
            mem[wbin_r[AW-1:0]] <= wdata;
    end

    assign wfull = wfull_r;

    // ----------------------------------------------------------------- read
    reg  [AW:0] rbin_r;
    reg  [AW:0] rcross_r;
    reg         rempty_r;

    wire        ren       = rinc & ~rempty_r;
    wire [AW:0] rbin_nxt  = rbin_r + {{AW{1'b0}}, ren};
    wire [AW:0] rgray_nxt = rbin_nxt ^ (rbin_nxt >> 1);

    wire [AW:0] wcross_sync;  // RAW BINARY seen in the read domain
    // gray encode moved to the FAR side of the crossing
    wire [AW:0] wgray_sync = wcross_sync ^ (wcross_sync >> 1);

    wire rempty_nxt = (rgray_nxt == wgray_sync);

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rbin_r   <= {(AW+1){1'b0}};
            rcross_r <= {(AW+1){1'b0}};
            rempty_r <= 1'b1;
        end else begin
            rbin_r   <= rbin_nxt;
            rcross_r <= rbin_nxt;
            rempty_r <= rempty_nxt;
        end
    end

    assign rdata  = mem[rbin_r[AW-1:0]];
    assign rempty = rempty_r;

    // -------------------------------------------------- pointer CDC (2 flops)
    sync2ff #(
        .WIDTH   (AW + 1),
        .RST_VAL (1'b0)
    ) u_sync_w2r (
        .clk   (rclk),
        .rst_n (rrst_n),
        .d     (wcross_r),
        .q     (wcross_sync)
    );

    sync2ff #(
        .WIDTH   (AW + 1),
        .RST_VAL (1'b0)
    ) u_sync_r2w (
        .clk   (wclk),
        .rst_n (wrst_n),
        .d     (rcross_r),
        .q     (rcross_sync)
    );

endmodule
