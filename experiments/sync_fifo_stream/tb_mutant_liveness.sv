`timescale 1ns/1ps
module tb_mutant_liveness;
    reg clk = 0;
    reg rst_n = 0;
    reg winc = 0;
    reg [7:0] wdata = 0;
    reg rinc = 0;
    wire wfull, rempty;
    wire [7:0] rdata;

    always #5 clk = ~clk;

    sync_fifo_pipelined #(.DW(8), .AW(3)) dut (
        .clk(clk), .rst_n(rst_n),
        .winc(winc), .wdata(wdata), .wfull(wfull),
        .rinc(rinc), .rdata(rdata), .rempty(rempty)
    );

    integer i;
    initial begin
        rst_n = 0; winc = 0; rinc = 0;
        #23 rst_n = 1;
        @(posedge clk);

        // write one word, then hold: never assert rinc, so s2_ready stays
        // permanently 1 (~rdata_valid_r) until the FIRST forward happens --
        // but the mutant only updates rempty_core_r inside s2_ready, so if
        // the fix's own reasoning is right, an EMPTY-to-non-empty
        // transition after a write with s2_ready already true should still
        // work here (s2_ready is true from reset since rdata_valid_r=0).
        // Try the harder case the original session flagged: write, let the
        // core register settle non-empty, consumer holds rinc low so
        // rdata_valid_r fills and s2_ready goes false, THEN write again
        // while s2_ready is false -- rempty_core_r should still notice the
        // new write once s2_ready returns, under the real fix. Under the
        // mutant it must NOT, because rempty_core_r is frozen while
        // s2_ready is false.
        winc = 1; wdata = 8'hAA; @(posedge clk); winc = 0;
        @(posedge clk); // let it forward into the output register (s2_ready was 1)
        @(posedge clk);

        if (rempty !== 1'b0)
            $display("FAIL-EARLY: rempty did not clear after first write+forward, rempty=%b", rempty);
        else
            $display("OK: first word forwarded, rempty=0 rdata=%h", rdata);

        // now output register is full (rdata_valid_r=1), s2_ready=0.
        // Write a SECOND word while s2_ready is false.
        winc = 1; wdata = 8'hBB; @(posedge clk); winc = 0;
        @(posedge clk);
        $display("after 2nd write while s2_ready=0: wfull=%b rempty=%b rdata=%h", wfull, rempty, rdata);

        // now drain the first word.
        rinc = 1; @(posedge clk); rinc = 0;
        @(posedge clk);
        $display("after draining word 1: rempty=%b rdata=%h (expect 0 / BB if the second word ever surfaces)", rempty, rdata);

        // give it 20 more cycles of draining attempts to see if word 2 EVER appears
        for (i = 0; i < 20; i = i + 1) begin
            rinc = 1; @(posedge clk); rinc = 0; @(posedge clk);
            if (rdata == 8'hBB) begin
                $display("word 2 (BB) surfaced at cycle %0d -- LIVE, no stuck transaction", i);
                $finish;
            end
        end
        $display("LIVENESS FAILURE CONFIRMED: word 2 (BB) never surfaced after 20 drain cycles. rempty=%b rdata=%h", rempty, rdata);
        $finish;
    end
endmodule
