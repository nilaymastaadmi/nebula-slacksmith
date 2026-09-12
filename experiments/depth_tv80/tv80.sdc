# Frozen before any proposal ran. 0.9x tv80s's own measured requirement of
# 8.938 ns, the same rule experiments/drrtl_transfer/ used for all 20 designs
# and experiments/depth_i2c/ used for i2c. No timing exception anywhere.
#
# The transfer study recorded tv80 at 9.797 ns and 4,023 cells. This is the
# upstream hutch31/tv80 source rather than the netlist that study measured, and
# it synthesises to 3,447 cells with an 8.938 ns requirement, so the target is
# re-derived here rather than inherited. The DEPTH verdict is re-derived too.
create_clock -name clk -period 8.044 [get_ports clk]
set_input_delay  0.0 -clock clk [all_inputs]
set_output_delay 0.0 -clock clk [all_outputs]
