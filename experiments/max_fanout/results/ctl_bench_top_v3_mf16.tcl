read_liberty /home/toshn/sta_work/sky130hd_tt.lib
read_verilog /home/toshn/flatexp/E/mapped.v
link_design bench_top
read_sdc sdc/bench_top_v3_mf16.sdc
foreach c {clk_a clk_b clk_e} {
  puts "---CLOCK:$c---"
  report_checks -path_delay max -to [get_clocks $c] -group_path_count 1 -digits 3
}
exit
