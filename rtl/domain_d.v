// ---------------------------------------------------------------------------
// domain_d - reloading timer with two programmable compare values.
//
//   clk      : clk_d          (primary, asynchronous to all other domains)
//   clk_div  : clk_d / 5      (generated clock, TRUE 50% duty via both edges)
//
// cnt_r counts on the /5 generated clock and reloads at cmp0_r, so m0_r is a
// periodic terminal-count pulse rather than a once-ever match.  cmp1_r is an
// intermediate compare inside the period (PWM style).  Both compare values are
// reprogrammed from bytes arriving over the C->D FIFO, and both are kept in
// the low bits so a reprogram always lands inside a reachable count range - a
// free-running counter with a large compare would simply never match.
//
// The output pulse is re-registered on the raw clk.
//
// Crossings owned here:
//   C -> D  data,    read side of a gray-pointer async FIFO (on clk_div)
//   D -> E  control, single-bit toggle launched on clk_div, synchronized
//           into domain E by a sync2ff over there.
// ---------------------------------------------------------------------------
module domain_d (
    input  wire       clk,
    input  wire       clk_div,
    input  wire       rst_n,

    // C -> D data FIFO, read side (clk_div domain)
    output wire       c2d_rd_en,
    input  wire [7:0] c2d_rdata,
    input  wire       c2d_empty,

    // D -> E single-bit control crossing (launched on clk_div)
    output wire       d2e_ctrl,

    output wire       timer_pulse
);

    reg [31:0] cnt_r;
    reg [31:0] cmp0_r;   // period   (counter reloads here)
    reg [31:0] cmp1_r;   // in-period compare
    reg        m0_r;
    reg        m1_r;
    reg        d2e_r;
    reg [7:0]  evt_r;

    // rempty is a registered FIFO flag, so this is not a combinational loop
    assign c2d_rd_en = ~c2d_empty;

    always @(posedge clk_div or negedge rst_n) begin
        if (!rst_n) begin
            cnt_r  <= 32'd0;
            cmp0_r <= 32'h0000_00FF;
            cmp1_r <= 32'h0000_007F;
            m0_r   <= 1'b0;
            m1_r   <= 1'b0;
            d2e_r  <= 1'b0;
            evt_r  <= 8'd0;
        end else begin
            if (cnt_r >= cmp0_r) begin
                cnt_r <= 32'd0;
                m0_r  <= 1'b1;
            end else begin
                cnt_r <= cnt_r + 32'd1;
                m0_r  <= 1'b0;
            end

            m1_r <= (cnt_r == cmp1_r);

            // rdata is valid in the same cycle rd_en is asserted
            if (c2d_rd_en) begin
                cmp0_r <= {20'd0, c2d_rdata, 4'h1};   // period, 1 .. 4081
                cmp1_r <= {24'd0, c2d_rdata};         // always <= cmp0_r
                evt_r  <= evt_r + 8'd1;
            end

            if (m1_r)
                d2e_r <= ~d2e_r;
        end
    end

    assign d2e_ctrl = d2e_r;

    // ---------------------------------------------- output pulse on raw clk
    reg pulse_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            pulse_r <= 1'b0;
        else
            pulse_r <= m0_r | m1_r;
    end

    assign timer_pulse = pulse_r;

endmodule
