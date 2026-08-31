// Latency-tolerant miter: domain_a_clamped_pipelined against
// domain_a_clamped_comb, padded with K=1 matched register.
//
//   Transform:   pipeline_cut_rigid(module=domain_a, cut_after=clamp_compare, k=1)
//   Obligation:  branch 2, k-padded miter, unbounded via k-induction/PDR.
//
// This is the SAME recipe as experiments/toy_miter/miter.sv, applied to real
// RTL for the first time this project. No new technique here -- reusing a
// proven one is the point. Only the scope differs, and deliberately: rather
// than comparing domain_a's full output set (mac_result, a2b_wr_en/wdata),
// which would require guessing how many CLK_DIV cycles a 1-CLK-cycle shift
// in the clk-domain front end actually produces at those clk_div-domain
// outputs -- itself dependent on the clk:clk_div phase relationship, the
// exact class of cross-domain assumption this project has been careful not
// to guess at -- the comparison is scoped to the one point where k=1 is
// unambiguous: clamped_w/clamped_r and their paired valid signals, both
// still entirely within the clk domain, before anything crosses to clk_div.
// Everything downstream of that point (cap_r capture, the accumulate loop,
// cnt_r/ctrl_r window logic, result_r, a2b_wr_en/wdata) is byte-for-byte
// identical between the two designs. CORRECTION 2026-08-31 (audit finding
// F2): this header originally went one step further and claimed the
// boundary proof was SUFFICIENT for module-level equivalence ("identical
// logic fed identical inputs at identical relative timing produces
// identical outputs"). That is false, and it was demonstrated by execution,
// not argument: tb_divergence.v in this directory drives both variants with
// identical stimulus and a real /2 divider, and mac_result diverges
// permanently (002a vs 0031). The mechanism: cap_r samples on clk_div at
// half the clk rate, so a 1-clk delay in its driver does not shift the
// captured stream, it selects a DIFFERENT SUBSEQUENCE of it (different
// phase of the stride-2 sampling). The transform is therefore a
// boundary-proven MICROARCHITECTURAL CHANGE, not a proven drop-in
// equivalent of the comb variant. What this miter proves is exactly and
// only what its assertions state: the drivers of cap_r/cap_v_r in the two
// designs are related by the k=1 padding relationship, within the clk
// domain. Decision of record: ~/jarvis-vault/Decisions/
// 2026-08-31-nebula-pipeline-cut-claim-refuted.md.
//
// The _fv wrapper pattern (tap an internal signal to a real port) is reused
// from experiments/fsm_reencode/ and experiments/mux_priority_to_parallel/,
// not re-derived: Yosys's -formal frontend does not support reading a
// submodule instance's internal signal by hierarchical reference.
//
// Two things ASSUMED rather than proved, same discipline as toy_miter/:
//
//   1. Reset alignment. Both instances share rst_n, so `initial assume
//      (!rst_n)` pins the BMC base case to start in reset. `primed` (below)
//      holds the assertion off for the first K=1 cycles after reset, when
//      the padding register has not yet captured a meaningful value.
//   2. Rigid interface. domain_a has no valid/ready handshake anywhere --
//      valid_in is a one-way strobe, not part of a bidirectional protocol --
//      so a fixed K-cycle offset is a sound obligation here. This was
//      checked, not assumed by default: the same lexical/structural
//      criteria the interface classifier (experiments/classify/) uses to
//      distinguish rigid from elastic interfaces both say rigid for
//      domain_a, and there is no back-pressure input anywhere in its
//      port list to suggest otherwise.

module miter_pipeline_domain_a (
    input wire        clk,
    input wire        clk_div,
    input wire        rst_n,
    input wire [7:0]  data_in,
    input wire        valid_in,
    input wire [31:0] cfg_rdata,
    input wire        cfg_empty,
    input wire        a2b_full
);

    wire [15:0] ref_clamped, opt_clamped;
    wire        ref_valid,   opt_valid;

    domain_a_clamped_comb_fv u_ref (
        .dbg_clamped (ref_clamped),
        .dbg_valid   (ref_valid),
        .clk         (clk),
        .clk_div     (clk_div),
        .rst_n       (rst_n),
        .data_in     (data_in),
        .valid_in    (valid_in),
        .cfg_rd_en   (),
        .cfg_rdata   (cfg_rdata),
        .cfg_empty   (cfg_empty),
        .a2b_wr_en   (),
        .a2b_wdata   (),
        .a2b_full    (a2b_full),
        .mac_result  ()
    );

    domain_a_clamped_pipelined_fv u_opt (
        .dbg_clamped (opt_clamped),
        .dbg_valid   (opt_valid),
        .clk         (clk),
        .clk_div     (clk_div),
        .rst_n       (rst_n),
        .data_in     (data_in),
        .valid_in    (valid_in),
        .cfg_rd_en   (),
        .cfg_rdata   (cfg_rdata),
        .cfg_empty   (cfg_empty),
        .a2b_wr_en   (),
        .a2b_wdata   (),
        .a2b_full    (a2b_full),
        .mac_result  ()
    );

    // ---- pad the reference with K=1 matched registers ----
    reg [15:0] ref_clamped_pipe;
    reg        ref_valid_pipe;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ref_clamped_pipe <= 16'd0;
            ref_valid_pipe   <= 1'b0;
        end else begin
            ref_clamped_pipe <= ref_clamped;
            ref_valid_pipe   <= ref_valid;
        end
    end

    // ---- reset alignment: cycles since reset released ----
    reg [3:0] prime;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)         prime <= 4'd0;
        else if (prime < 1) prime <= prime + 4'd1;
    end
    wire primed = (prime >= 1);

`ifdef FORMAL
    initial assume (!rst_n);

    always @(posedge clk) begin
        if (rst_n && primed) begin
            clamped_match: assert (opt_clamped == ref_clamped_pipe);
            valid_match:   assert (opt_valid   == ref_valid_pipe);
        end
    end
`endif

endmodule
