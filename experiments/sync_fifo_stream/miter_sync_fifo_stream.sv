// Stream equivalence: sync_fifo_pipelined vs sync_fifo.
//
// Same technique as experiments/vr_miter/miter_vr_stream.sv, reused not
// re-derived: anyconst index selects one transaction, each side latches
// its Nth output independently, values must match once both have one.
//
// Two changes from the MAC case, both required by a FIFO's shape:
//
// 1. Lockstep applies to WRITES, not a single combined transaction. Both
//    designs must see the identical accepted-write sequence, or an
//    observed difference could come from the input diverging rather than
//    the transform. winc_real fires only when neither side is full.
//    sync_fifo_pipelined has strictly more capacity (DEPTH+1 vs DEPTH), so
//    an unconditional winc would let it accept writes sync_fifo rejects --
//    exactly the divergence lockstep exists to prevent.
//
// 2. rinc is shared directly to both sides, unconditionally -- mirroring
//    vr_miter's own out_ready handling exactly. Output-side backpressure
//    does not need lockstepping: unlike wfull, rempty differing between
//    the two designs is expected (that is the capacity difference doing
//    its job), not a hazard to the input-sequence argument.

module miter_sync_fifo_stream #(
    parameter DW = 8,
    parameter AW = 3
) (
    input wire            clk,
    input wire            rst_n,
    input wire            winc_raw,
    input wire [DW-1:0]   wdata,
    input wire            rinc
);
    wire ref_wfull, opt_wfull;
    wire ref_rempty, opt_rempty;
    wire [DW-1:0] ref_rdata, opt_rdata;

    wire winc_real = winc_raw && !ref_wfull && !opt_wfull;

    sync_fifo #(.DW(DW), .AW(AW)) u_ref (
        .clk(clk), .rst_n(rst_n),
        .winc(winc_real), .wdata(wdata), .wfull(ref_wfull),
        .rinc(rinc), .rdata(ref_rdata), .rempty(ref_rempty)
    );

    sync_fifo_pipelined #(.DW(DW), .AW(AW)) u_opt (
        .clk(clk), .rst_n(rst_n),
        .winc(winc_real), .wdata(wdata), .wfull(opt_wfull),
        .rinc(rinc), .rdata(opt_rdata), .rempty(opt_rempty)
    );

    wire ref_fire = !ref_rempty && rinc;
    wire opt_fire = !opt_rempty && rinc;

    (* anyconst *) reg [3:0] nsel;

    reg [3:0]   ref_cnt, opt_cnt;
    reg [DW-1:0] ref_lat, opt_lat;
    reg         ref_got, opt_got;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ref_cnt <= 4'd0; opt_cnt <= 4'd0;
            ref_got <= 1'b0; opt_got <= 1'b0;
            ref_lat <= {DW{1'b0}}; opt_lat <= {DW{1'b0}};
        end else begin
            if (ref_fire) begin
                if (ref_cnt == nsel && !ref_got) begin ref_lat <= ref_rdata; ref_got <= 1'b1; end
                ref_cnt <= ref_cnt + 4'd1;
            end
            if (opt_fire) begin
                if (opt_cnt == nsel && !opt_got) begin opt_lat <= opt_rdata; opt_got <= 1'b1; end
                opt_cnt <= opt_cnt + 4'd1;
            end
        end
    end

`ifdef FORMAL
    initial assume (!rst_n);

    always @(posedge clk) begin
        if (rst_n && ref_got && opt_got)
            stream_match: assert (ref_lat == opt_lat);
    end

    // Vacuity check, added after mutation testing showed it was needed:
    // stream_match only fires once BOTH ref_got and opt_got are true. A
    // design that never completes any transaction (opt_fire never true)
    // satisfies stream_match vacuously forever -- confirmed directly, not
    // theorized: a mutant reproducing sync_fifo_pipelined's own documented
    // stuck-at-reset-empty bug (rempty_core_r gated by core_avail instead
    // of updated unconditionally) proved PASS in 0 seconds, because the
    // guard condition ref_got && opt_got was never reachable. cover proves
    // the guard condition itself is reachable, which assert alone cannot:
    // an unreachable assert guard is trivially unfalsifiable and PDR/BMC
    // report that as a pass with no warning, so the absence of a cover
    // failure is the only signal separating a real proof from a vacuous
    // one. Every stream-equivalence proof in this project from this point
    // needs both.
    cover_reachable: cover property (ref_got && opt_got);
`endif
endmodule
