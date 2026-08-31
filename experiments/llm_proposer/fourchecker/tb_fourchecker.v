`timescale 1ns/1ps
// Registered four-checker column for P4: would a testbench have caught what
// EQY caught? Two stimulus regimes, both driving gold and gate cores in
// lockstep and comparing every architectural output.
module tb_fc;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg [31:0] imem_data, dmem_rdata;
    wire [31:0] g_ia,g_da,g_dw,g_rp,g_ri,g_rv, t_ia,t_da,t_dw,t_rp,t_ri,t_rv;
    wire [3:0] g_ws,t_ws; wire [4:0] g_rd,t_rd; wire g_we,t_we,g_rwe,t_rwe,g_h,t_h;
    rv32i_core_gold ug(.clk(clk),.rst_n(rst_n),.imem_addr(g_ia),.imem_data(imem_data),
      .dmem_addr(g_da),.dmem_wdata(g_dw),.dmem_wstrb(g_ws),.dmem_we(g_we),.dmem_rdata(dmem_rdata),
      .retire_pc(g_rp),.retire_insn(g_ri),.retire_rd(g_rd),.retire_val(g_rv),.retire_we(g_rwe),.halted(g_h));
    rv32i_core_gate ut(.clk(clk),.rst_n(rst_n),.imem_addr(t_ia),.imem_data(imem_data),
      .dmem_addr(t_da),.dmem_wdata(t_dw),.dmem_wstrb(t_ws),.dmem_we(t_we),.dmem_rdata(dmem_rdata),
      .retire_pc(t_rp),.retire_insn(t_ri),.retire_rd(t_rd),.retire_val(t_rv),.retire_we(t_rwe),.halted(t_h));

    integer i, miss; reg bad;
    task step; begin @(negedge clk); end endtask
    function differs; input dummy; begin
      differs = (g_ia!==t_ia)||(g_da!==t_da)||(g_dw!==t_dw)||(g_ws!==t_ws)||(g_we!==t_we)
              ||(g_rp!==t_rp)||(g_ri!==t_ri)||(g_rd!==t_rd)||(g_rv!==t_rv)||(g_rwe!==t_rwe)||(g_h!==t_h);
    end endfunction

    initial begin
        dmem_rdata = 32'd0;
        // ---- REGIME 1: the ACTUAL firmware loop shipped in rv32_load.v
        rst_n=0; imem_data=32'h00000013; repeat(4) step; rst_n=1;
        bad=0;
        for (i=0;i<400;i=i+1) begin
            case (i%4)
              0: imem_data=32'h00100093; // addi x1,x0,1
              1: imem_data=32'h00110133; // add  x2,x2,x1
              2: imem_data=32'h0021C1B3; // xor  x3,x3,x2
              3: imem_data=32'hFF5FF06F; // jal  x0,-12
            endcase
            step; if (rst_n && differs(1'b0)) bad=1;
        end
        $display("REGIME 1 (real firmware loop, 400 cycles, no shift instructions): %s",
                 bad ? "CAUGHT" : "MISSED");

        // ---- REGIME 2: random instruction words
        rst_n=0; repeat(4) step; rst_n=1; miss=-1;
        for (i=0;i<20000;i=i+1) begin
            imem_data = $random;
            step;
            if (rst_n && differs(1'b0) && miss<0) miss=i;
        end
        if (miss>=0) $display("REGIME 2 (random instructions): CAUGHT at vector %0d of 20000", miss);
        else         $display("REGIME 2 (random instructions, 20000): MISSED");
        $finish;
    end
endmodule
