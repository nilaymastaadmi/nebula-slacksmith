// ---------------------------------------------------------------------------
// domain_b_onehot_parallel - domain_b_onehot with the next-state decode
// flattened from a 10-level if/else-if priority chain into direct
// sum-of-products per output bit.
//
// SlackSmith transform: mux_priority_to_parallel(module=domain_b_onehot,
//                                                  mux_chain=next-state decode)
// Branch 1 (latency-preserving, combinational) per the transform library
// design doc. k=0.
//
// This transform is ONLY eligible because the previous one made it so:
// fsm_reencode(domain_b, state_r, onehot) proved state_r is genuinely
// one-hot for all time after reset (PDR, experiments/fsm_reencode/), so the
// original if/else-if chain's mutual-exclusivity is no longer a coincidence
// of program order, it is a proven invariant. That is what makes the
// flagship precondition from the design doc -- pairwise mutual exclusivity
// of the select conditions -- something that can be PROVEN rather than
// merely hoped, and is why this transform is picked second, not first: it
// composes with the prior one.
//
// The transition table below was derived by hand from domain_b_onehot.v's
// exact if/else-if chain (every branch read and transcribed, not
// paraphrased) before this file was written:
//
//   from S_IDLE:   !a2b_empty -> S_FETCH         a2b_empty -> S_IDLE (self)
//   from S_FETCH:  !a2b_empty -> S_WAIT (+rd_en,ld_pl)   a2b_empty -> S_IDLE
//   from S_WAIT:   always -> S_DECODE
//   from S_DECODE: payload_r[15] -> S_ERR   else -> S_EXEC1
//   from S_EXEC1:  always -> S_EXEC2
//   from S_EXEC2:  always -> S_ACCUM
//   from S_ACCUM:  always -> S_EMIT (+do_acc)
//   from S_EMIT:   always -> S_HOLD (+do_emit, clr_ret)
//   from S_HOLD:   a2b_empty -> S_IDLE   else -> S_FETCH
//   from S_ERR:    retry_r==8'hFF -> S_IDLE (+inc_ret)   else -> S_HOLD (+inc_ret)
//
// PRECONDITION, stated explicitly rather than hidden in the SAT check alone:
// this parallel form is bit-exact against domain_b_onehot ONLY when state_r
// is one-hot. It is NOT bit-exact over the full 10-bit input space: for a
// MULTI-HOT state_r (e.g. S_IDLE and S_FETCH both set, which cannot occur in
// this design's real operation but is not excluded by the bit width alone),
// the original chain's program-order priority picks S_IDLE's transition and
// silently ignores S_FETCH; this parallel form ORs both contributions
// together instead, which can produce a different (and, for a genuinely
// illegal input, equally meaningless) result. The all-zero case is handled
// identically on purpose (see the extra term on nstate[S_IDLE] below,
// mirroring the original's defensive catch-all) because that one is free;
// the multi-hot case is not free to close without reintroducing priority
// logic, which would defeat the point of parallelizing. The formal
// obligation for this transform is therefore explicitly SCOPED to the
// one-hot subspace -- see experiments/mux_priority_to_parallel/NOTES.md for
// both the unscoped EQY run (expected and confirmed to find a real
// counterexample at an illegal multi-hot input) and the scoped SBY proof
// (assume one-hot, which is the physically relevant claim, and which PDR
// discharges unbounded).
// ---------------------------------------------------------------------------
module domain_b_onehot_parallel (
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,

    output wire        a2b_rd_en,
    input  wire [15:0] a2b_rdata,
    input  wire        a2b_empty,

    output wire        b2c_ctrl,

    output wire [7:0]  status
);

    localparam S_IDLE   = 0,
               S_FETCH  = 1,
               S_WAIT   = 2,
               S_DECODE = 3,
               S_EXEC1  = 4,
               S_EXEC2  = 5,
               S_ACCUM  = 6,
               S_EMIT   = 7,
               S_HOLD   = 8,
               S_ERR    = 9;

    reg  [9:0] state_r;
    reg [15:0] payload_r;
    reg [15:0] acc_r;
    reg [15:0] lfsr_r;
    reg  [7:0] retry_r;
    reg        b2c_r;

    reg  [9:0] nstate;
    reg        rd_en;
    reg        ld_pl;
    reg        do_acc;
    reg        do_emit;
    reg        clr_ret;
    reg        inc_ret;

