// One-hot invariant proof for domain_b_onehot and domain_b_onehot_parallel.
//
// Exists because of audit finding F1 (2026-08-31): two write-ups and one
// commit message claimed fsm_reencode's PDR proof "proved state_r is
// genuinely one-hot". It did not. That proof established decoded-state
// correspondence through decode_state(), a priority encoder that maps many
// multi-hot states onto the same values as legal states, so it cannot
// distinguish one-hot from multi-hot. One-hotness rested on a syntactic
// construction argument (reset sets exactly one bit, every assignment sets
// exactly one bit), never formally discharged. mux_priority_to_parallel's
// scoped equivalence proof ASSUMES one-hot on both designs, so until this
// file, the composition chain had an undischarged link.
//
// This harness discharges it: both designs instantiated independently,
// inputs free (over-general, therefore sound for the real system), assert
// one-hot on the raw 10-bit state tap of each, every clk_div cycle after
// reset. The manual form (s != 0) && ((s & (s-1)) == 0) is used instead of
// $onehot() to avoid any frontend-support question; they are equivalent
// for a 10-bit vector.
//
// The _fv tap wrappers are the same generated-wrapper pattern as every
// other proof in this project (Yosys's -formal frontend cannot read a
// submodule's internal signal hierarchically).

module onehot_check (
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,
    input  wire [15:0] a2b_rdata,
    input  wire        a2b_empty
);

    wire [9:0] oh_state, par_state;

    domain_b_onehot_raw_fv u_onehot (
        .dbg_state (oh_state),
        .clk       (clk),
        .clk_div   (clk_div),
        .rst_n     (rst_n),
        .a2b_rd_en (),
        .a2b_rdata (a2b_rdata),
        .a2b_empty (a2b_empty),
        .b2c_ctrl  (),
        .status    ()
    );

    domain_b_onehot_parallel_fv u_parallel (
        .dbg_state (par_state),
        .clk       (clk),
        .clk_div   (clk_div),
        .rst_n     (rst_n),
        .a2b_rd_en (),
        .a2b_rdata (a2b_rdata),
        .a2b_empty (a2b_empty),
        .b2c_ctrl  (),
        .status    ()
    );

`ifdef FORMAL
    initial assume (!rst_n);

    always @(posedge clk_div) begin
        if (rst_n) begin
            onehot_reencoded: assert (oh_state  != 10'b0 && (oh_state  & (oh_state  - 1'b1)) == 10'b0);
            onehot_parallel:  assert (par_state != 10'b0 && (par_state & (par_state - 1'b1)) == 10'b0);
        end
    end
`endif

endmodule
