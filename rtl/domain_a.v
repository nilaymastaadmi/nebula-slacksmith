// ---------------------------------------------------------------------------
// domain_a - 8-bit MAC datapath.
//
//   clk      : clk_a          (primary, asynchronous to all other domains)
//   clk_div  : clk_a / 2      (generated clock from clkdiv, 50% duty)
//
// Front end (input capture, 8x8 multiply, scale) runs on clk.
// Accumulate / result / FIFO-write stage runs on the /2 generated clock, so
// the divided clock drives real flip-flops and the clk -> clk_div paths are
// genuine source-to-generated-clock timing arcs.
//
// Crossings owned here:
//   E -> A  config data, read side of a gray-pointer async FIFO (on clk)
//   A -> B  result data, write side of a gray-pointer async FIFO (on clk_div)
// ---------------------------------------------------------------------------
module domain_a (
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,

    input  wire [7:0]  data_in,
    input  wire        valid_in,

    // E -> A config FIFO, read side (clk domain)
    output wire        cfg_rd_en,
    input  wire [31:0] cfg_rdata,
    input  wire        cfg_empty,

    // A -> B data FIFO, write side (clk_div domain)
    output wire        a2b_wr_en,
    output wire [15:0] a2b_wdata,
    input  wire        a2b_full,

    output wire [15:0] mac_result
);

    // ------------------------------------------------------------ clk stage
    reg  [7:0]  sample_r;
    reg  [7:0]  coeff_r;
    reg  [7:0]  scale_r;
    reg  [7:0]  ctrl_r;
    reg         valid_r;
    reg         prod_valid_r;
    reg  [15:0] product_r;
    reg  [15:0] scaled_r;

    // rempty is a registered flag inside the FIFO, so this is not a comb loop
    assign cfg_rd_en = ~cfg_empty;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sample_r     <= 8'd0;
            coeff_r      <= 8'd1;
            scale_r      <= 8'd0;
            ctrl_r       <= 8'd7;
            valid_r      <= 1'b0;
            prod_valid_r <= 1'b0;
            product_r    <= 16'd0;
            scaled_r     <= 16'd0;
        end else begin
            valid_r      <= valid_in;
            prod_valid_r <= valid_r;

            if (valid_in)
                sample_r <= data_in;

            if (cfg_rd_en) begin
                coeff_r <= cfg_rdata[7:0];
                scale_r <= cfg_rdata[15:8];
                ctrl_r  <= cfg_rdata[23:16];
            end

            product_r <= sample_r * coeff_r;         // 8 x 8 -> 16
            scaled_r  <= product_r + {8'd0, scale_r};
        end
    end

    // -------------------------------------------------------- clk_div stage
    reg  [15:0] cap_r;
    reg         cap_v_r;
    reg  [31:0] acc_r;
    reg  [7:0]  cnt_r;
    reg  [15:0] result_r;
    reg  [15:0] wdata_r;
    reg         wr_r;

    always @(posedge clk_div or negedge rst_n) begin
        if (!rst_n) begin
            cap_r    <= 16'd0;
            cap_v_r  <= 1'b0;
            acc_r    <= 32'd0;
            cnt_r    <= 8'd0;
            result_r <= 16'd0;
            wdata_r  <= 16'd0;
            wr_r     <= 1'b0;
        end else begin
            cap_r   <= scaled_r;
            cap_v_r <= prod_valid_r;
            wr_r    <= 1'b0;

            if (cap_v_r) begin
                if (cnt_r == ctrl_r) begin
                    cnt_r    <= 8'd0;
                    acc_r    <= {16'd0, cap_r};      // restart the window
                    result_r <= acc_r[15:0];
                    wdata_r  <= acc_r[15:0];
                    wr_r     <= ~a2b_full;
                end else begin
                    cnt_r <= cnt_r + 8'd1;
                    acc_r <= acc_r + {16'd0, cap_r};
                end
            end
        end
    end

    assign a2b_wr_en  = wr_r;
    assign a2b_wdata  = wdata_r;
    assign mac_result = result_r;

endmodule
