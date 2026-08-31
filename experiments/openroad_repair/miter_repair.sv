// Bounded equivalence of bench_top before and after OpenROAD repair_design.
//
// A name-based check (equiv_make) does not work here: repair_design writes a
// flattened netlist with its own instance and net names, so equiv_make created
// only 86 equivalence points across a 55K-cell design and proved none of them.
// That is a failure of the matching, not evidence about the circuits.
//
// This compares the only things whose names are guaranteed stable: the five
// clocks, five resets, three input buses and the five primary outputs. Both
// designs see identical stimulus. Bounded, and reported as bounded.
module miter_repair (
    input wire clk_a, input wire clk_b, input wire clk_c,
    input wire clk_d, input wire clk_e,
    input wire rst_a_n, input wire rst_b_n, input wire rst_c_n,
    input wire rst_d_n, input wire rst_e_n,
    input wire [7:0]  data_in_a,
    input wire        valid_in_a,
    input wire [3:0]  cfg_addr_e,
    input wire [31:0] cfg_wdata_e,
    input wire        cfg_we_e
);
    wire [15:0] g_mac, t_mac;
    wire [7:0]  g_status, t_status;
    wire        g_uart, t_uart;
    wire        g_timer, t_timer;
    wire [7:0]  g_cfg, t_cfg;

    bench_top_gold u_g (
        .clk_a(clk_a), .clk_b(clk_b), .clk_c(clk_c), .clk_d(clk_d), .clk_e(clk_e),
        .rst_a_n(rst_a_n), .rst_b_n(rst_b_n), .rst_c_n(rst_c_n),
        .rst_d_n(rst_d_n), .rst_e_n(rst_e_n),
        .data_in_a(data_in_a), .valid_in_a(valid_in_a),
        .cfg_addr_e(cfg_addr_e), .cfg_wdata_e(cfg_wdata_e), .cfg_we_e(cfg_we_e),
        .mac_result_a(g_mac), .status_b(g_status), .uart_tx_c(g_uart),
        .timer_pulse_d(g_timer), .cfg_status_e(g_cfg)
    );

    bench_top_gate u_t (
        .clk_a(clk_a), .clk_b(clk_b), .clk_c(clk_c), .clk_d(clk_d), .clk_e(clk_e),
        .rst_a_n(rst_a_n), .rst_b_n(rst_b_n), .rst_c_n(rst_c_n),
        .rst_d_n(rst_d_n), .rst_e_n(rst_e_n),
        .data_in_a(data_in_a), .valid_in_a(valid_in_a),
        .cfg_addr_e(cfg_addr_e), .cfg_wdata_e(cfg_wdata_e), .cfg_we_e(cfg_we_e),
        .mac_result_a(t_mac), .status_b(t_status), .uart_tx_c(t_uart),
        .timer_pulse_d(t_timer), .cfg_status_e(t_cfg)
    );

`ifdef FORMAL
    initial assume (!rst_a_n);
    initial assume (!rst_b_n);
    initial assume (!rst_c_n);
    initial assume (!rst_d_n);
    initial assume (!rst_e_n);

    always @* begin
        eq_mac:    assert (g_mac    == t_mac);
        eq_status: assert (g_status == t_status);
        eq_uart:   assert (g_uart   == t_uart);
        eq_timer:  assert (g_timer  == t_timer);
        eq_cfg:    assert (g_cfg    == t_cfg);
    end
`endif
endmodule
