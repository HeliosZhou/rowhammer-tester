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



**使用示例**:
```bash
0.通用代码
    export TARGET=zcu104 && export IP_ADDRESS=192.168.100.50  
    生成json文件 --log-dir ./test
    
    画图  (venv) $ python logs2plot.py --aggressors-vs-victims your_error_summary.json
    # 快速概览
    python logs2plot.py log.json --aggressors-vs-victims -gr 64 -gc 64 (每把所有行分成64组展示)

    # 详细分析
    python logs2plot.py log.json --annotate bitflips --no-colorbar --png detailed.png

    # 发布用图表
    python logs2plot.py ./result/a-hammer/a-hammer_single_side_r0-10_rc40K.json --aggressors-vs-victims --annotate bitflips --no-colorbar --png logs2plot.py a-hammer_single_side_r0-10_rc40K.png

    # 研究用高精度
    python logs2plot.py log.json -gr 256 -gc 256 --annotate bitflips
    
    读取范围 --read_count_range 10e5 10e6 20e5

    # 数据处理（地址正确映射）
    python convert_address.py --input-file ./test/error_summary_2023-07-13_16-04-01.json 
    python convert_address.py /home/hc/rowhammer-tester/rowhammer_tester/scripts/result/retention/bitflip_time_test_20251126_182933.json

1.数据保持时间
    # 基础测试：
    python hw_rowhammer.py --no-attack-time 5e9 --no-refresh --pattern all_1 (T = 5s)

    # 测试1：数据保持时间（发生第一次bit翻转所需时间）：
    # 结果1：T = 1s
    python find_min_bitflip_time.py 

    # 测试2：bit翻转数量随等待时间变化 + 热力图可视化 + 折线图
    # 结果2：指数关系，分布无明显规律，存在弱单元容易泄露
    python bitflip_time_test.py 
    python plot_bitflip_time.py 
    python quick_heatmap.py 

2.HCfirst（发生第一个bit翻转需要的锤击数，能否读到攻击所花费时间，方便与retention比较）
    # 测试单边攻击：(10)
    python hw_rowhammer.py --row-pairs const --const-rows-pair 10 10 --read_count 5e4 --nrows 8192 --no-refresh --payload-executor 

    # 测试1：使用脚本进行大范围测试 精度100    
    # 结果1：HCfirst = 10000-20000 存在脆弱行
    python test_hcfirst_simple.py --start 0 --count 128 --precision 100 
    python test_hcfirst_simple.py --start 4032 --count 128 --precision 100
    python test_hcfirst_simple.py --start 8064 --count 128 --precision 100
    python plot_hcfirst.py HCfirst_*.json 
    python plot_hcfirst.py --compact --output compact_view.png  # 紧凑视图，自动分段显示
    python plot_hcfirst.py HCfirst_rows_8064-8191.json 

    # 测试2：攻击时间增大，是否会出现大面积bit翻转
    # 结果2：read_count = 6e6 即六百万次锤击后出现异常翻转，时间908ms < retention 1s
    --read_count 5e6    759ms   无
    --read_count 6e6    908ms   开始出现  结论：攻击会促进易损行的电荷泄露
    --read_count 7e6    1060ms  开始出现  注：无法再高，超过了payload executor 容量，要重跑Bit流

3.数据模式 
    # 测试1：改变数据模式，测试20-29行，4万次锤击，单边攻击
    # 结论1：数据模式敏感性排序 All_0 > 01_in_row ≈ rand_per_row > 01_per_row > All_1
    # 结论2：All_0模式最容易受攻击（730+ bitflips），All_1最稳定（260+ bitflips）

    # Checkerboard 棋盘格 (581 bitflips)
    python hw_rowhammer.py --all-rows --start-row 20 --row-jump 1 --nrows 30 --row-pair-distance 0  --read_count 4e4 --pattern 01_in_row --no-refresh --payload-executor --save datapattern 
    # Rowstripe 行条纹 (526 bitflips)
    python hw_rowhammer.py --all-rows --start-row 20 --row-jump 1 --nrows 30 --row-pair-distance 0  --read_count 4e4 --pattern 01_per_row --no-refresh --payload-executor --save datapattern  
    # All_1 全1 (260 bitflips - 最稳定)
    python hw_rowhammer.py --all-rows --start-row 20 --row-jump 1 --nrows 30 --row-pair-distance 0  --read_count 4e4 --pattern all_1  --no-refresh --payload-executor --save datapattern  
    # All_0 全0 (730+ bitflips - 最敏感)
    python hw_rowhammer.py --all-rows --start-row 20 --row-jump 1 --nrows 30 --row-pair-distance 0  --read_count 4e4 --pattern all_0  --no-refresh --payload-executor --save datapattern  
    # 随机数据 (550 bitflips)
    python hw_rowhammer.py --all-rows --start-row 20 --row-jump 1 --nrows 30 --row-pair-distance 0  --read_count 4e4 --pattern rand_per_row --no-refresh --payload-executor --save datapattern  
    # 绘图
    python logs2vis.py /home/hc/rowhammer-tester/rowhammer_tester/scripts/result/a-hammer/a-hammer_single_side_r1000-2000_rc40K.json /home/hc/rowhammer-tester/rowhammer_tester/scripts/result/a-hammer/ --aggressors-vs-victims
    
    python logs2plot.py /home/hc/rowhammer-tester/rowhammer_tester/scripts/result/datapattern/datapattern_single_side_r20-30_rc40K_pat_rand_per_row.json --aggressors-vs-victims --annotate bitflips --png /home/hc/rowhammer-tester/rowhammer_tester/scripts/result/datapattern/datapattern_single_side_r20-30_rc40K_pat_rand_per_row.png


4.单边攻击
    # 单边攻击：基础测试：（10）
    python hw_rowhammer.py --row-pairs const --const-rows-pair 10 10 --nrows 8192 --read_count 9e6 --no-refresh --payload-executor --save a-hammer
    # 单边攻击：基础测试：(0)-(1)-...-(10)
    python hw_rowhammer.py --all-rows --start-row 0 --row-jump 1 --nrows 10 --row-pair-distance 0  --read_count 3e4 --pattern all_1 --no-refresh --payload-executor --save a-hammer 

    # 测试1：边界值测试
    # 结论1：（0，1，2）（8193-8191）行异常翻转
    python hw_rowhammer.py --row-pairs const --const-rows-pair 5 5 --nrows 8192 --read_count 3e4 --no-refresh --payload-executor --save a-hammer
    （0）
    Bit-flips for row     1: 11  # 异常
    Bit-flips for row  4985: 24
    （1）
    Bit-flips for row     0: 48  # 异常
    Bit-flips for row  1272: 135
    Bit-flips for row  1280: 32
    （2）
    Bit-flips for row     3: 28  # 异常，不管--read_count 加到多大都只有row3翻转
    （3）
    Bit-flips for row     2: 36  # 正常，从row3开始一切正常
    Bit-flips for row     4: 111
    （4）
    Bit-flips for row     3: 18  # 正常
    Bit-flips for row     5: 22
    （5）
    Bit-flips for row     4: 51  # 正常
    Bit-flips for row     6: 107    
    ...
    （8182）
    Bit-flips for row  8181: 31  # 正常
    Bit-flips for row  8183: 18  # 从8183开始异常
    （8183）
    Bit-flips for row  8182: 65
    Bit-flips for row  8190: 183 # 以下异常，应该是8184
    （8184）
    Bit-flips for row  8182: 31  # 异常
    Bit-flips for row  8185: 21
    Bit-flips for row  8187: 88
    Bit-flips for row  8190: 93
    ...
    （8190）


    # 测试2：遍历0-8191行，看是否能找到异常值（受害者行未明显翻转，即存在子阵列）--10h
    # 结论2：周期性异常，6行正常，10行不正常，且正常行呈现奇偶规律
    python hw_rowhammer.py --all-rows --start-row 1000 --row-jump 1 --nrows 2000 --row-pair-distance 0  --read_count 4e4 --pattern all_1 --no-refresh --payload-executor --save a-hammer



5、双边、大半径攻击（）
    # 1-双边攻击：测试：(10,12)
    python hw_rowhammer.py --row-pairs const --const-rows-pair 1111 1113 --read_count 7e6 --pattern all_1 --no-refresh --nrows 8192 --save a-hammer

    # 2-双边攻击：(10,12)-(11,13)-...-(18,20) --row-pair-distance 2
    python hw_rowhammer.py --all-rows --start-row 10 --row-jump 1 --nrows 20 --row-pair-distance 2  --read_count 5e7 --pattern all_1 --no-refresh --payload-executor --save a-hammer

    # 3-双边攻击：(10,13)-(11,14)-...-(17,20) --row-pair-distance 3
    python hw_rowhammer.py --all-rows --start-row 10 --row-jump 1 --nrows 20 --row-pair-distance 3 --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --save a-hammer

    # 4-双边攻击：(10,14)-(11,15)-...-(16,20) --row-pair-distance 4
    python hw_rowhammer.py --all-rows --start-row 10 --row-jump 1 --nrows 20 --row-pair-distance 4  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --save a-hammer

# 注：看下--nrows 10 是不是这样用的

6.探索新的攻击模式
