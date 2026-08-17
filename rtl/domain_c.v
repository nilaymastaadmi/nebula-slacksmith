// ---------------------------------------------------------------------------
// domain_c - UART-transmitter-like shift block.
//
//   clk      : clk_c          (primary, asynchronous to all other domains)
//   clk_div  : clk_c / 4      (generated clock, 50% duty)
//
// The shift engine, baud counter and tx output flop all run on the /4
// generated clock.  The B -> C control bit is synchronized by a sync2ff
// clocked by clk_div, i.e. the CDC lands directly on a generated clock -
// deliberate, this is one of the awkward constraints the benchmark exists to
// exercise.  clk itself still clocks real flops: this domain's clkdiv (in
// bench_top) has posedge flops on clk_c, and the tx output is re-registered
// on clk_c so the divided -> primary clock path inside the domain is real.
//
// Crossings owned here:
//   B -> C  control, single-bit, sync2ff (instantiated here, on clk_div)
//   C -> D  data,    write side of a gray-pointer async FIFO (on clk_div)
// ---------------------------------------------------------------------------
module domain_c (
    input  wire       clk,
    input  wire       clk_div,
    input  wire       rst_n,

    // B -> C single-bit control, asynchronous to this domain
    input  wire       b2c_ctrl_async,

    // C -> D data FIFO, write side (clk_div domain)
    output wire       c2d_wr_en,
    output wire [7:0] c2d_wdata,
    input  wire       c2d_full,

    output wire       tx
);

    localparam [7:0] BAUD_DIV = 8'd15;

    // ------------------------------------------- single-bit CDC into clk_div
    wire b2c_sync;

    sync2ff #(
        .WIDTH   (1),
        .RST_VAL (1'b0)
    ) u_b2c_sync (
        .clk   (clk_div),
        .rst_n (rst_n),
        .d     (b2c_ctrl_async),
        .q     (b2c_sync)
    );

    // -------------------------------------------------------- shift engine
    reg        b2c_q;
    reg [9:0]  shift_r;
    reg [3:0]  bitcnt_r;
    reg [7:0]  baud_r;
    reg [7:0]  payload_r;
    reg [7:0]  bytecnt_r;
    reg        busy_r;
    reg        tx_r;
    reg        wr_r;
    reg [7:0]  wdata_r;

    wire b2c_evt = b2c_sync ^ b2c_q;   // toggle-edge detect on the synced bit

    always @(posedge clk_div or negedge rst_n) begin
        if (!rst_n) begin
            b2c_q     <= 1'b0;
            shift_r   <= 10'h3FF;
            bitcnt_r  <= 4'd0;
            baud_r    <= 8'd0;
            payload_r <= 8'd0;
            bytecnt_r <= 8'd0;
            busy_r    <= 1'b0;
            tx_r      <= 1'b1;
            wr_r      <= 1'b0;
            wdata_r   <= 8'd0;
        end else begin
            b2c_q <= b2c_sync;
            wr_r  <= 1'b0;

            if (b2c_evt)
                payload_r <= payload_r + 8'd1;

            if (!busy_r) begin
                if (b2c_evt) begin
                    shift_r  <= {1'b1, payload_r, 1'b0};  // stop, data, start
                    busy_r   <= 1'b1;
                    bitcnt_r <= 4'd0;
                    baud_r   <= 8'd0;
                end
            end else begin
                if (baud_r == BAUD_DIV) begin
                    baud_r  <= 8'd0;
                    tx_r    <= shift_r[0];
                    shift_r <= {1'b1, shift_r[9:1]};

                    if (bitcnt_r == 4'd9) begin
                        busy_r    <= 1'b0;
                        bytecnt_r <= bytecnt_r + 8'd1;
                        if (!c2d_full) begin
                            wr_r    <= 1'b1;
                            wdata_r <= bytecnt_r ^ payload_r;
                        end
                    end else begin
                        bitcnt_r <= bitcnt_r + 4'd1;
                    end
                end else begin
                    baud_r <= baud_r + 8'd1;
                end
            end
        end
    end

    assign c2d_wr_en = wr_r;
    assign c2d_wdata = wdata_r;

    // ------------------------------------------- tx output flop on raw clk_c
    // clk_div -> clk generated-to-primary path inside the domain
    reg tx_out_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            tx_out_r <= 1'b1;
        else
            tx_out_r <= tx_r;
    end

    assign tx = tx_out_r;

endmodule
