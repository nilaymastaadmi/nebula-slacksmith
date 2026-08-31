// ---------------------------------------------------------------------------
// sync_fifo_pipelined - sync_fifo with the read side split into a core
// array plus a pipelined output register, giving one extra word of real
// capacity (DEPTH+1 total) via the same two-stage forward-flow pattern
// experiments/vr_miter/mac_vr_opt.v already proved correct.
//
// SlackSmith transform: pipeline_cut_elastic(module=sync_fifo,
//   cut_after=read_data_mux, k=1). Branch 3 (stream equivalence) per the
// transform library design doc -- elastic interface (real wfull/rempty
// back-pressure), so a k-padded miter is the WRONG obligation here, not
// merely an alternative one: see experiments/vr_miter/NOTES.md, where the
// identical obligation on the identical class of design (two-stage
// forward-flow vs single-stage) was refuted in 0 seconds against a
// correct transform. Reused here rather than re-derived: the "extra
// headroom via an output register with s1_ready = !s1_valid || s2_ready
// -style forwarding" IS mac_vr_opt's own mechanism, applied to a FIFO's
// read side instead of a MAC's single-item pipeline.
//
// Why this design and not a bolted-on overflow register: an earlier design
// attempt (adding a single overflow register triggered whenever the core
// looked full-but-not-yet-externally-reported) needed a "promotion" step to
// move that overflow item back into the core array once room appeared --
// and gets the FIFO ordering WRONG if a new external write can claim the
// freed core slot before promotion happens, since the overflow item is
// chronologically OLDER and must be read out first. That is a real design
// hazard, caught during design rather than after the fact, and it is
// exactly why this design routes the extra capacity through an always-
// eligible output register instead of a specially-triggered overflow path:
// the "core forwards into the output register whenever the output register
// has room" rule has no priority conflict to get wrong, because writes
// (into mem[] at wbin_r) and the core-to-output forward (reading mem[] at
// rbin_r_core) never target the same address while wfull is honoured, and
// the forward is attempted unconditionally every cycle rather than only in
// a special-cased overflow scenario.
//
// Capacity: DEPTH (core array) + 1 (output register) words, vs sync_fifo's
// DEPTH words -- a genuine capacity difference, not merely a relabeling of
// the same DEPTH words, which is what makes the two designs actually
// diverge under back-pressure rather than being trivially k-padding-
// equivalent.
// ---------------------------------------------------------------------------
module sync_fifo_pipelined #(
    parameter DW = 8,
    parameter AW = 3
) (
    input  wire          clk,
    input  wire          rst_n,

    input  wire          winc,
    input  wire [DW-1:0] wdata,
    output wire          wfull,

    input  wire          rinc,
    output wire [DW-1:0] rdata,
    output wire          rempty
);

    localparam DEPTH = (1 << AW);

    reg [DW-1:0] mem [0:DEPTH-1];

    // ---- write side: unchanged in spirit from sync_fifo, but compares
    // against the CORE's own read pointer (rbin_r_core), not against any
    // notion of external consumption -- a write is safe as soon as the
    // core has forwarded its front word onward, even if the external
    // consumer has not popped anything yet. That is the extra headroom.
    reg [AW:0] wbin_r;
    reg        wfull_r;
    wire        wen      = winc & ~wfull_r;
    wire [AW:0] wbin_nxt = wbin_r + {{AW{1'b0}}, wen};

    // ---- core read pointer: tracks how much has been pulled from the
    // array into the output register, not how much the external consumer
    // has popped.
    reg [AW:0] rbin_r_core;
    reg        rempty_core_r;

    wire core_avail = ~rempty_core_r;

    // ---- output register: the extra word of headroom, and the read-side
    // half of the transform (k=1 relative to sync_fifo's combinational
    // rdata).
    reg [DW-1:0] rdata_r;
    reg          rdata_valid_r;

    wire s2_ready = ~rdata_valid_r | rinc;

    // FIX (found by simulation, not assumed correct): rempty_core_r must be
    // recomputed EVERY cycle, unconditionally, exactly like wfull_r is --
    // it is a continuous function of "how much has been written vs pulled
    // into the output register," not a side effect of a successful pull.
    // The original version only updated rempty_core_r INSIDE the
    // `if (core_avail)` branch, which meant a core that had never yet
    // pulled anything could never transition out of "empty" in the first
    // place after a fresh write -- confirmed directly: the sanity
    // simulation showed rempty staying high forever after successful
    // writes, an infinite loop in the testbench's drain phase, not a
    // subtle timing skew. rbin_r_core itself still only ADVANCES when a
    // pull actually happens (below); only its EMPTINESS is unconditional.
    // Look-ahead against wbin_nxt (not wbin_r), matching wfull_nxt's own
    // look-ahead style, so a write and the core noticing it happen in the
    // same cycle rather than the core lagging by an extra, unnecessary one.
    wire [AW:0] rbin_core_nxt   = rbin_r_core + {{AW{1'b0}}, (s2_ready & core_avail)};
    wire        rempty_core_nxt = (rbin_core_nxt == wbin_nxt);
    wire        wfull_nxt       = (wbin_nxt == {~rbin_r_core[AW], rbin_r_core[AW-1:0]});

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wbin_r        <= {(AW+1){1'b0}};
            wfull_r       <= 1'b0;
            rbin_r_core   <= {(AW+1){1'b0}};
            rempty_core_r <= 1'b1;
            rdata_r       <= {DW{1'b0}};
            rdata_valid_r <= 1'b0;
        end else begin
            wbin_r        <= wbin_nxt;
            wfull_r       <= wfull_nxt;
            rempty_core_r <= rempty_core_nxt;   // unconditional -- the fix

            // core -> output register forward, attempted every cycle the
            // output register has room. Mirrors mac_vr_opt.v's
            // `if (s2_ready) out_valid <= s1_valid;` exactly: when
            // s2_ready, the output register's next valid state simply
            // becomes whatever the core currently has available, whether
            // that is 1 (forward a word) or 0 (nothing to forward, output
            // register correctly goes empty).
            if (s2_ready) begin
                rdata_valid_r <= core_avail;
                if (core_avail) begin
                    rdata_r     <= mem[rbin_r_core[AW-1:0]];
                    rbin_r_core <= rbin_core_nxt;   // advances only when a pull happens; emptiness itself is tracked unconditionally above
                end
            end
        end
    end

    always @(posedge clk)
        if (wen)
            mem[wbin_r[AW-1:0]] <= wdata;

    assign wfull  = wfull_r;
    assign rdata  = rdata_r;
    assign rempty = ~rdata_valid_r;

endmodule
