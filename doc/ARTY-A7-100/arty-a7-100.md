# Arty DDR3 Rowhammer 测试操作流程

本文档指导在 Digilent Arty A7 (Artix-7 + 板载 DDR3) 上进行 Rowhammer 测试的完整步骤。与 ZCU104 不同，Arty 无需制作/移植 SD 卡，所有控制均在 PC 端完成。

## 📊 DDR3 内存规格信息

### 基于antmicro开源项目的 Arty-A7 板
-**芯片型号**:(镁光)Micron MT41K128M16
-**内存类型**:DDR3 SDRAM（板载）
-**制造商**:Micron Technology
-**总容量**:256MB(128M x16-bit)
-**数据宽度**:16-bit
-**系统时钟**:100MHZ
-**速度等级**:DDR3-1600 实际测试800MT/s

### 内存几何结构
| 参数 | 位数 | 数量 | 说明 |
|------|------|------|------|
| **行数** | 14-bit | **16,384 行** | 每个Bank 16384行 |
| **列数** | 10-bit | **1,024 列** | 每行1024个数据位置 |
| **Bank数** | 3-bit | **8 个Bank** | 独立的存储区域 |

### 容量计算
```
每行容量 = 1,024 列 × 16-bit = 16,384 bit = 2 KB
总容量 = 16,384 行 × 1,024 列 × 8 Bank × 16-bit = 256 MB
测试覆盖 = 16,777,216 地址（行14bit * 列10bit = 24bit）
```

### 关键时序参数
- **CAS延迟**: CL=7
- **刷新间隔**: tREFI = 64ms/8192 ≈ 7.8μs
- **行激活时间**: tRAS = 35ns
- **预充电时间**: tRP = 13.75ns

---

## 快速清单（Checklist）
```bash
DDR3测试（ARTY-A7）
1.生成比特流文件(可选，注意型号匹配)
    export TARGET=arty
    
    # 基本构建（使用默认参数：a7-35, 100MHz）
    make build
    
    # 指定FPGA型号（a7-35或a7-100）
    make build ARGS="--variant a7-100"
    
    # 指定系统时钟频率
    make build ARGS="--variant a7-100 --sys-clk-freq 50e6"    # 50MHz  (DDR3-400) 
    make build ARGS="--variant a7-100 --sys-clk-freq 100e6"   # 100MHz (DDR3-800)  ✅ 默认
    make build ARGS="--variant a7-100 --sys-clk-freq 133e6"   # 133MHz (DDR3-1066)  
    make build ARGS="--variant a7-100 --sys-clk-freq 167e6"   # 167MHz (DDR3-1333) 
    make build ARGS="--variant a7-100 --sys-clk-freq 200e6"   # 200MHz (DDR3-1600)



2.Vivado下载bitstream（可以在vivado下载，也可以使用命令）
    make upload/up 
注：可以将bit流文件下载到FLASH
    ./venv/bin/openFPGALoader --board arty_a7_100t build/arty/gateware/digilent_arty.bit --write-flash
    
3.测试网络
    查看各个网口状态：ip link → state up（确保处于up状态）
        ip link set xxx up
        sudo ip addr add 192.168.100.10/24 dev xxx
        ip addr
       
    最终，通过ping命令测试网络连通性：ping -c 3 192.168.100.50 

4.连接服务器
    make srv

5.打开新终端（虚拟环境、目标FPGA、进入文件夹）
    source ./venv/bin/activate
    export TARGET=arty  # (or zcu104) required to load target configuration
    export TARGET=zcu104
    cd rowhammer_tester/scripts/
    python leds.py -t 1000 # stop with Ctrl-C
    执行实例脚本：python leds.py （灯来回闪烁即连接成功）

6.执行测试脚本
    python bios_console.py 
# sys-clk-freq 50MHz  (DDR3-400，测试正常，降速) 
--=============== SoC ==================--
CPU:            VexRiscv_Lite @ 50MHz
BUS:            WISHBONE 32-bit @ 4GiB
CSR:            32-bit data
ROM:            128.0KiB
SRAM:           8.0KiB
L2:             8.0KiB
SDRAM:          256.0MiB 16-bit @ 400MT/s (CL-7 CWL-5)
MAIN-RAM:       256.0MiB
# sys-clk-freq 100MHz  (DDR3-800，测试正常，默认) 
--=============== SoC ==================--
CPU:            VexRiscv_Lite @ 100MHz
BUS:            WISHBONE 32-bit @ 4GiB
CSR:            32-bit data
ROM:            128.0KiB
SRAM:           8.0KiB
L2:             8.0KiB
SDRAM:          256.0MiB 16-bit @ 800MT/s (CL-7 CWL-5)
MAIN-RAM:       256.0MiB
# sys-clk-freq 200MHz  (DDR3-1600，测试异常，提速) 
--=============== SoC ==================--
CPU:            VexRiscv_Lite @ 200MHz
BUS:            WISHBONE 32-bit @ 4GiB
CSR:            32-bit data
ROM:            128.0KiB
SRAM:           8.0KiB
L2:             8.0KiB
SDRAM:          256.0MiB 16-bit @ 1600MT/s (CL-12 CWL-8)
MAIN-RAM:       256.0MiB
# 结论：由于系统晶振时钟为100MHz，构建bit流时sys-clk-freq参数只能指定在100MHz内，且参数值越低攻击速度越慢

litex> help

LiteX BIOS, available commands:

leds                     - Set Leds value
flush_l2_cache           - Flush L2 cache
flush_cpu_dcache         - Flush CPU data cache
crc                      - Compute CRC32 of a part of the address space
ident                    - Identifier of the system
help                     - Print this help

serialboot               - Boot from Serial (SFL)
boot                     - Boot from Memory

mem_cmp                  - Compare memory content
mem_speed                - Test memory speed
mem_test                 - Test memory access
mem_copy                 - Copy address space
mem_write                - Write address space
mem_read                 - Read address space
mem_list                 - List available memory regions
    Available memory regions:
    ROM                  0x00000000 0x20000 
    SRAM                 0x10000000 0x2000 
    MAIN_RAM             0x40000000 0x10000000 
    WRITER_PATTERN_DATA  0x20000000 0x400 
    WRITER_PATTERN_ADDR  0x21000000 0x100 
    READER_PATTERN_DATA  0x22000000 0x400 
    READER_PATTERN_ADDR  0x23000000 0x100 
    PAYLOAD              0x30000000 0x8000 
    SCRATCHPAD           0x31000000 0x400 
    CSR                  0xf0000000 0x10000 
sdram_mr_write           - Write SDRAM Mode Register
sdram_cal                - Calibrate SDRAM
sdram_test               - Test SDRAM
sdram_init               - Initialize SDRAM (Init + Calibration)
sdram_force_wrphase      - Force write phase
sdram_force_rdphase      - Force read phase
sdram_hw_test            - Run SDRAM HW-accelerated memtest
sdram_bist               - Run SDRAM Build-In Self-Test

mdio_dump                - Dump MDIO registers
mdio_read                - Read MDIO register
mdio_write               - Write MDIO register



