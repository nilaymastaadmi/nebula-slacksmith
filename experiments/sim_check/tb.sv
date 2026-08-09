// Self-checking testbench: mac_opt (latency 2) against mac_ref (latency 1),
// compared with a one-cycle scoreboard offset. This is the shape of the
// correctness gate that agentic RTL tools actually rely on in practice.
//
// Two stimulus regimes, selected with +lazy:
//
//   aggressive (default) -- a, b and c all fresh random every cycle
//   lazy (+lazy)         -- c HELD CONSTANT, a and b random
//
// The lazy regime is not a strawman. A directed test for a multiply-accumulate
// naturally fixes the accumulate operand and sweeps the multiplier operands.
// It is what a human writes, and what a model writes when asked for a testbench.

`timescale 1ns/1ps

module tb;
    localparam W = 8;
    localparam DW = 2*W;

    reg clk = 0, rst = 1;
    reg [W-1:0]  a, b;
    reg [DW-1:0] c;

    wire [DW-1:0] y_ref, y_opt;

    mac_ref #(.W(W)) u_ref (.clk(clk), .rst(rst), .a(a), .b(b), .c(c), .y(y_ref));
    mac_opt #(.W(W)) u_opt (.clk(clk), .rst(rst), .a(a), .b(b), .c(c), .y(y_opt));

    // golden output delayed by K=1 to match the transformed design
    reg [DW-1:0] ref_d;
    always @(posedge clk) ref_d <= y_ref;

    always #5 clk = ~clk;

    integer errors = 0, checks = 0, i;
    integer lazy = 0, nvec = 20000;
    integer seed;
    reg [DW-1:0] c_fixed;

    initial begin
        if (!$value$plusargs("vectors=%d", nvec)) nvec = 20000;
        lazy = $test$plusargs("lazy");
        seed = 32'h0C0FFEE;            // fixed seed: reproducible

        c_fixed = 16'h1234;
        a = 0; b = 0; c = c_fixed;

        repeat (4) @(posedge clk);
        rst = 0;
        repeat (3) @(posedge clk);     // let both pipelines prime

        for (i = 0; i < nvec; i = i + 1) begin
            @(negedge clk);
            a = $random(seed);
            b = $random(seed);
            c = lazy ? c_fixed : $random(seed);
            @(posedge clk);
            #1;
            checks = checks + 1;
            if (y_opt !== ref_d) begin
                errors = errors + 1;
                if (errors <= 3)
                    $display("  MISMATCH @%0t  opt=%h  ref_delayed=%h  (a=%h b=%h c=%h)",
                             $time, y_opt, ref_d, a, b, c);
            end
        end

        $display("RESULT %s  checks=%0d errors=%0d  regime=%s",
                 (errors == 0) ? "PASS" : "FAIL", checks, errors,
                 lazy ? "lazy" : "aggressive");
        $finish;
    end
endmodule
