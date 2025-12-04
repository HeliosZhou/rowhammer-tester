# Rowhammer Tester Scripts 脚本说明文档
本目录包含了 Rowhammer Tester 项目的各种测试和分析脚本。这些脚本提供了从基础硬件测试到高级 Rowhammer 攻击分析的完整工具套件。

## DRAM 结构以及项目测试说明
16384行 实际只测试8192行，即0-8191（1/8）


## 主要参数详解

**基础配置参数**:
- `--nrows NROWS`: 要测试的行数（默认512行）
- `--bank BANK`: 指定测试的内存Bank编号（默认0）
- `--column COLUMN`: 指定读取的列地址（默认512）
- `--start-row START_ROW`: 起始行号，测试范围为 [start, start+nrows)

**攻击强度配置**:
- `--read_count READ_COUNT`: 对每对地址执行的读取次数（单次测试）
- `--read_count_range START STOP STEP`: 读取次数范围测试，如 `1000 10000 1000` 表示从1000到10000，步长1000

**内存刷新控制**:
- `--no-refresh`: 禁用攻击期间的刷新命令（增加攻击效果）

**数据模式配置**:
- `--pattern`: 写入DRAM的数据模式
  - `all_0`: 全0模式
  - `all_1`: 全1模式  
  - `01_in_row`: 行内01交替
  - `01_per_row`: 按行01交替
  - `rand_per_row`: 每行随机数据

**行选择策略**:
- `--row-pairs`: 攻击行对的选择方式
  - `sequential`: 顺序选择相邻行对
  - `const`: 固定行对（需配合 `--const-rows-pair`）
  - `random`: 随机选择行对
- `--const-rows-pair ROW1 ROW2`: 指定固定的攻击行对，如 `--const-rows-pair 100 102`
- `--row-pair-distance DISTANCE`: 攻击行对之间的距离（默认1，即相邻行）

**攻击模式**:
- `--hammer-only ROW1 [ROW2...]`: 仅执行Rowhammer攻击，不进行完整测试
  - BIST/DMA模式：必须提供恰好2行
  - Payload Executor模式：可提供任意行数
- `--payload-executor`: 使用载荷执行器进行攻击（更精确的时序控制）

**全行测试**:
- `--all-rows`: 对所有行执行完整测试序列，
- `--row-jump JUMP`: 配合 `--all-rows` 使用，设置行间跳跃距离

**实验配置**:
- `--experiment-no NO`: 运行预配置的实验编号
- `--no-attack-time NANOSECONDS`: 不进行攻击，仅睡眠指定纳秒数（用于对照测试）
- `--data-inversion DIVISOR MASK`: 对受害者行的数据进行反转（除数，掩码）

**输出和日志**:
- `--srv`: 启动LiteX服务器模式
- `--log-dir LOG_DIR`: 指定输出文件目录，生成 `error_summary_<timestamp>.json` 文件供 `logs2plot.py` 使用
- `-v, --verbose`: 详细输出模式
- `--exit-on-bit-flip`: 发现bit翻转后立即退出测试

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


```
