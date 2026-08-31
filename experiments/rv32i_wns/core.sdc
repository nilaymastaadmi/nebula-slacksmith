# Single clock. 10 ns starting period; real F_max derived from WNS.
create_clock -name clk -period 10.0 [get_ports clk]

# Every non-clock input is explicitly driven and delayed.
# imem_data and dmem_rdata are the async-read memory returns: if these are left
# unconstrained their paths vanish from the analysis and WNS becomes fiction.
set NONCLK [get_ports {rst_n imem_data dmem_rdata}]
set_driving_cell -lib_cell sky130_fd_sc_hd__buf_1 -pin X $NONCLK
set_input_delay  -clock clk 2.0 $NONCLK

# Every output loaded and delayed.
set_output_delay -clock clk 2.0 [all_outputs]
set_load 0.05 [all_outputs]
