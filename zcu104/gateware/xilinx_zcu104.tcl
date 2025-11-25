
# Create Project

create_project -force -name xilinx_zcu104 -part xczu7ev-ffvc1156-2-i
set_msg_config -id {Common 17-55} -new_severity {Warning}

# Add Sources

read_verilog {/home/hc/rowhammer-tester-ZCU104/venv/lib/python3.10/site-packages/pythondata_cpu_vexriscv/verilog/VexRiscv_Min.v}
read_verilog {/home/hc/rowhammer-tester-ZCU104/build/zcu104/gateware/xilinx_zcu104.v}

# Add EDIFs


# Add IPs


# Add constraints

read_xdc xilinx_zcu104.xdc
set_property PROCESSING_ORDER EARLY [get_files xilinx_zcu104.xdc]

# Add pre-synthesis commands


# Synthesis

synth_design -directive default -top xilinx_zcu104 -part xczu7ev-ffvc1156-2-i

# Synthesis report

report_timing_summary -file xilinx_zcu104_timing_synth.rpt
report_utilization -hierarchical -file xilinx_zcu104_utilization_hierarchical_synth.rpt
report_utilization -file xilinx_zcu104_utilization_synth.rpt

# Optimize design

opt_design -directive default

# Add pre-placement commands


# Placement

place_design -directive default

# Placement report

report_utilization -hierarchical -file xilinx_zcu104_utilization_hierarchical_place.rpt
report_utilization -file xilinx_zcu104_utilization_place.rpt
report_io -file xilinx_zcu104_io.rpt
report_control_sets -verbose -file xilinx_zcu104_control_sets.rpt
report_clock_utilization -file xilinx_zcu104_clock_utilization.rpt

# Add pre-routing commands


# Routing

route_design -directive default
phys_opt_design -directive default
write_checkpoint -force xilinx_zcu104_route.dcp

# Routing report

report_timing_summary -no_header -no_detailed_paths
report_route_status -file xilinx_zcu104_route_status.rpt
report_drc -file xilinx_zcu104_drc.rpt
report_timing_summary -datasheet -max_paths 10 -file xilinx_zcu104_timing.rpt
report_power -file xilinx_zcu104_power.rpt

# Bitstream generation

write_bitstream -force xilinx_zcu104.bit 

# End

quit