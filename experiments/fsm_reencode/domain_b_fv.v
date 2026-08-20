// ---------------------------------------------------------------------------
// domain_b - control FSM (10 states) driving the A->B consumer.
//
//   clk      : clk_b          (primary, asynchronous to all other domains)
//   clk_div  : clk_b / 3      (generated clock, TRUE 50% duty via both edges)
//
// The FSM and datapath run entirely on the /3 generated clock.  The status
// output register runs on the raw clk, giving a generated-clock -> primary
// -clock path inside the domain.
//
// Crossings owned here:
//   A -> B  data,    read side of a gray-pointer async FIFO (on clk_div)
//   B -> C  control, single-bit toggle launched on clk_div, synchronized
//           into domain C by a sync2ff over there.
// ---------------------------------------------------------------------------
module domain_b_fv (
    output wire [3:0] dbg_state,   // formal-only tap, added by the wrapper, zero effect on behaviour
    input  wire        clk,
    input  wire        clk_div,
    input  wire        rst_n,

    // A -> B data FIFO, read side (clk_div domain)
    output wire        a2b_rd_en,
    input  wire [15:0] a2b_rdata,
    input  wire        a2b_empty,

    // B -> C single-bit control crossing (launched on clk_div)
    output wire        b2c_ctrl,

    output wire [7:0]  status
);

    localparam [3:0] S_IDLE   = 4'd0,
                     S_FETCH  = 4'd1,
                     S_WAIT   = 4'd2,
                     S_DECODE = 4'd3,
                     S_EXEC1  = 4'd4,
                     S_EXEC2  = 4'd5,
                     S_ACCUM  = 4'd6,
                     S_EMIT   = 4'd7,
                     S_HOLD   = 4'd8,
                     S_ERR    = 4'd9;

    reg  [3:0]  state_r;
    reg  [15:0] payload_r;
    reg  [15:0] acc_r;
    reg  [15:0] lfsr_r;
    reg  [7:0]  retry_r;
    reg         b2c_r;

    reg  [3:0]  nstate;
    reg         rd_en;
    reg         ld_pl;
    reg         do_acc;
    reg         do_emit;
    reg         clr_ret;
    reg         inc_ret;

    // next-state / output decode - every output is assigned a default on the
    // first lines, so no path can infer a latch
    always @(*) begin
        nstate  = state_r;
        rd_en   = 1'b0;
        ld_pl   = 1'b0;
        do_acc  = 1'b0;
        do_emit = 1'b0;
        clr_ret = 1'b0;
        inc_ret = 1'b0;

        case (state_r)
            S_IDLE: begin
                if (!a2b_empty)
                    nstate = S_FETCH;
            end
            S_FETCH: begin
                // async_fifo presents rdata for the CURRENT head in the same
                // cycle rd_en is asserted - the read pointer only advances on
                // this edge.  Capture the payload here; waiting a state would
                // read the next (possibly unwritten) slot.
                if (!a2b_empty) begin
                    rd_en  = 1'b1;
                    ld_pl  = 1'b1;
                    nstate = S_WAIT;
                end else begin
                    nstate = S_IDLE;
                end
            end
            S_WAIT: begin
                nstate = S_DECODE;
            end
            S_DECODE: begin
                if (payload_r[15])
                    nstate = S_ERR;
                else
                    nstate = S_EXEC1;
            end
            S_EXEC1: begin
                nstate = S_EXEC2;
            end
            S_EXEC2: begin
                nstate = S_ACCUM;
            end
            S_ACCUM: begin
                do_acc = 1'b1;
                nstate = S_EMIT;
            end
            S_EMIT: begin
                do_emit = 1'b1;
                clr_ret = 1'b1;
                nstate  = S_HOLD;
            end
            S_HOLD: begin
                if (a2b_empty)
                    nstate = S_IDLE;
                else
                    nstate = S_FETCH;
            end
            S_ERR: begin
                inc_ret = 1'b1;
                if (retry_r == 8'hFF)
                    nstate = S_IDLE;
                else
                    nstate = S_HOLD;
            end
            default: begin
                nstate = S_IDLE;
            end
        endcase
    end

    always @(posedge clk_div or negedge rst_n) begin
        if (!rst_n) begin
            state_r   <= S_IDLE;
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
    reg [7:0] status_r;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            status_r <= 8'd0;
        else
            status_r <= {b2c_r, a2b_empty, acc_r[1:0], state_r};
    end

    assign status = status_r;
    assign dbg_state = state_r;   // formal-only tap

endmodule
