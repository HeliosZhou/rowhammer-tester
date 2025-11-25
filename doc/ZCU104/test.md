# Rowhammer Tester Scripts 脚本说明文档

本目录包含了 Rowhammer Tester 项目的各种测试和分析脚本。这些脚本提供了从基础硬件测试到高级 Rowhammer 攻击分析的完整工具套件。

## 📋 目录结构

```
rowhammer_tester/scripts/
├── __init__.py                 # Python 包初始化文件
├── analyzer.py                 # LiteScope 逻辑分析仪
├── benchmark.py                # 性能基准测试
├── bios_console.py             # BIOS 控制台访问
├── decode_ddr5_dimms.py        # DDR5 DIMM 解码工具
├── dump_regs.py                # 内存寄存器转储
├── execute_payload.py          # 载荷命令执行演示
├── hw_rowhammer.py             # 硬件加速 Rowhammer 攻击
├── leds.py                     # LED 控制测试
├── logs2dq.py                  # DQ 数据线分析
├── logs2plot.py                # 攻击日志绘图工具
├── logs2vis.py                 # F4PGA 数据库可视化
├── mem.py                      # 基础 DRAM 内存测试
├── mem_bist.py                 # 硬件 BIST 内存测试
├── read_level.py               # DRAM 读取电平校准
├── rowhammer.py                # Rowhammer 攻击基础框架
├── sim_runner.py               # 仿真运行器
├── sim_runner_timed.py         # 带时间的仿真运行器
├── spd_eeprom.py               # SPD EEPROM 读取
├── utils.py                    # 通用工具库
├── version.py                  # 版本信息
└── playbook/                   # 攻击脚本集合
```

## 🔧 核心测试脚本

### `rowhammer.py` - Rowhammer攻击基础框架
**功能**: Rowhammer攻击的基类和核心逻辑实现
- 提供行选择、攻击模式配置、数据验证等功能
- 支持软件和硬件两种攻击方式
- 其他 Rowhammer 相关脚本的基础框架

#### 主要参数详解

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
默认第0行开始（--start-row 0），行数每次增加1（--row-jump 1），行对间隔2（--row-pair-distance 2）
(venv) $ python hw_rowhammer.py --all-rows --nrows 5  
(0, 2), (1, 3), (2, 4)
(venv) $ python hw_rowhammer.py --all-rows --start-row 10 --nrows 16 --row-jump 2 --row-distance 3
(10, 13), (12, 15)
(venv) $ python hw_rowhammer.py --all-rows --nrows 5 --row-pair-distance 0 --payload-executor
单行

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
(venv) $ python  hw_rowhammer.py --no-attack-time 1e9 --no-refresh --pattern all_1
(T = 0.1-20s)



2.单边、双边、大半径攻击（10e6次观察row11）
最大攻击次数16e6次，否则超过数据保持时间
(10) (venv) $ python hw_rowhammer.py --row-pairs const --const-rows-pair 10 10 --read_count 10e6 --no-refresh --payload-executor --payload-size 0x30000 --log-dir ./test --log-filename xxx
# 如果出现载荷内存不足错误，增加载荷内存大小
(10) (venv) $ python hw_rowhammer.py --row-pairs const --const-rows-pair 10 10 --read_count 17e6 --no-refresh --payload-executor --payload-size 0x10000 --log-dir ./test

(0)-(1)-...-(10)
 $ python hw_rowhammer.py --all-rows --start-row 0 --row-jump 1 --nrows 20 --row-pair-distance 0  --read_count 5e4 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx

(10,12)(venv) $ python hw_rowhammer.py --row-pairs const --const-rows-pair 10 12 --read_count 5e4 --no-refresh
(0,2)-(1,3)-...-(8,10) 
 $ python hw_rowhammer.py --all-rows --start-row 0 --row-jump 1 --nrows 10 --row-pair-distance 2  --read_count 10e6 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
(0,3)-(1,4)-...-(7,10) 
 $ python hw_rowhammer.py --all-rows --start-row 0 --row-jump 1 --nrows 10 --row-pair-distance 3  --read_count 10e6 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx
(0,4)-(1,5)-...-(6,10) 
 $ python hw_rowhammer.py --all-rows --start-row 0 --row-jump 1 --nrows 10 --row-pair-distance 4  --read_count 10e6 --pattern all_1 --no-refresh --payload-executor --log-dir ./test --log-filename xxx

16383行
上0-30 中8190-8220 下16353-16383


3.数据模式 
(Checkerboard 棋盘格)(venv) 
$ python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 20e6 --pattern 01_in_row --no-refresh

(Rowstripe 行条纹)(venv) 
$ python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 20e6 --pattern 01_per_row --no-refresh

(All_1 全1)(venv) 
$ python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 20e6 --pattern all_1 --no-refresh

(All_0 全0)(venv) 
$ python hw_rowhammer.py --nrows 512 --row-pairs const --const-rows-pair 10 14 --read_count 20e6 --pattern all_0 --no-refresh

rand_per_row 有问题，不要使用。（可以在rowhammer.py观察到）

```



### `hw_rowhammer.py` - 硬件加速Rowhammer攻击
**功能**: 使用 FPGA 硬件 BIST 模块执行高速 Rowhammer 攻击
- 继承自 rowhammer.py，提供硬件加速功能
- 比软件方式速度更快，能产生更密集的内存访问
- 专门用于测试 DRAM 的 Rowhammer 漏洞

**特点**:
- 硬件加速，攻击速度极快
- 支持多行同时攻击
- 自动错误检测和报告
- 使用 `--log-dir` 参数生成 JSON 日志文件供可视化分析

**日志生成示例**:
```bash
# 生成 JSON 日志文件用于可视化
python hw_rowhammer.py --nrows 512 --read_count 10e7 --const-rows-pair 54 133 --log-dir ./logs
```


**使用示例**:
```bash
# 基本用法 - 显示单个攻击
python logs2plot.py attack_log.json

# 生成攻击者对比图
python logs2plot.py attack_log.json --aggressors-vs-victims

# 保存为PNG并显示位翻转数量
python logs2plot.py attack_log.json --annotate bitflips --png result.png

# 自定义分组大小
python logs2plot.py attack_log.json -gr 32 -gc 32
```

### `logs2vis.py` - F4PGA数据库可视化
**功能**: 使用 F4PGA Database Visualizer 生成攻击日志可视化
- 每次攻击生成独立的可视化结果
- 提供更高级的可视化功能

### `logs2dq.py` - DQ数据线分析
**功能**: 分析 bit 翻转在不同 DQ 数据线上的分布
- 生成按 DQ 分组的条形图
- 帮助理解硬件故障模式和内存颗粒问题




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