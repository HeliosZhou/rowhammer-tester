#!/bin/bash
# ZCU104 环境配置脚本

# 激活Python虚拟环境
source venv/bin/activate

# 设置Vivado环境
source /home/hc/Xilinx/Vivado/2020.2/settings64.sh

# 设置RISC-V交叉编译工具链
export PATH="$(pwd)/third_party/riscv64-unknown-elf-gcc/bin:$PATH"

# 设置ZCU104目标板配置
export TARGET=zcu104
export IP_ADDRESS=192.168.100.50

# 确保路径包含项目的bin目录
export PATH="$(pwd)/venv/bin:$(pwd)/bin:$PATH"

echo "ZCU104环境配置完成:"
echo "TARGET=${TARGET}"
echo "IP_ADDRESS=${IP_ADDRESS}"
echo "虚拟环境已激活"
echo "Vivado 2020.2 环境已加载"
echo "RISC-V交叉编译工具链已配置"
echo ""
echo "接下来的操作："
echo "1. 构建bitstream: make build"
echo "2. 配置ZCU104板的网络和SD卡"