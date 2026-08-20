// ---------------------------------------------------------------------------
// domain_b_onehot - domain_b with state_r re-encoded binary -> one-hot.
//
// SlackSmith transform: fsm_reencode(module=domain_b, fsm=state_r,
//                                     encoding=onehot)
// Branch 4 (mapped-state equivalence) per the transform library design doc.
//
// PRECONDITION P2 ("state bits fan out only to next-state/output logic, not
// to a module output") FAILS for domain_b's raw state_r: a mechanical Yosys
// fanin-cone check (`select domain_b/status_r %ci*`) confirms state_r is in
// status_r's fanin cone -- status_b[3:0] exposes the raw encoding today.
//
// Applying the transform correctly therefore requires more than swapping the
// register width: status_r must re-derive the ORIGINAL 4-bit binary value
// from the new one-hot state, via the decode() function below, so external
// behaviour is bit-exact. Everything else in this module (payload_r, acc_r,
// lfsr_r, retry_r, b2c_r, a2b_rd_en, b2c_ctrl) is untouched -- none of it
// depends on the state encoding.
//
// The same decode() logic is reused, unmodified, as the state-mapping
// invariant asserted in the formal obligation (see
// experiments/fsm_reencode/miter_mapped.sv), so the RTL fix and the proof
// cannot silently drift apart -- one function, two consumers.
// ---------------------------------------------------------------------------
module domain_b_onehot_fv (
    output wire [3:0] dbg_state,   // formal-only tap, added by the wrapper, zero effect on behaviour
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,

    output wire        a2b_rd_en,
    input  wire [15:0] a2b_rdata,
    input  wire        a2b_empty,

    output wire        b2c_ctrl,

    output wire [7:0]  status
);

    // one-hot bit positions, same numbering as the original binary encoding
    // (S_IDLE was 4'd0 -> bit 0, S_FETCH was 4'd1 -> bit 1, etc.) so decode()
    // is a plain "which bit is set" priority encoder with no remapping.
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

    // decode_state: one-hot state -> the original 4-bit binary value.
    // Priority encoder; safe because state_r is one-hot by construction
    // (reset to exactly one bit set, every assignment below sets exactly
    // one bit). Defined once in decode_state.vh and included verbatim here
    // and in the formal miter -- one function, two consumers, no drift.
`include "decode_state.vh"

    // next-state / output decode - identical structure to domain_b.v, only
    // the state test/assignment syntax changes (bit test instead of value
    // compare, one-hot literal instead of binary literal).
    always @(*) begin
        nstate  = state_r;
        rd_en   = 1'b0;
        ld_pl   = 1'b0;
        do_acc  = 1'b0;
        do_emit = 1'b0;
        clr_ret = 1'b0;
        inc_ret = 1'b0;

        if (state_r[S_IDLE]) begin
            if (!a2b_empty) begin
                nstate = 10'b0;
                nstate[S_FETCH] = 1'b1;
            end
        end else if (state_r[S_FETCH]) begin
            if (!a2b_empty) begin
                rd_en  = 1'b1;
                ld_pl  = 1'b1;
                nstate = 10'b0;
                nstate[S_WAIT] = 1'b1;
            end else begin
                nstate = 10'b0;
                nstate[S_IDLE] = 1'b1;
            end
        end else if (state_r[S_WAIT]) begin
            nstate = 10'b0;
            nstate[S_DECODE] = 1'b1;
        end else if (state_r[S_DECODE]) begin
            nstate = 10'b0;
            if (payload_r[15])
                nstate[S_ERR] = 1'b1;
            else
                nstate[S_EXEC1] = 1'b1;
        end else if (state_r[S_EXEC1]) begin
            nstate = 10'b0;
            nstate[S_EXEC2] = 1'b1;
        end else if (state_r[S_EXEC2]) begin
            nstate = 10'b0;
            nstate[S_ACCUM] = 1'b1;
        end else if (state_r[S_ACCUM]) begin
            do_acc = 1'b1;
            nstate = 10'b0;
            nstate[S_EMIT] = 1'b1;
        end else if (state_r[S_EMIT]) begin
            do_emit = 1'b1;
            clr_ret = 1'b1;
            nstate  = 10'b0;
            nstate[S_HOLD] = 1'b1;
        end else if (state_r[S_HOLD]) begin
            nstate = 10'b0;
            if (a2b_empty)
                nstate[S_IDLE] = 1'b1;
            else
                nstate[S_FETCH] = 1'b1;
        end else if (state_r[S_ERR]) begin
            inc_ret = 1'b1;
            nstate  = 10'b0;
            if (retry_r == 8'hFF)
                nstate[S_IDLE] = 1'b1;
            else
                nstate[S_HOLD] = 1'b1;
        end else begin
            // unreachable if state_r is truly one-hot; defensive default
            nstate = 10'b0;
            nstate[S_IDLE] = 1'b1;
        end
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

    // ---------------------------------------------------- status on raw clk
    // Re-derives the ORIGINAL binary state value via decode(), so status_b
    // is bit-exact against domain_b.v despite the internal encoding change.
    reg [7:0] status_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            status_r <= 8'd0;
        else
            status_r <= {b2c_r, a2b_empty, acc_r[1:0], decode_state(state_r)};
    end

    assign status = status_r;
    assign dbg_state = decode_state(state_r);   // formal-only tap, same function as status uses

endmodule
