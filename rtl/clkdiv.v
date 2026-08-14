// ---------------------------------------------------------------------------
// clkdiv - parameterizable clock divider producing a real generated clock.
//
//   DIV == 1 : bypass
//   DIV even : single posedge counter, output toggles every DIV/2 edges
//   DIV odd  : two counters, one on posedge and one on negedge of clk_in.
//              Each produces a phase flag that is high for (DIV+1)/2 source
//              cycles.  The negedge flag lags the posedge flag by half a
//              source period, so ANDing them removes exactly half a source
//              period from the high time:
//                  high = (DIV+1)/2 - 1/2 = DIV/2   ->  exact 50% duty.
//              This is a genuine divided clock (it clocks flops), NOT a
//              1-in-N clock-enable pulse.
//
// The AND of two registered phase flags cannot glitch: clk_p and clk_n never
// change at the same instant (their launch edges are half a period apart).
//
// All state is reset asynchronously, active low.
// Plain Verilog-2001 - no vendor primitives, no clock-buffer macros.
// ---------------------------------------------------------------------------
module clkdiv #(
    parameter DIV = 2
) (
    input  wire clk_in,
    input  wire rst_n,
    output wire clk_out
);

    function integer clog2;
        input integer value;
        integer v;
        begin
            v = value - 1;
            for (clog2 = 0; v > 0; clog2 = clog2 + 1)
                v = v >> 1;
        end
    endfunction

    generate
    if (DIV <= 1) begin : g_bypass

        assign clk_out = clk_in;

    end
    else if ((DIV % 2) == 0) begin : g_even

        localparam integer HALF = DIV / 2;
        localparam integer CW   = (HALF < 2) ? 1 : clog2(HALF);

        reg [CW-1:0] cnt;
        reg          clk_r;

        always @(posedge clk_in or negedge rst_n) begin
            if (!rst_n) begin
                cnt   <= {CW{1'b0}};
                clk_r <= 1'b0;
            end else if (cnt == (HALF - 1)) begin
                cnt   <= {CW{1'b0}};
                clk_r <= ~clk_r;
            end else begin
                cnt   <= cnt + 1'b1;
            end
        end

        assign clk_out = clk_r;

    end
    else begin : g_odd

        localparam integer HIGH = (DIV + 1) / 2;   // source cycles held high
        localparam integer CW   = clog2(DIV);

        reg [CW-1:0] cnt_p, cnt_n;
        reg          clk_p, clk_n;

        // rising-edge phase flag
        always @(posedge clk_in or negedge rst_n) begin
            if (!rst_n) begin
                cnt_p <= {CW{1'b0}};
                clk_p <= 1'b1;
            end else if (cnt_p == (DIV - 1)) begin
                cnt_p <= {CW{1'b0}};
                clk_p <= 1'b1;
            end else begin
                cnt_p <= cnt_p + 1'b1;
                if (cnt_p == (HIGH - 1))
                    clk_p <= 1'b0;
            end
        end

        // falling-edge phase flag - identical sequence, half a period later
        always @(negedge clk_in or negedge rst_n) begin
            if (!rst_n) begin
                cnt_n <= {CW{1'b0}};
                clk_n <= 1'b1;
            end else if (cnt_n == (DIV - 1)) begin
                cnt_n <= {CW{1'b0}};
                clk_n <= 1'b1;
            end else begin
                cnt_n <= cnt_n + 1'b1;
                if (cnt_n == (HIGH - 1))
                    clk_n <= 1'b0;
            end
        end

        assign clk_out = clk_p & clk_n;

    end
    endgenerate

endmodule
