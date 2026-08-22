// ---------------------------------------------------------------------------
// domain_a_clamped_pipelined - domain_a_clamped_comb with the clamp compare
// pipelined: registered on clk instead of feeding cap_r combinationally.
//
// SlackSmith transform: pipeline_cut_rigid(module=domain_a, cut_after=
//   clamp_compare, k=1). Precondition P1 (design doc): every path from the
// cut to any consumer crosses it exactly once -- clamped_r has exactly one
// consumer (cap_r) and clamp_valid_r has exactly one consumer (cap_v_r), so
// this holds by construction, not by inspection alone. Precondition P4
// (rigid interface): domain_a has no valid/ready handshake on any port --
// valid_in is a one-way strobe into the module, not part of a bidirectional
// protocol -- confirmed by the same lexical/structural criteria the
// interface classifier (experiments/classify/) already established.
//
// The new register pair (clamped_r, clamp_valid_r) mirrors the EXISTING
// valid_r -> prod_valid_r pattern exactly: one more data register, one more
// paired valid register, same reset values, same unconditional update every
// cycle. This is deliberate -- the transform reuses the module's own idiom
// rather than introducing a new one.
//
// Everything from cap_r onward (the accumulate loop, cnt_r/ctrl_r window
// logic, result_r, a2b_wr_en/wdata) is byte-for-byte unchanged from
// domain_a.v: this transform is local to the clk-domain front end and does
// not touch the A->B or E->A FIFO protocols at all.
// ---------------------------------------------------------------------------
module domain_a_clamped_pipelined (
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

    // the pipeline cut: clamp compare registered on clk, one cycle after
    // scaled_r, instead of feeding cap_r in the same cycle it becomes valid.
    reg  [15:0] clamped_r;
    reg         clamp_valid_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            clamped_r     <= 16'd0;
            clamp_valid_r <= 1'b0;
        end else begin
            clamped_r     <= (scaled_r > CLAMP_MAX) ? CLAMP_MAX : scaled_r;
            clamp_valid_r <= prod_valid_r;
        end
    end

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
            cap_r   <= clamped_r;
            cap_v_r <= clamp_valid_r;
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

endmodule
