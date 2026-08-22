// ---------------------------------------------------------------------------
// domain_a_clamped_comb - domain_a with a saturating clamp added to the
// multiply-scale front end, computed COMBINATIONALLY (same cycle as
// scaled_r, no new register). This is the REFERENCE for the pipeline_cut
// transform below, not itself the transform: it represents "clamping added,
// latency unchanged" -- a real, honestly-motivated addition (saturating
// output is standard MAC/DSP practice), added specifically because the
// unmodified benchmark has no natural, feed-forward, non-self-looping
// combinational chain to demonstrate a latency-changing transform against.
// Every other candidate in this benchmark (the accumulator, the FSM state,
// the timer's counter) has real feedback and is explicitly ineligible for
// pipeline_cut_rigid per the transform library design doc.
//
// SlackSmith transform under test: pipeline_cut_rigid(module=domain_a,
//   cut_after=clamp_compare, k=1). This file is the k=0 side of that
// obligation; domain_a_clamped_pipelined.v is the k=1 side.
// ---------------------------------------------------------------------------
module domain_a_clamped_comb_fv (
    output wire [15:0] dbg_clamped,
    output wire         dbg_valid,
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,

    input  wire [7:0]  data_in,
    input  wire        valid_in,

    output wire        cfg_rd_en,
    input  wire [31:0] cfg_rdata,
    input  wire        cfg_empty,

    output wire        a2b_wr_en,
    output wire [15:0] a2b_wdata,
    input  wire        a2b_full,

    output wire [15:0] mac_result
);

    localparam [15:0] CLAMP_MAX = 16'hFF00;

    reg  [7:0]  sample_r;
    reg  [7:0]  coeff_r;
    reg  [7:0]  scale_r;
    reg  [7:0]  ctrl_r;
    reg         valid_r;
    reg         prod_valid_r;
    reg  [15:0] product_r;
    reg  [15:0] scaled_r;

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

            product_r <= sample_r * coeff_r;
            scaled_r  <= product_r + {8'd0, scale_r};
        end
    end

    // clamp computed combinationally from scaled_r, feeding cap_r in the
    // SAME cycle scaled_r itself becomes valid -- no cut, no new latency.
    // This is the k=0 reference for the obligation.
    wire [15:0] clamped_w = (scaled_r > CLAMP_MAX) ? CLAMP_MAX : scaled_r;

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
            cap_r   <= clamped_w;
            cap_v_r <= prod_valid_r;
            wr_r    <= 1'b0;

            if (cap_v_r) begin
                if (cnt_r == ctrl_r) begin
                    cnt_r    <= 8'd0;
                    acc_r    <= {16'd0, cap_r};
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
    assign dbg_clamped = clamped_w;
    assign dbg_valid   = prod_valid_r;

endmodule
