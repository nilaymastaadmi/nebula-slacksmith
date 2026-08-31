`timescale 1ns/1ps
// F2 demonstration: does pipelining the clamp change domain_a's OBSERVABLE
// module-level behaviour (mac_result), despite the boundary proof?
// Same stimulus, real /2 divider, compare mac_result streams.
module tb_f2;
    reg clk = 0, rst_n = 0;
    always #5 clk = ~clk;
    // real /2 divider, same as bench_top
    reg cdiv = 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cdiv <= 0; else cdiv <= ~cdiv;

    reg [7:0] data = 0; reg vld = 0;
    reg [31:0] cfg = 32'h0007_0101; reg cfg_empty = 1;
    wire [15:0] res_a, res_b;
    wire rda, rdb, wea, web; wire [15:0] wda, wdb;

    domain_a_clamped_comb u_a (.clk(clk), .clk_div(cdiv), .rst_n(rst_n),
        .data_in(data), .valid_in(vld), .cfg_rd_en(rda), .cfg_rdata(cfg),
        .cfg_empty(cfg_empty), .a2b_wr_en(wea), .a2b_wdata(wda), .a2b_full(1'b0),
        .mac_result(res_a));
    domain_a_clamped_pipelined u_b (.clk(clk), .clk_div(cdiv), .rst_n(rst_n),
        .data_in(data), .valid_in(vld), .cfg_rd_en(rdb), .cfg_rdata(cfg),
        .cfg_empty(cfg_empty), .a2b_wr_en(web), .a2b_wdata(wdb), .a2b_full(1'b0),
        .mac_result(res_b));

    integer i; integer diverged = 0;
    initial begin
        #23 rst_n = 1;
        // stream of distinct samples every clk, valid always on
        for (i = 1; i <= 200; i = i + 1) begin
            @(negedge clk); data = i[7:0]; vld = 1;
        end
        vld = 0;
        repeat (30) @(posedge clk);
        if (diverged == 0) $display("NO DIVERGENCE in mac_result over 200 samples");
        $finish;
    end
    always @(posedge clk)
        if (rst_n && res_a !== res_b && diverged < 5) begin
            diverged = diverged + 1;
            $display("DIVERGED t=%0t  comb=%h  pipelined=%h", $time, res_a, res_b);
        end
endmodule
