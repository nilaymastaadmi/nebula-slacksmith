// Mapped-state miter: domain_b_onehot (re-encoded) against domain_b (golden).
//
//   Transform:   fsm_reencode(module=domain_b, fsm=state_r, encoding=onehot)
//   Obligation:  branch 4, mapped-state equivalence (design doc S2).
//
// k=0 here -- re-encoding is latency-preserving, so unlike toy_miter/ there
// is no output padding. The obligation instead needs a STATE-MAPPING
// invariant, because dsec cannot find one on its own: measured directly in
// experiments/fsm_reencode/NOTES.md, bare `dsec` reports NOT EQUIVALENT in
// 0.08s with no hint (register correspondence is destroyed by construction --
// that is the entire point of re-encoding).
//
// This miter instantiates domain_b_fv / domain_b_onehot_fv, not the real
// domain_b / domain_b_onehot. The _fv wrappers are exact copies plus ONE
// added output port (dbg_state) that taps the internal state register --
// domain_b_fv taps it raw, domain_b_onehot_fv taps it through decode_state()
// (the same function status_r uses). That is the whole difference; no other
// line changed. This exists because Yosys's -formal frontend does not
// support reading a submodule instance's internal signals by hierarchical
// reference (confirmed directly: an earlier version of this file tried
// `u_opt.state_r` and Yosys silently treated it as an undriven free wire,
// which made the very first BMC run fail against garbage, not against the
// real state -- caught only because the frontend also warned "implicitly
// declared" / "has no driver" on the same lines). Comparing two ordinary
// top-level output ports avoids that failure mode entirely. The REAL
// deliverable RTL, domain_b.v and domain_b_onehot.v, is untouched by any of
// this and is what actually gets synthesized and timed.
//
// decode_state() itself is still a single source of truth: domain_b_onehot.v,
// domain_b_onehot_fv.v and this miter all `include "decode_state.vh"`.
//
// Two things are ASSUMED rather than proved, stated explicitly:
//
//   1. Reset alignment. Both instances share rst_n, so they leave reset on
//      the same cycle. `initial assume (!rst_n)` pins the BMC base case to
//      start in reset; the k-induction step begins from an arbitrary state,
//      which is exactly why state_inv has to be independently inductive
//      (see below) rather than riding on the reset-alignment assumption.
//   2. state_r is genuinely one-hot in domain_b_onehot_fv. It resets to a
//      single set bit and every assignment in its next-state block sets
//      exactly one bit, so this holds by construction -- not re-derived
//      here, only relied on.
//
// state_inv is asserted as its own property, separately from the three
// output-matching properties, because SymbiYosys's k-induction step can use
// any currently-holding assertion as a strengthening lemma for the others.
// If state_inv is independently inductive (plausible: both machines see the
// same inputs and reset together, so the mapping should hold one step ahead
// whenever it holds now), it is what lets the output properties close by
// induction even though they would not close alone -- unhinted dsec already
// proved that much. Report each property's result separately; do not fold
// state_inv's outcome into whether the transform is accepted.

module miter_mapped (
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,
    input  wire [15:0] a2b_rdata,
    input  wire        a2b_empty
);

    wire        ref_rd_en, opt_rd_en;
    wire        ref_ctrl,  opt_ctrl;
    wire [7:0]  ref_status, opt_status;
    wire [3:0]  ref_dbg_state, opt_dbg_state;

    domain_b_fv u_ref (
        .dbg_state (ref_dbg_state),
        .clk       (clk),
        .clk_div   (clk_div),
        .rst_n     (rst_n),
        .a2b_rd_en (ref_rd_en),
        .a2b_rdata (a2b_rdata),
        .a2b_empty (a2b_empty),
        .b2c_ctrl  (ref_ctrl),
        .status    (ref_status)
    );

    domain_b_onehot_fv u_opt (
        .dbg_state (opt_dbg_state),
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
            state_inv:   assert (ref_dbg_state == opt_dbg_state);
            rd_en_match: assert (ref_rd_en == opt_rd_en);
            ctrl_match:  assert (ref_ctrl  == opt_ctrl);
        end
    end

    always @(posedge clk) begin
        if (rst_n)
            status_match: assert (ref_status == opt_status);
    end
`endif

endmodule
