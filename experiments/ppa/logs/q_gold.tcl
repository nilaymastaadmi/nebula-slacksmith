read_liberty /home/toshn/sta_work/sky130hd_tt.lib
read_verilog core_gold.v
link_design rv32i_core
read_sdc ppa.sdc
report_wns
report_power
