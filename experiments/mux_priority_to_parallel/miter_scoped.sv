// Scoped equivalence miter: domain_b_onehot_parallel (mux_priority_to_parallel
// applied) against domain_b_onehot (golden).
//
//   Transform:  mux_priority_to_parallel(module=domain_b_onehot,
//                                         mux_chain=next-state decode)
//   Obligation: branch 1 (combinational, latency-preserving), k=0.
//
// The unscoped EQY comparison (parallel.eqy, see logs/) correctly found this
// pair NOT equivalent over the full 10-bit state_r input space -- 10 of 24
// partitions fail, all downstream of nstate, exactly where the parallel
// form's OR-of-products diverges from the original's program-order priority
// on an illegal MULTI-HOT state_r (impossible in real operation, not
// excluded by the bit width alone). That result is real and correctly
// reported in logs/, not discarded.
//
// The claim that matters is narrower and is what this miter proves: under
// the precondition that state_r is one-hot, the two designs are equivalent.
// The precondition is stated as explicit ASSUMES below, in the manual form
// (s != 0) && ((s & (s-1)) == 0), on BOTH instances, because the claim is
// symmetric: if either design's state left the one-hot subspace the
// comparison would stop being meaningful for either side. CORRECTION
// 2026-08-31 (audit finding F1): this header originally said one-hotness
// was "proven separately, unbounded, in experiments/fsm_reencode/". That
// was drift -- the fsm_reencode proof established decoded-state
// correspondence, which cannot distinguish one-hot from multi-hot. The
// assumption used here is now actually discharged, unbounded, for both
// instantiated designs in experiments/onehot_invariant/.
//
// Reused from experiments/fsm_reencode/: the _fv wrapper pattern (tap an
// internal register to a real port), because Yosys's -formal frontend does
// not support reading a submodule instance's internal signal by
// hierarchical reference -- confirmed there, not re-discovered here.

module miter_scoped (
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,
    input  wire [15:0] a2b_rdata,
    input  wire        a2b_empty
);

    wire        ref_rd_en, opt_rd_en;
    wire        ref_ctrl,  opt_ctrl;
    wire [7:0]  ref_status, opt_status;
    wire [9:0]  ref_state,  opt_state;

    domain_b_onehot_raw_fv u_ref (
        .dbg_state (ref_state),
        .clk       (clk),
        .clk_div   (clk_div),
        .rst_n     (rst_n),
        .a2b_rd_en (ref_rd_en),
        .a2b_rdata (a2b_rdata),
        .a2b_empty (a2b_empty),
        .b2c_ctrl  (ref_ctrl),
        .status    (ref_status)
    );

    domain_b_onehot_parallel_fv u_opt (
        .dbg_state (opt_state),
        .clk       (clk),
        .clk_div   (clk_div),
        .rst_n     (rst_n),
        .a2b_rd_en (opt_rd_en),
        .a2b_rdata (a2b_rdata),
        .a2b_empty (a2b_empty),
        .b2c_ctrl  (opt_ctrl),
        .status    (opt_status)
    );

`ifdef FORMAL
    initial assume (!rst_n);

    always @(posedge clk_div) begin
        if (rst_n) begin
            // the scoped precondition, stated explicitly, not implicit
            assume (ref_state != 10'b0 && (ref_state & (ref_state - 1'b1)) == 10'b0);
            assume (opt_state != 10'b0 && (opt_state & (opt_state - 1'b1)) == 10'b0);

            state_match: assert (ref_state  == opt_state);
            rd_en_match: assert (ref_rd_en  == opt_rd_en);
            ctrl_match:  assert (ref_ctrl   == opt_ctrl);
        end
    end

    always @(posedge clk) begin
        if (rst_n)
            status_match: assert (ref_status == opt_status);
    end
`endif

endmodule
