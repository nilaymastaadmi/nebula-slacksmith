// ---------------------------------------------------------------------------
// bench_top - 5-clock-domain SoC skeleton, device-under-test for an RTL
//             timing-optimization benchmark (Yosys synthesis + OpenSTA).
//
// Five primary clocks with no phase relationship, each with its own async
// active-low reset.  Each primary clock feeds one in-RTL divider producing a
// real generated clock that clocks real flip-flops:
//
//   clk_a -> /2   clk_b -> /3   clk_c -> /4   clk_d -> /5   clk_e -> /2
//
// The /3 and /5 dividers use both edges of their source clock to get a true
// 50% duty cycle (see clkdiv.v).
//
// Crossings form a ring A -> B -> C -> D -> E -> A:
//   multi-bit data    -> gray-pointer async FIFO (async_fifo)
//   single-bit control-> two-flop synchronizer   (sync2ff)
//
// Plain Verilog-2001.  No vendor primitives, no interfaces/structs/classes,
// no initial blocks, no # delays, no $readmemh, no latches.
// ---------------------------------------------------------------------------
module bench_top (
    // five independent asynchronous clocks + their async active-low resets
    input  wire        clk_a,
    input  wire        clk_b,
    input  wire        clk_c,
    input  wire        clk_d,
    input  wire        clk_e,
    input  wire        rst_a_n,
    input  wire        rst_b_n,
    input  wire        rst_c_n,
    input  wire        rst_d_n,
    input  wire        rst_e_n,

    // domain A stimulus
    input  wire [7:0]  data_in_a,
    input  wire        valid_in_a,

    // domain E config write port
    input  wire [3:0]  cfg_addr_e,
    input  wire [31:0] cfg_wdata_e,
    input  wire        cfg_we_e,

    // one observable output per domain, so timing paths terminate
    output wire [15:0] mac_result_a,
    output wire [7:0]  status_b,
    output wire        uart_tx_c,
    output wire        timer_pulse_d,
    output wire [7:0]  cfg_status_e
);

    // ---------------------------------------------------- generated clocks
    wire clk_a_div2;
    wire clk_b_div3;
    wire clk_c_div4;
    wire clk_d_div5;
    wire clk_e_div2;

    clkdiv #(.DIV(2)) u_clkdiv_a (.clk_in(clk_a), .rst_n(rst_a_n), .clk_out(clk_a_div2));
    clkdiv #(.DIV(3)) u_clkdiv_b (.clk_in(clk_b), .rst_n(rst_b_n), .clk_out(clk_b_div3));
    clkdiv #(.DIV(4)) u_clkdiv_c (.clk_in(clk_c), .rst_n(rst_c_n), .clk_out(clk_c_div4));
    clkdiv #(.DIV(5)) u_clkdiv_d (.clk_in(clk_d), .rst_n(rst_d_n), .clk_out(clk_d_div5));
    clkdiv #(.DIV(2)) u_clkdiv_e (.clk_in(clk_e), .rst_n(rst_e_n), .clk_out(clk_e_div2));

    // -------------------------------------------------------- interconnect
    // A -> B  data (FIFO)
    wire        a2b_wr_en;
    wire [15:0] a2b_wdata;
    wire        a2b_full;
    wire        a2b_rd_en;
    wire [15:0] a2b_rdata;
    wire        a2b_empty;

    // B -> C  control (2FF, synchronizer lives inside domain_c)
    wire        b2c_ctrl;

    // C -> D  data (FIFO)
    wire        c2d_wr_en;
    wire [7:0]  c2d_wdata;
    wire        c2d_full;
    wire        c2d_rd_en;
    wire [7:0]  c2d_rdata;
    wire        c2d_empty;

    // D -> E  control (2FF, synchronizer lives inside domain_e)
    wire        d2e_ctrl;

    // E -> A  config data (FIFO)
    wire        e2a_wr_en;
    wire [31:0] e2a_wdata;
    wire        e2a_full;
    wire        e2a_rd_en;
    wire [31:0] e2a_rdata;
    wire        e2a_empty;

    // ------------------------------------------------------------ domain A
    domain_a_clamped_pipelined u_domain_a (
        .clk        (clk_a),
        .clk_div    (clk_a_div2),
        .rst_n      (rst_a_n),
        .data_in    (data_in_a),
        .valid_in   (valid_in_a),
        .cfg_rd_en  (e2a_rd_en),
        .cfg_rdata  (e2a_rdata),
        .cfg_empty  (e2a_empty),
        .a2b_wr_en  (a2b_wr_en),
        .a2b_wdata  (a2b_wdata),
        .a2b_full   (a2b_full),
        .mac_result (mac_result_a)
    );

    // ------------------------------------------------------------ domain B
    domain_b u_domain_b (
        .clk       (clk_b),
        .clk_div   (clk_b_div3),
        .rst_n     (rst_b_n),
        .a2b_rd_en (a2b_rd_en),
        .a2b_rdata (a2b_rdata),
        .a2b_empty (a2b_empty),
        .b2c_ctrl  (b2c_ctrl),
        .status    (status_b)
    );

    // ------------------------------------------------------------ domain C
    domain_c u_domain_c (
        .clk            (clk_c),
        .clk_div        (clk_c_div4),
        .rst_n          (rst_c_n),
        .b2c_ctrl_async (b2c_ctrl),
        .c2d_wr_en      (c2d_wr_en),
        .c2d_wdata      (c2d_wdata),
        .c2d_full       (c2d_full),
        .tx             (uart_tx_c)
    );

    // ------------------------------------------------------------ domain D
    domain_d u_domain_d (
        .clk         (clk_d),
        .clk_div     (clk_d_div5),
        .rst_n       (rst_d_n),
        .c2d_rd_en   (c2d_rd_en),
        .c2d_rdata   (c2d_rdata),
        .c2d_empty   (c2d_empty),
        .d2e_ctrl    (d2e_ctrl),
        .timer_pulse (timer_pulse_d)
    );

    // ------------------------------------------------------------ domain E
    domain_e u_domain_e (
        .clk            (clk_e),
        .clk_div        (clk_e_div2),
        .rst_n          (rst_e_n),
        .cfg_addr       (cfg_addr_e),
        .cfg_wdata      (cfg_wdata_e),
        .cfg_we         (cfg_we_e),
        .d2e_ctrl_async (d2e_ctrl),
        .e2a_wr_en      (e2a_wr_en),
        .e2a_wdata      (e2a_wdata),
        .e2a_full       (e2a_full),
        .cfg_status     (cfg_status_e)
    );

    // ----------------------------------------------- multi-bit CDC: A -> B
    // write: clk_a/2   read: clk_b/3
    async_fifo #(
        .DW (16),
        .AW (3)
    ) u_fifo_a2b (
        .wclk   (clk_a_div2),
        .wrst_n (rst_a_n),
        .winc   (a2b_wr_en),
        .wdata  (a2b_wdata),
        .wfull  (a2b_full),
        .rclk   (clk_b_div3),
        .rrst_n (rst_b_n),
        .rinc   (a2b_rd_en),
        .rdata  (a2b_rdata),
        .rempty (a2b_empty)
    );

    // ----------------------------------------------- multi-bit CDC: C -> D
    // write: clk_c/4   read: clk_d/5
    async_fifo #(
        .DW (8),
        .AW (3)
    ) u_fifo_c2d (
        .wclk   (clk_c_div4),
        .wrst_n (rst_c_n),
        .winc   (c2d_wr_en),
        .wdata  (c2d_wdata),
        .wfull  (c2d_full),
        .rclk   (clk_d_div5),
        .rrst_n (rst_d_n),
        .rinc   (c2d_rd_en),
        .rdata  (c2d_rdata),
        .rempty (c2d_empty)
    );

    // ----------------------------------------------- multi-bit CDC: E -> A
    // write: clk_e/2   read: clk_a (primary)
    async_fifo #(
        .DW (32),
        .AW (2)
    ) u_fifo_e2a (
        .wclk   (clk_e_div2),
        .wrst_n (rst_e_n),
        .winc   (e2a_wr_en),
        .wdata  (e2a_wdata),
        .wfull  (e2a_full),
        .rclk   (clk_a),
        .rrst_n (rst_a_n),
        .rinc   (e2a_rd_en),
        .rdata  (e2a_rdata),
        .rempty (e2a_empty)
    );

endmodule
