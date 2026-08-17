// ---------------------------------------------------------------------------
// domain_e - 16 x 32-bit config/status register file.
//
//   clk      : clk_e          (primary, asynchronous to all other domains)
//   clk_div  : clk_e / 2      (generated clock, 50% duty)
//
// The primary config write port is captured on the raw clk; the register file
// itself and the E->A FIFO write side run on the /2 generated clock.  The
// register array is declared as a reg array but every element is reset from
// the async reset, so it synthesizes to plain reset flops (not a RAM) - this
// keeps the "every flop explicitly reset" rule intact.
//
// Crossings owned here:
//   D -> E  control, single-bit, sync2ff (instantiated here, on clk_div)
//   E -> A  config data, write side of a gray-pointer async FIFO (on clk_div)
// ---------------------------------------------------------------------------
module domain_e (
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,

    input  wire [3:0]  cfg_addr,
    input  wire [31:0] cfg_wdata,
    input  wire        cfg_we,

    // D -> E single-bit control, asynchronous to this domain
    input  wire        d2e_ctrl_async,

    // E -> A config FIFO, write side (clk_div domain)
    output wire        e2a_wr_en,
    output wire [31:0] e2a_wdata,
    input  wire        e2a_full,

    output wire [7:0]  cfg_status
);

    // ---------------------------------------- primary write port on raw clk
    reg [3:0]  addr_r;
    reg [31:0] wdata_r;
    reg        we_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            addr_r  <= 4'd0;
            wdata_r <= 32'd0;
            we_r    <= 1'b0;
        end else begin
            addr_r  <= cfg_addr;
            wdata_r <= cfg_wdata;
            we_r    <= cfg_we;
        end
    end

    // ------------------------------------------- single-bit CDC into clk_div
    wire d2e_sync;

    sync2ff #(
        .WIDTH   (1),
        .RST_VAL (1'b0)
    ) u_d2e_sync (
        .clk   (clk_div),
        .rst_n (rst_n),
        .d     (d2e_ctrl_async),
        .q     (d2e_sync)
    );

    // ------------------------------------------------------- register file
    reg [31:0] cfg_reg [0:15];
    reg [3:0]  rptr_r;
    reg [7:0]  evtcnt_r;
    reg        d2e_q;
    reg        wr_r;
    reg [31:0] wdata_out_r;

    integer i;

    wire       d2e_evt = d2e_sync ^ d2e_q;
    wire [31:0] cfg_rd = cfg_reg[rptr_r];

    always @(posedge clk_div or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 16; i = i + 1)
                cfg_reg[i] <= 32'd0;
            rptr_r      <= 4'd0;
            evtcnt_r    <= 8'd0;
            d2e_q       <= 1'b0;
            wr_r        <= 1'b0;
            wdata_out_r <= 32'd0;
        end else begin
            d2e_q <= d2e_sync;
            wr_r  <= 1'b0;

            if (we_r)
                cfg_reg[addr_r] <= wdata_r;

            if (d2e_evt) begin
                rptr_r   <= rptr_r + 4'd1;
                evtcnt_r <= evtcnt_r + 8'd1;
                if (!e2a_full) begin
                    wr_r        <= 1'b1;
                    wdata_out_r <= cfg_rd;
                end
            end
        end
    end

    assign e2a_wr_en = wr_r;
    assign e2a_wdata = wdata_out_r;

    // -------------------------------------------------- status on raw clk_e
    reg [7:0] status_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            status_r <= 8'd0;
        else
            status_r <= {evtcnt_r[3:0], rptr_r};
    end

    assign cfg_status = status_r;

endmodule
