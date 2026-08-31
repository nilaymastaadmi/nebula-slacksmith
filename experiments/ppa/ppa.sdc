create_clock -name clk -period 10.0 [get_ports clk]
set NONCLK [get_ports {rst_n imem_data dmem_rdata}]
set_driving_cell -lib_cell sky130_fd_sc_hd__buf_1 -pin X $NONCLK
set_input_delay  -clock clk 2.0 $NONCLK
set_output_delay -clock clk 2.0 [all_outputs]
set_load 0.05 [all_outputs]
set_false_path -from [get_ports rst_n]
