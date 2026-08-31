// ---------------------------------------------------------------------------
// rv32_load - RV32I core workload block for domain A.
//
// Exists for benchmark growth (organizer spec "~50K standard cells"). Wraps
// the project's own rv32i_core (from rv32-dsp-soc, same author, verified
// there against a golden C++ ISS over a 400-seed differential regression)
// with the two memories it needs to run standalone:
//
//   imem: an 8-word case-statement ROM holding a real, hand-encoded RV32I
//         loop (addi/add/xor/jal), so the fetch/decode/execute datapath
//         processes genuine instructions every cycle. Encodings checked
//         against the RV32I spec by hand:
//           0x00: 00100093  addi x1, x0, 1
//           0x04: 00110133  add  x2, x2, x1
//           0x08: 0021C1B3  xor  x3, x3, x2
//           0x0C: FF5FF06F  jal  x0, -12   (back to 0x00)
//         The pc register stops synthesis const-folding the instruction
//         stream, so the whole core stays live logic.
//
//   dmem: a 16-word register-file data memory, byte-strobed, elementwise
//         async-reset (same convention domain_e's cfg_reg established: a
//         reg array reset elementwise synthesizes to plain reset flops,
//         keeping the benchmark's every-flop-reset rule without a new
//         disclosed exception). The loop performs no loads or stores, but
//         the core cannot know that at synthesis time, so the full
//         load/store datapath remains reachable logic with real endpoints.
//
// fold_out mixes the retire stream into the hosting domain's visible
// outputs so nothing here is prunable.
// ---------------------------------------------------------------------------
module rv32_load (
    input  wire        clk,
    input  wire        rst_n,
    output wire [15:0] fold_out
);

    wire [31:0] imem_addr, dmem_addr, dmem_wdata;
    reg  [31:0] imem_data;
    wire [3:0]  dmem_wstrb;
    wire        dmem_we;
    wire [31:0] retire_pc, retire_insn, retire_val;
    wire [4:0]  retire_rd;
    wire        retire_we, halted;

    always @(*) begin
        case (imem_addr[4:2])
            3'd0:    imem_data = 32'h00100093;
            3'd1:    imem_data = 32'h00110133;
            3'd2:    imem_data = 32'h0021C1B3;
            3'd3:    imem_data = 32'hFF5FF06F;
            default: imem_data = 32'h00000013;   // nop
        endcase
    end

    reg [31:0] dm [0:15];
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 16; i = i + 1)
                dm[i] <= 32'd0;
        end else if (dmem_we) begin
            if (dmem_wstrb[0]) dm[dmem_addr[5:2]][7:0]   <= dmem_wdata[7:0];
            if (dmem_wstrb[1]) dm[dmem_addr[5:2]][15:8]  <= dmem_wdata[15:8];
            if (dmem_wstrb[2]) dm[dmem_addr[5:2]][23:16] <= dmem_wdata[23:16];
            if (dmem_wstrb[3]) dm[dmem_addr[5:2]][31:24] <= dmem_wdata[31:24];
        end
    end
    wire [31:0] dmem_rdata = dm[dmem_addr[5:2]];

    rv32i_core u_core (
        .clk         (clk),
        .rst_n       (rst_n),
        .imem_addr   (imem_addr),
        .imem_data   (imem_data),
        .dmem_addr   (dmem_addr),
        .dmem_wdata  (dmem_wdata),
        .dmem_wstrb  (dmem_wstrb),
        .dmem_we     (dmem_we),
        .dmem_rdata  (dmem_rdata),
        .retire_pc   (retire_pc),
        .retire_insn (retire_insn),
        .retire_rd   (retire_rd),
        .retire_val  (retire_val),
        .retire_we   (retire_we),
        .halted      (halted)
    );

    assign fold_out = retire_val[15:0] ^ retire_pc[15:0] ^ {15'd0, halted};

endmodule
