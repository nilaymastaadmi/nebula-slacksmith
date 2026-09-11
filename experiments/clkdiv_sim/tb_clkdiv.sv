// Measure the generated-clock periods and duty cycles that REPORT section 4
// claims, so the claim has evidence in this repository rather than in a
// simulation somebody ran once.
//
// Added 2026-09-11 after tools/check_report_numbers.py flagged "15.000" and
// "25.000" as numbers appearing nowhere in the evidence directories. They were
// measured; they were never committed.
//
// Source clock is 5 ns period (200 MHz), so:
//   /2 -> 10.000 ns    /3 -> 15.000 ns    /4 -> 20.000 ns    /5 -> 25.000 ns
//
// Reset is released OFF the source grid, at 13.3 ns, because a divider that
// only works when reset lands on an edge is a divider that works by accident.
`timescale 1ns / 1ps

module tb_clkdiv;

    localparam real SRC_PERIOD = 5.0;

    reg clk_in = 1'b0;
    reg rst_n  = 1'b0;
    always #(SRC_PERIOD/2.0) clk_in = ~clk_in;

    wire d2, d3, d4, d5;
    clkdiv #(.DIV(2)) u2 (.clk_in(clk_in), .rst_n(rst_n), .clk_out(d2));
    clkdiv #(.DIV(3)) u3 (.clk_in(clk_in), .rst_n(rst_n), .clk_out(d3));
    clkdiv #(.DIV(4)) u4 (.clk_in(clk_in), .rst_n(rst_n), .clk_out(d4));
    clkdiv #(.DIV(5)) u5 (.clk_in(clk_in), .rst_n(rst_n), .clk_out(d5));

    integer fail = 0;

    // One checker instance per divider. Skips the first two edges so the
    // measurement never includes the reset-release transient.
    task automatic check(input integer div, input real period, input real high);
        begin
            if (period < 0.0) begin
                $display("  DIV=%0d  NO EDGES SEEN", div);
                fail = fail + 1;
            end else begin
                $display("  DIV=%0d  period %0.3f ns  high %0.3f ns  duty %0.1f%%",
                         div, period, high, 100.0 * high / period);
                if (period != div * SRC_PERIOD) begin
                    $display("    FAIL expected period %0.3f", div * SRC_PERIOD);
                    fail = fail + 1;
                end
            end
        end
    endtask

    // Edge bookkeeping, one set per divider.
    real r2, r3, r4, r5;      // last rise time
    real f2, f3, f4, f5;      // last fall time
    real p2, p3, p4, p5;      // measured period
    real h2, h3, h4, h5;      // measured high time
    integer n2 = 0, n3 = 0, n4 = 0, n5 = 0;

    initial begin p2 = -1.0; p3 = -1.0; p4 = -1.0; p5 = -1.0; end

    always @(posedge d2) begin
        if (n2 > 1) p2 = $realtime - r2;
        r2 = $realtime; n2 = n2 + 1;
    end
    always @(negedge d2) if (n2 > 1) h2 = $realtime - r2;

    always @(posedge d3) begin
        if (n3 > 1) p3 = $realtime - r3;
        r3 = $realtime; n3 = n3 + 1;
    end
    always @(negedge d3) if (n3 > 1) h3 = $realtime - r3;

    always @(posedge d4) begin
        if (n4 > 1) p4 = $realtime - r4;
        r4 = $realtime; n4 = n4 + 1;
    end
    always @(negedge d4) if (n4 > 1) h4 = $realtime - r4;

    always @(posedge d5) begin
        if (n5 > 1) p5 = $realtime - r5;
        r5 = $realtime; n5 = n5 + 1;
    end
    always @(negedge d5) if (n5 > 1) h5 = $realtime - r5;

    initial begin
        #13.3 rst_n = 1'b1;      // deliberately off the source grid
        #2000;
        $display("clkdiv, source period %0.3f ns, reset released at 13.300 ns",
                 SRC_PERIOD);
        check(2, p2, h2);
        check(3, p3, h3);
        check(4, p4, h4);
        check(5, p5, h5);
        if (fail == 0)
            $display("CLKDIV OK: /2 /3 /4 /5 all exact");
        else
            $display("CLKDIV FAIL: %0d checks failed", fail);
        $finish;
    end

endmodule
