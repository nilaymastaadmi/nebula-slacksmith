# Saved, rerunnable recipe for the rv32i_core calibrated-WNS numbers.
# Netlist: rv32i_core_mapped.v = yosys synth -> dfflibmap -> abc, sky130hd_tt,
# from github.com/nilaymastaadmi/rv32-dsp-soc rtl/rv32i_core.v (external repo;
# 6,769 cells, 1,024 dfrtp_1). The mapped netlist and liberty live outside
# this repo (~/sta_work/ on the build machine); this file is the exact query.
read_liberty sky130hd_tt.lib
read_verilog rv32i_core_mapped.v
link_design rv32i_core
read_sdc core.sdc
puts "=== WNS overall (includes the reset recovery group, see NOTES) ==="
report_wns
puts "=== worst path, full ==="
report_checks -path_delay max -digits 3
puts "=== reg-to-reg only ==="
report_checks -from [all_registers] -to [all_registers] -path_delay max -digits 3
