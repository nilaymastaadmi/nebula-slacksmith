// ---------------------------------------------------------------------------
// sync_fifo - single-clock-domain elastic FIFO, DEPTH words.
//
// Reference (k=0) design for a branch-3 (stream equivalence) demonstration
// on real RTL. Single clock domain deliberately: the property under test --
// does a design with more internal buffering diverge from a fixed-cycle-
// offset comparison under back-pressure -- is orthogonal to cross-clock
// synchronization, and conflating the two would mean solving two different
// kinds of hard problems (CDC correctness and elastic-interface latency)
// in one module. async_fifo.v already answers the CDC question; this
// answers the elastic-interface question, cleanly separated.
//
// Reuses this project's own established async_fifo.v convention -- gray
// coding is dropped deliberately: gray coding exists specifically to
// survive a multi-bit-change hazard across an ASYNCHRONOUS clock boundary,
// and there is none here (single clock), so a direct binary pointer
// comparison is both simpler and equally correct.
// ---------------------------------------------------------------------------
module sync_fifo #(
    parameter DW = 8,
    parameter AW = 3          // depth = 2**AW
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

    reg [AW:0] wbin_r, rbin_r;
    reg        wfull_r, rempty_r;

    wire        wen       = winc & ~wfull_r;
    wire        ren       = rinc & ~rempty_r;
    wire [AW:0] wbin_nxt  = wbin_r + {{AW{1'b0}}, wen};
    wire [AW:0] rbin_nxt  = rbin_r + {{AW{1'b0}}, ren};

    // full when the next write pointer would lap the read pointer; empty
    // when the next read pointer catches the write pointer. Look-ahead
    // (computed from the _nxt pointers), matching async_fifo.v's own
    // registered-flag convention, one cycle ahead of the pointer update.
    wire wfull_nxt  = (wbin_nxt == {~rbin_r[AW], rbin_r[AW-1:0]});
    wire rempty_nxt = (rbin_nxt == wbin_r);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wbin_r   <= {(AW+1){1'b0}};
            rbin_r   <= {(AW+1){1'b0}};
            wfull_r  <= 1'b0;
            rempty_r <= 1'b1;
        end else begin
            wbin_r   <= wbin_nxt;
            rbin_r   <= rbin_nxt;
            wfull_r  <= wfull_nxt;
            rempty_r <= rempty_nxt;
        end
    end

    always @(posedge clk)
        if (wen)
            mem[wbin_r[AW-1:0]] <= wdata;

    assign wfull  = wfull_r;
    assign rdata  = mem[rbin_r[AW-1:0]];
    assign rempty = rempty_r;

endmodule
