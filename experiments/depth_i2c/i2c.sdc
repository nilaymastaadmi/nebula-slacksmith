# Frozen before the loop ran. 0.9x i2c_master_top's own measured requirement
# of 3.956 ns, the same rule experiments/drrtl_transfer/ used for all 20
# designs. No timing exception is used anywhere in this file.
create_clock -name wb_clk_i -period 3.560 [get_ports wb_clk_i]
set_input_delay  0.0 -clock wb_clk_i [all_inputs]
set_output_delay 0.0 -clock wb_clk_i [all_outputs]
