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
    python logs2plot.py xxx.json --aggressors-vs-victims --annotate bitflips --no-colorbar --png xxx.png

    # 研究用高精度
    python logs2plot.py log.json -gr 256 -gc 256 --annotate bitflips
    
    读取范围 --read_count_range 10e5 10e6 20e5

1.数据保持时间
    # 基础测试：
    python hw_rowhammer.py --no-attack-time 5e9 --no-refresh --pattern all_1 (T = 5s)
    # 数据保持时间（发生第一次bit翻转所需时间）：
    python find_min_bitflip_time.py 
    # bit翻转数量随等待时间变化 + 热力图可视化 + 折线图
    python bitflip_time_test.py 
    python plot_bitflip_time.py 
    python quick_plot.py --all

2.HCfirst（发生第一个bit翻转需要的锤击数，能否读到攻击所花费时间，方便与retention比较）
    # 单边攻击：前部：(0)-(1)-...-(10)
    python hw_rowhammer.py --all-rows --start-row 180 --row-jump 1 --nrows 182 --row-pair-distance 0  --read_count 2e4 --pattern all_1 --no-refresh --payload-executor --save 

    # 攻击时间增大，是否会出现大面积bit翻转
    --read_count 5e6    759ms   无
    --read_count 6e6    908ms   开始出现  结论：攻击会促进易损行的电荷泄露
    --read_count 7e6    1060ms  开始出现


3.单边、双边、大半径攻击（）
    # 单边攻击：测试：（10）
    python hw_rowhammer.py --row-pairs const --const-rows-pair 10 10 --read_count 5e4 --no-refresh --payload-executor 
    # 单边攻击：前部：(0)-(1)-...-(10)
    python hw_rowhammer.py --all-rows --start-row 0 --row-jump 1 --nrows 10 --row-pair-distance 0  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
    # 单边攻击：中部：(4090)-(4091)-...-(4100)
    python hw_rowhammer.py --all-rows --start-row 4090 --row-jump 1 --nrows 10 --row-pair-distance 0  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
    # 单边攻击：后部：(8181)-(8182)-...-(8191)
    python hw_rowhammer.py --all-rows --start-row 8181 --row-jump 1 --nrows 10 --row-pair-distance 0  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
    # 特殊位置攻击：24 7523 5419
    

    # 1-双倍攻击：测试：(10,12)
    python hw_rowhammer.py --row-pairs const --const-rows-pair 10 12 --read_count 5e4 --no-refresh
    # 1-双边攻击：前部：(0,2)-(1,3)-...-(8,10) 
    python hw_rowhammer.py --all-rows --start-row 0 --row-jump 1 --nrows 10 --row-pair-distance 2  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
    # 1-双边攻击：中部：(4090,4092)-(4091,4093)-...-(4098,4100)
    python hw_rowhammer.py --all-rows --start-row 4090 --row-jump 1 --nrows 10 --row-pair-distance 2  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
    # 1-双边攻击：后部：(8181,8183)-(8182,8184)-...-(8189,8191)
    python hw_rowhammer.py --all-rows --start-row 8181 --row-jump 1 --nrows 10 --row-pair-distance 2  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
    # 2-双边攻击：(0,2)-(1,3)-...-(8,10) --row-pair-distance 2
    # 3-双边攻击：(0,3)-(1,4)-...-(7,10) --row-pair-distance 3
    # 4-双边攻击：(0,4)-(1,5)-...-(6,10) --row-pair-distance 4
# 注：看下--nrows 10 是不是这样用的


3.数据模式 
    # Checkerboard 棋盘格
    python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 5e4 --pattern 01_in_row --no-refresh
    # Rowstripe 行条纹
    python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 5e4 --pattern 01_per_row --no-refresh
    # All_1 全1
    # All_0 全0

(All_1 全1)(venv) 
$ python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 5e4--pattern all_1 --no-refresh

(All_0 全0)(venv) 
$ python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 20e6 --pattern all_0 --no-refresh

rand_per_row 有问题，不要使用。（可以在rowhammer.py观察到）

```







        "read_count": 10000000,
        "pair_10_10": {
            "hammer_row_1": 10,
            "hammer_row_2": 10,
            "errors_in_rows": {
                "9": {
                    "row": 9,
                    "col": {
                        "56": [
                            68
                        ],
                        "160": [
                            98,
                            114
                        ],
                        ...
                    },
                    "bitflips": 26
                },
                "11": {
                    "row": 11,
                    "col": {
                        "216": [
                            97
                        ],
                        "560": [
                            2,
                            18
                        ]
                    },
                    "bitflips": 3
                }
            }
        },

这里col都是8的倍数，原因：DDR3系统有128位数据宽度（32 dfi_databits × 4 nphases = 128位）
"phy": {
    "databits": 16,      // 物理内存芯片的数据宽度
    "dfi_databits": 32,  // DFI接口的数据宽度  
    "nphases": 4         // DDR 相位数
}
所以8列（16bit*8）对应1组数据(128bit)，即将1024列分成128组，每组8列（128bit）
 "col": 
                        "56": [
                            68    //第（56+68%16=60列），第4bit翻转
                        ],
                        "160": [
                            98,   //第（160+98%16=166列），第2bit翻转
                            114   //第（160+114%16=167列），第2bit翻转
                        ],