`include "decode_state.vh"

    // next-state / output decode - parallel sum-of-products form. Every
    // output bit is a direct OR of (predecessor-state-bit AND condition)
    // terms, derived from the transition table above. No nested if/else,
    // no priority evaluation -- every term evaluates independently and at
    // most one is true at a time, given state_r is one-hot (the scoped
    // precondition this transform relies on).
    always @(*) begin
        nstate[S_IDLE]   = (state_r[S_IDLE]  &  a2b_empty)
                          | (state_r[S_FETCH] &  a2b_empty)
                          | (state_r[S_HOLD]  &  a2b_empty)
                          | (state_r[S_ERR]   & (retry_r == 8'hFF))
                          | (state_r == 10'b0);   // all-zero recovery, matches
                                                   // the original's defensive
                                                   // catch-all -- free to keep
                                                   // bit-exact, no priority
                                                   // logic needed for this case
        nstate[S_FETCH]  = (state_r[S_IDLE] & ~a2b_empty)
                          | (state_r[S_HOLD] & ~a2b_empty);
        nstate[S_WAIT]   = (state_r[S_FETCH] & ~a2b_empty);
        nstate[S_DECODE] = state_r[S_WAIT];
        nstate[S_EXEC1]  = state_r[S_DECODE] & ~payload_r[15];
        nstate[S_EXEC2]  = state_r[S_EXEC1];
        nstate[S_ACCUM]  = state_r[S_EXEC2];
        nstate[S_EMIT]   = state_r[S_ACCUM];
        nstate[S_HOLD]   = state_r[S_EMIT]
                          | (state_r[S_ERR] & (retry_r != 8'hFF));
        nstate[S_ERR]    = state_r[S_DECODE] & payload_r[15];

        rd_en   = state_r[S_FETCH] & ~a2b_empty;
        ld_pl   = state_r[S_FETCH] & ~a2b_empty;
        do_acc  = state_r[S_ACCUM];
        do_emit = state_r[S_EMIT];
        clr_ret = state_r[S_EMIT];
        inc_ret = state_r[S_ERR];
    end

    always @(posedge clk_div or negedge rst_n) begin
        if (!rst_n) begin
            state_r   <= 10'b0;
            state_r[S_IDLE] <= 1'b1;
            payload_r <= 16'd0;
            acc_r     <= 16'd0;
            lfsr_r    <= 16'hACE1;
            retry_r   <= 8'd0;
            b2c_r     <= 1'b0;
        end else begin
            state_r <= nstate;
            lfsr_r  <= {lfsr_r[14:0],
                        lfsr_r[15] ^ lfsr_r[13] ^ lfsr_r[12] ^ lfsr_r[10]};

            if (ld_pl)
                payload_r <= a2b_rdata;

            if (do_acc)
                acc_r <= acc_r + payload_r + lfsr_r;

            if (do_emit)
                b2c_r <= ~b2c_r;

            if (clr_ret)
                retry_r <= 8'd0;
            else if (inc_ret)
                retry_r <= retry_r + 8'd1;
        end
    end

    assign a2b_rd_en = rd_en;
    assign b2c_ctrl  = b2c_r;

    reg [7:0] status_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            status_r <= 8'd0;
        else
            status_r <= {b2c_r, a2b_empty, acc_r[1:0], decode_state(state_r)};
    end

    assign status = status_r;

endmodule
