`timescale 1ns/1ps
// Directed probe: does the P4 bug manifest in SIMULATION at all?
// addi x1,x0,-1  -> x1 = 0xFFFFFFFF
// srai x2,x1,4   -> gold (SRA) = 0xFFFFFFFF ; buggy (SRL) = 0x0FFFFFFF
module tb_d;
    reg clk=0, rst_n=0; always #5 clk=~clk;
    reg [31:0] imem_data; reg [31:0] dmem_rdata=0;
    wire [31:0] g_rv,t_rv; wire [31:0] g_ia,t_ia,g_da,t_da,g_dw,t_dw,g_rp,t_rp,g_ri,t_ri;
    wire [3:0] g_ws,t_ws; wire [4:0] g_rd,t_rd; wire g_we,t_we,g_rwe,t_rwe,g_h,t_h;
    rv32i_core_gold ug(.clk(clk),.rst_n(rst_n),.imem_addr(g_ia),.imem_data(imem_data),
      .dmem_addr(g_da),.dmem_wdata(g_dw),.dmem_wstrb(g_ws),.dmem_we(g_we),.dmem_rdata(dmem_rdata),
      .retire_pc(g_rp),.retire_insn(g_ri),.retire_rd(g_rd),.retire_val(g_rv),.retire_we(g_rwe),.halted(g_h));
    rv32i_core_gate ut(.clk(clk),.rst_n(rst_n),.imem_addr(t_ia),.imem_data(imem_data),
      .dmem_addr(t_da),.dmem_wdata(t_dw),.dmem_wstrb(t_ws),.dmem_we(t_we),.dmem_rdata(dmem_rdata),
      .retire_pc(t_rp),.retire_insn(t_ri),.retire_rd(t_rd),.retire_val(t_rv),.retire_we(t_rwe),.halted(t_h));
    initial begin
        imem_data=32'h00000013; repeat(4) @(negedge clk); rst_n=1;
        imem_data=32'hFFF00093; @(negedge clk);           // addi x1,x0,-1
        imem_data=32'h4040D113; @(negedge clk);           // srai x2,x1,4
        @(negedge clk);
        $display("SRAI x2,x1,4 with x1=0xFFFFFFFF:");
        $display("  gold retire_val = %h", g_rv);
        $display("  gate retire_val = %h", t_rv);
        $display("  %s", (g_rv===t_rv) ? "SIMULATION AGREES (bug does NOT manifest in Icarus)"
                                       : "SIMULATION DIFFERS (bug manifests)");
        $finish;
    end
endmodule
