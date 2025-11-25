# User guide
# 用户指南

This tool can be run on real hardware (FPGAs) or in a simulation mode.
As the rowhammer attack exploits physical properties of cells in DRAM (draining charges), no bit flips can be observed in simulation mode.
However, the simulation mode is useful to test command sequences during the development.

该工具可以在真实硬件（FPGA）上运行，也可以在仿真模式下运行。
由于行锤击（rowhammer）攻击利用DRAM单元的物理特性（电荷泄漏），在仿真模式下无法观察到位翻转。
但是，仿真模式对于在开发过程中测试命令序列很有用。

The Makefile can be configured using environmental variables to modify the network configuration used and to select the target.
Currently, 4 boards are supported, each targeting different memory type:
| Board                      | Memory type      | TARGET                       |
|----------------------------|------------------|------------------------------|
| Arty A7                    | DDR3             | `arty`                       |
| ZCU104                     | DDR4 (SO-DIMM)   | `zcu104`                     |
| DDR Datacenter DRAM Tester | DDR4 (RDIMM)     | `ddr4_datacenter_test_board` |
| LPDDR4 Test Board          | LPDDR4 (SO-DIMM) | `lpddr4_test_board`          |

Makefile可以使用环境变量来配置网络配置和选择目标板。
目前支持4种开发板，每种针对不同的内存类型：
| 开发板                      | 内存类型         | 目标                         |
|----------------------------|------------------|------------------------------|
| Arty A7                    | DDR3             | `arty`                       |
| ZCU104                     | DDR4 (SO-DIMM)   | `zcu104`                     |
| DDR Datacenter DRAM Tester | DDR4 (RDIMM)     | `ddr4_datacenter_test_board` |
| LPDDR4 Test Board          | LPDDR4 (SO-DIMM) | `lpddr4_test_board`          |

```{note}
Although you choose a target board for the simulation, it doesn't require having a physical board.
Simulation is done entirely on your computer.
```

```{note}
虽然您为仿真选择了目标开发板，但这并不需要拥有实际的物理开发板。
仿真完全在您的计算机上进行。
```

For board-specific instructions refer to [Arty A7](arty.md), [ZCU104](zcu104.md), [DDR4 Datacenter DRAM Tester](ddr4_datacenter_dram_tester.md) and [LPDDR4 Test Board](lpddr4_tb.md) chapters.
The rest of this chapter describes operations that are common for all supported boards.

对于板卡特定的说明，请参考[Arty A7](arty.md)、[ZCU104](zcu104.md)、[DDR4 Datacenter DRAM Tester](ddr4_datacenter_dram_tester.md)和[LPDDR4 Test Board](lpddr4_tb.md)章节。
本章节的其余部分描述了所有支持板卡的通用操作。


## Network USB adapter setup
## 网络USB适配器设置

In order to control the Rowhammer platform an Ethernet connection is necessary. 
In case you want to use an USB Ethernet adapter for this purpose read the instructions below.

为了控制行锤击（Rowhammer）平台，需要以太网连接。
如果您想为此目的使用USB以太网适配器，请阅读以下说明。

1. Make sure you use a 1GbE USB network adapter
2. Figure out the MAC address for the USB network adapter:
   * Run ``sudo lshw -class network -short`` to get the list of all network interfaces
   * Check which of the devices uses the r8152 driver by running ``sudo ethtool -i <device>``
   * Display the link information for the device running ``sudo ip link show <device>`` and look for the mac address next to the ``link/ether`` field

1. 确保您使用1GbE USB网络适配器
2. 找出USB网络适配器的MAC地址：
   * 运行 ``sudo lshw -class network -short`` 获取所有网络接口的列表
   * 通过运行 ``sudo ethtool -i <device>`` 检查哪些设备使用r8152驱动程序
   * 运行 ``sudo ip link show <device>`` 显示设备的链接信息，并在 ``link/ether`` 字段旁查找MAC地址
3. Configure the USB network adapter to appear as network device ``fpga0`` using systemd
   * Create ``/etc/systemd/network/10-fpga0.link`` with the following contents:
      ```sh
      [Match]
      # Set this to the MAC address of the USB network adapter
      MACAddress=XX:XX:XX:XX:XX
      
      [Link]
      Name=fpga0
      ```

3. 使用systemd配置USB网络适配器显示为网络设备 ``fpga0``
   * 创建 ``/etc/systemd/network/10-fpga0.link`` 文件，内容如下：
      ```sh
      [Match]
      # 将此设置为USB网络适配器的MAC地址
      MACAddress=XX:XX:XX:XX:XX
      
      [Link]
      Name=fpga0
      ```

4. Configure the ``fpga0`` network device with a static IP address, always up (even when disconnected) and ignored by the network manager.
   * Make sure your ``/etc/network/interfaces`` file has the following line:
      ```sh
      source /etc/network/interfaces.d/*
      ```
   * Create ``/etc/network/interfaces.d/fpga0`` with the following contents:
      ```sh
      auto fpga0
      allow-hotplug fpga0
      iface fpga0 inet static
              address 192.168.100.100/24
      ```
   * Check that ``nmcli device`` says the state is ``connected (externally)`` otherwise run ``sudo systemctl restart NetworkManager``
   * Run ``ifup fpga0``

4. 配置 ``fpga0`` 网络设备使用静态IP地址，始终启用（即使断开连接），并被网络管理器忽略。
   * 确保您的 ``/etc/network/interfaces`` 文件包含以下行：
      ```sh
      source /etc/network/interfaces.d/*
      ```
   * 创建 ``/etc/network/interfaces.d/fpga0`` 文件，内容如下：
      ```sh
      auto fpga0
      allow-hotplug fpga0
      iface fpga0 inet static
              address 192.168.100.100/24
      ```
   * 检查 ``nmcli device`` 显示状态为 ``connected (externally)``，否则运行 ``sudo systemctl restart NetworkManager``
   * 运行 ``ifup fpga0``

5. Run ``sudo udevadm control --reload`` and then unplug the USB ethernet device and plug it back in
6. Check you have an ``fpga0`` interface and it has the correct IP address by running ``networkctl status``

5. 运行 ``sudo udevadm control --reload``，然后拔下USB以太网设备并重新插入
6. 通过运行 ``networkctl status`` 检查您是否拥有 ``fpga0`` 接口并且它具有正确的IP地址

```{note} 
In case you see ``libusb_open() failed with LIBUSB_ERROR_ACCESS`` when trying to use the rowhammer tester scripts with the USB ethernet adapter then it means that you have a permissions issue and need to allow access to the FTDI USB to serial port chip. Check the group listed for the tty's when running ``ls -l /dev/ttyUSB*`` and add the current user to this group by running ``sudo adduser <username> <group>``.
```

```{note} 
如果在尝试将行锤击测试脚本与USB以太网适配器一起使用时看到 ``libusb_open() failed with LIBUSB_ERROR_ACCESS`` 错误，这意味着您遇到了权限问题，需要允许访问FTDI USB转串口芯片。运行 ``ls -l /dev/ttyUSB*`` 查看tty列出的组，并通过运行 ``sudo adduser <username> <group>`` 将当前用户添加到该组。
```

(controlling-the-board)=
## Controlling the board
## 控制开发板

Board control is the same for both simulation and hardware runs.
In order to communicate with the board via EtherBone, the `litex_server` needs to be started with the following command:

仿真和硬件运行的板卡控制是相同的。
为了通过EtherBone与开发板通信，需要使用以下命令启动 `litex_server`：

```sh
export IP_ADDRESS=192.168.100.50  # optional, should match the one used during build
make srv
```

```sh
export IP_ADDRESS=192.168.100.50  # 可选，应与构建期间使用的IP地址匹配
make srv
```

```{warning}
If you want to run the simulation and the rowhammer scripts on a physical board at the same time,
you have to change the ``IP_ADDRESS`` variable, otherwise the simulation can conflict with the communication with your board.
```

```{warning}
如果您想同时在物理开发板上运行仿真和行锤击脚本，
您必须更改 ``IP_ADDRESS`` 变量，否则仿真可能与您的开发板通信发生冲突。
```

The build files (CSRs address list) must be up to date. It can be re-generated with `make` without arguments.

构建文件（CSR地址列表）必须是最新的。可以使用不带参数的 `make` 重新生成。

Then, in another terminal, you can use the Python scripts provided. *Remember to enter the Python virtual environment before running the scripts!* Also, the `TARGET` variable should be set to load configuration for the given target.
For example, to use the `leds.py` script, run the following:

然后，在另一个终端中，您可以使用提供的Python脚本。*记住在运行脚本之前进入Python虚拟环境！* 同时，应设置 `TARGET` 变量来为给定目标加载配置。
例如，要使用 `leds.py` 脚本，运行以下命令：

```sh
source ./venv/bin/activate
export TARGET=arty  # (or zcu104) required to load target configuration
cd rowhammer_tester/scripts/
python leds.py  # stop with Ctrl-C
```

```sh
source ./venv/bin/activate
export TARGET=arty  # （或zcu104）加载目标配置所需
cd rowhammer_tester/scripts/
python leds.py  # 使用Ctrl-C停止
```

## Hammering
## 行锤击

Rowhammer attacks can be run against a DRAM module. It can be then used for measuring cell retention.
For the complete list of scripts' modifiers, see `--help`.

可以对DRAM模块运行行锤击攻击。然后可以用于测量单元保持性。
有关脚本修饰符的完整列表，请参阅 `--help`。

There are two versions of a rowhammer script:

有两个版本的行锤击脚本：

- `rowhammer.py` - this one uses regular memory access via EtherBone to fill/check the memory (slower)
- `hw_rowhammer.py` - BIST blocks will be used to fill/check the memory (much faster, but with some limitations regarding fill pattern)

- `rowhammer.py` - 此脚本使用通过EtherBone的常规内存访问来填充/检查内存（较慢）
- `hw_rowhammer.py` - 将使用BIST块来填充/检查内存（快得多，但在填充模式方面有一些限制）

BIST blocks are faster and are the intended way of running Row Hammer Tester.

BIST块更快，是运行行锤击测试器的预期方式。

Hammering of a row is done by reading it. There are two ways to specify a number of reads:

行的锤击是通过读取它来完成的。有两种方法指定读取次数：

- `--read_count N`           - one pass of `N` reads
- `--read_count_range K M N` - multiple passes of reads, as generated by `range(K, M, N)`

- `--read_count N`           - 一次传递的 `N` 次读取
- `--read_count_range K M N` - 多次传递的读取，如 `range(K, M, N)` 生成的

Regardless of which one is used, the number of reads in one pass is divided equally between hammered rows.
If a user specifies `--read_count 1000`, then each row will be hammered 500 times.

无论使用哪种方式，一次传递中的读取次数在锤击行之间平均分配。
如果用户指定 `--read_count 1000`，那么每行将被锤击500次。

Normally hammering is being performed via DMA, but there is also an alternative way with `--payload-executor`.
It bypasses the DMA and directly talks with the PHY.
That allows the user to issue specific activation, refresh and precharge commands.

通常锤击是通过DMA执行的，但也有使用 `--payload-executor` 的替代方法。
它绕过DMA并直接与PHY通信。
这允许用户发出特定的激活、刷新和预充电命令。


### Attack modes
### 攻击模式

Different attack and row selection modes can be used, but only one of them can be specified at the same time.

可以使用不同的攻击和行选择模式，但一次只能指定其中一种。

- `--hammer-only`

  Only hammers a pair of rows, without doing any error checks or reports.

  For example following command will hammer rows 4 and 6 1000 times total (so 500 times each):

  ```sh
  (venv) $ python hw_rowhammer.py --hammer-only 4 6 --read_count 1000
  ```

- `--hammer-only`

  仅锤击一对行，不进行任何错误检查或报告。

  例如，以下命令将总共锤击第4行和第6行1000次（每行500次）：

  ```sh
  (venv) $ python hw_rowhammer.py --hammer-only 4 6 --read_count 1000
  ```

- `--all-rows`

  Row pairs generated from `range(start-row, nrows - row-pair-distance, row-jump)` expression will be hammered.

  Generated pairs are of form `(i, i + row-pair-distance)`.
  Default values for used arguments are:

  | argument              | default |
  | --------------------- | ------- |
  | `--start-row`         | 0       |
  | `--row-jump`          | 1       |
  | `--row-pair-distance` | 2       |

  So you can run following command to hammer rows `(0, 2), (1, 3), (2, 4)`:

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --nrows 5
  ```

- `--all-rows`

  将锤击从 `range(start-row, nrows - row-pair-distance, row-jump)` 表达式生成的行对。

  生成的行对形式为 `(i, i + row-pair-distance)`。
  使用参数的默认值为：

  | 参数                  | 默认值  |
  | --------------------- | ------- |
  | `--start-row`         | 0       |
  | `--row-jump`          | 1       |
  | `--row-pair-distance` | 2       |

  因此您可以运行以下命令来锤击行 `(0, 2), (1, 3), (2, 4)`：

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --nrows 5
  ```

  And in case of:

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --start-row 10 --nrows 16 --row-jump 2 --row-distance 3
  ```

  hammered pairs would be: `(10, 13), (12, 15)`.

  In a special case, where `--row-pair-distance` is 0, you can check how hammering a single row affects other rows.
  Normally activations and deactivations are achieved with row reads using the DMA, but in this case it is not possible.
  Because the same row is being read all the time, no deactivation command would be sent by the DMA.
  In this case, `--payload-executor` is required as it bypasses the DMA and sends deactivation commands on its own.

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --nrows 5 --row-pair-distance 0 --payload-executor
  ```

  在以下情况下：

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --start-row 10 --nrows 16 --row-jump 2 --row-distance 3
  ```

  锤击的行对将是：`(10, 13), (12, 15)`。

  在 `--row-pair-distance` 为0的特殊情况下，您可以检查锤击单行如何影响其他行。
  通常激活和去激活是通过使用DMA的行读取来实现的，但在这种情况下是不可能的。
  因为始终在读取同一行，DMA不会发送去激活命令。
  在这种情况下，需要 `--payload-executor`，因为它绕过DMA并自行发送去激活命令。

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --nrows 5 --row-pair-distance 0 --payload-executor
  ```

- `--row-pairs sequential`

  Hammers pairs of `(start-row, start-row + n)`, where `n` is from 0 to `nrows`.

  ```sh
  (venv) $ python hw_rowhammer.py --row-pairs sequential --start-row 4 --nrows 10
  ```

  Command above, would hammer following set of row pairs:

  ```
  (4, 4 + 0)
  (4, 4 + 1)
  ...
  (4, 4 + 9)
  (4, 4 + 10)
  ```

- `--row-pairs sequential`

  锤击 `(start-row, start-row + n)` 对，其中 `n` 从0到 `nrows`。

  ```sh
  (venv) $ python hw_rowhammer.py --row-pairs sequential --start-row 4 --nrows 10
  ```

  上述命令将锤击以下行对集合：

  ```
  (4, 4 + 0)
  (4, 4 + 1)
  ...
  (4, 4 + 9)
  (4, 4 + 10)
  ```

- `--row-pairs const`

  Two rows specified with the `const-rows-pair` parameter will be hammered:

  ```sh
  (venv) $ python hw_rowhammer.py --row-pairs const --const-rows-pair 4 6
  ```

- `--row-pairs const`

  将锤击使用 `const-rows-pair` 参数指定的两行：

  ```sh
  (venv) $ python hw_rowhammer.py --row-pairs const --const-rows-pair 4 6
  ```

- `--row-pairs random`

  `nrows` pairs of random rows will be hammered. Row numbers will be between `start-row` and `start-row + nrows`.

  ```sh
  (venv) $ python hw_rowhammer.py --row-pairs random --start-row 4 --nrows 10
  ```

- `--row-pairs random`

  将锤击 `nrows` 对随机行。行号将在 `start-row` 和 `start-row + nrows` 之间。

  ```sh
  (venv) $ python hw_rowhammer.py --row-pairs random --start-row 4 --nrows 10
  ```

### Patterns
### 模式

User can choose a pattern that memory will be initially filled with:

用户可以选择内存最初填充的模式：

- `all_0` - all bits set to 0
- `all_1` - all bits set to 1
- `01_in_row` - alternating 0's and 1's in a row (`0xaaaaaaaa` in hex)
- `01_per_row` - all 0's in odd-numbered rows, all 1's in even rows
- `rand_per_row` - random values for all rows

- `all_0` - 所有位设置为0
- `all_1` - 所有位设置为1
- `01_in_row` - 在一行中交替的0和1（十六进制为 `0xaaaaaaaa`）
- `01_per_row` - 奇数编号行全为0，偶数行全为1
- `rand_per_row` - 所有行的随机值

### Example output
### 示例输出

```sh
(venv) $ python hw_rowhammer.py --nrows 512 --read_count 10e6 --pattern 01_in_row --row-pairs const --const-rows-pair 54 133 --no-refresh
Preparing ...
WARNING: only single word patterns supported, using: 0xaaaaaaaa
Filling memory with data ...
Progress: [========================================] 16777216 / 16777216
Verifying written memory ...
Progress: [========================================] 16777216 / 16777216 (Errors: 0)
OK
Disabling refresh ...
Running Rowhammer attacks ...
read_count: 10000000
  Iter 0 / 1 Rows = (54, 133), Count = 10.00M / 10.00M
Reenabling refresh ...
Verifying attacked memory ...
Progress: [========================================] 16777216 / 16777216 (Errors: 30)
Bit-flips for row    53: 5
Bit-flips for row    55: 11
Bit-flips for row   132: 12
Bit-flips for row   134: 3
```

```sh
(venv) $ python hw_rowhammer.py --nrows 512 --read_count 1e5 --pattern 01_in_row --row-pairs const --const-rows-pair 54 133 --no-refresh
准备中 ...
警告：仅支持单字模式，使用：0xaaaaaaaa
用数据填充内存 ...
进度：[========================================] 16777216 / 16777216
验证写入的内存 ...
进度：[========================================] 16777216 / 16777216（错误：0）
正常
禁用刷新 ...
运行行锤击攻击 ...
read_count：10000000
  迭代 0 / 1 行 = (54, 133)，计数 = 10.00M / 10.00M
重新启用刷新 ...
验证攻击的内存 ...
进度：[========================================] 16777216 / 16777216（错误：30）
第53行的位翻转：5
第55行的位翻转：11
第132行的位翻转：12
第134行的位翻转：3
```

### Row selection examples
### 行选择示例

```{warning}
Attacks are performd on a single bank.
By default it is bank 0.
To change the bank that is being attacked use the `--bank` flag.
```

```{warning}
攻击在单个存储体上执行。
默认情况下是存储体0。
要更改被攻击的存储体，请使用 `--bank` 标志。
```

- Select row pairs from row 3 (`--start-row`) to row 59 (`--nrows`) where the next pair is 5 rows away (`--row-jump`) from the previous one:

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --start-row 3 --nrows 60 --row-jump 5 --no-refresh --read_count 10e4
  ```

- 从第3行（`--start-row`）到第59行（`--nrows`）选择行对，其中下一对距离前一对5行（`--row-jump`）：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --start-row 3 --nrows 60 --row-jump 5 --no-refresh --read_count 10e4
  ```

- Select row pairs from row 3 to to row 59 without a distance between subsequent pairs (no `--row-jump`), which means that rows pairs are incremented by 1:

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --start-row 3 --nrows 60 --no-refresh --read_count 10e4
  ```

- 从第3行到第59行选择行对，后续对之间没有距离（无 `--row-jump`），这意味着行对递增1：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --start-row 3 --nrows 60 --no-refresh --read_count 10e4
  ```

- Select all row pairs (from 0 to nrows - 1):

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --nrows 512 --no-refresh --read_count 10e4
  ```

- 选择所有行对（从0到nrows - 1）：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --nrows 512 --no-refresh --read_count 10e4
  ```

- Select all row pairs (from 0 to nrows - 1) and save the error summary in JSON format to the `test` directory:

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --nrows 512 --no-refresh --read_count 10e4 --log-dir ./test
  ```

- 选择所有行对（从0到nrows - 1）并将错误摘要以JSON格式保存到 `test` 目录：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --nrows 512 --no-refresh --read_count 10e4 --log-dir ./test
  ```

- Select only one row (42 in this case) and save the error summary in JSON format to the `test` directory:

  ```sh
  (venv) $ python hw_rowhammer.py --pattern all_1 --row-pairs const --const-rows-pair 42 42 --no-refresh --read_count 10e4 --log-dir ./test
  ```

- 仅选择一行（本例中为第42行）并将错误摘要以JSON格式保存到 `test` 目录：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern all_1 --row-pairs const --const-rows-pair 42 42 --no-refresh --read_count 10e4 --log-dir ./test
  ```

- Select all rows (from 0 to nrows - 1) and hammer them one by one 1M times each.

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --nrows 100 --row-pair-distance 0 --payload-executor --no-refresh --read_count 1e6
  ```

- 选择所有行（从0到nrows - 1）并逐一锤击每行100万次。

  ```sh
  (venv) $ python hw_rowhammer.py --all-rows --nrows 100 --row-pair-distance 0 --payload-executor --no-refresh --read_count 1e6
  ```

```{note}
Since for a single ended attack row activation needs to be triggered the `--payload-executor` switch is required.
The size of the payload memory is set by default to 1024 bytes and can be changed using the `--payload-size` switch.
```

```{note}
由于单端攻击需要触发行激活，因此需要 `--payload-executor` 开关。
有效载荷内存的大小默认设置为1024字节，可以使用 `--payload-size` 开关更改。
```

### Cell retention measurement examples
### 单元保持性测量示例

- Select all row pairs (from 0 to nrows - 1) and perform a set of tests for different read count values, starting from 10e4 and ending at 10e5 with a step of 20e4 (`--read_count_range [start stop step]`):

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --nrows 512 --no-refresh --read_count_range 10e4 10e5 20e4
  ```

- 选择所有行对（从0到nrows - 1）并对不同的读取计数值执行一系列测试，从10e4开始，到10e5结束，步长为20e4（`--read_count_range [start stop step]`）：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --all-rows --nrows 512 --no-refresh --read_count_range 10e4 10e5 20e4
  ```

- Perform set of tests for different read count values in a given range for one row pair (50, 100):

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs const --const-rows-pair 50 100 --no-refresh --read_count_range 10e4 10e5 20e4
  ```

- 对一个行对（50，100）在给定范围内的不同读取计数值执行一系列测试：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs const --const-rows-pair 50 100 --no-refresh --read_count_range 10e4 10e5 20e4
  ```

- Perform set of tests for different read count values in a given range for one row pair (50, 100) and stop the test execution as soon as a bitflip is found:

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs const --const-rows-pair 50 100 --no-refresh --read_count_range 10e4 10e5 20e4 --exit-on-bit-flip
  ```

- 对一个行对（50，100）在给定范围内的不同读取计数值执行一系列测试，并在发现位翻转后立即停止测试执行：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs const --const-rows-pair 50 100 --no-refresh --read_count_range 10e4 10e5 20e4 --exit-on-bit-flip
  ```

- Perform set of tests for different read count values in a given range for one row pair (50, 100) and save the error summary in JSON format to the `test` directory:

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs const --const-rows-pair 50 100 --no-refresh --read_count_range 10e4 10e5 20e4 --log-dir ./test
  ```

- 对一个行对（50，100）在给定范围内的不同读取计数值执行一系列测试，并将错误摘要以JSON格式保存到 `test` 目录：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs const --const-rows-pair 50 100 --no-refresh --read_count_range 10e4 10e5 20e4 --log-dir ./test
  ```

- Perform set of tests for different read count values in a given range for a sequence of attacks for different pairs, where the first row of a pair is 40 and the second one is a row of a number from range (40, nrows - 1):

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs sequential --start-row 40 --nrows 512 --no-refresh --read_count_range 10e3 10e4 10e3 --exit-on-bit-flip
  ```

- 对不同行对的一系列攻击在给定范围内的不同读取计数值执行一系列测试，其中一对的第一行是40，第二行是范围（40，nrows - 1）中的一行：

  ```sh
  (venv) $ python hw_rowhammer.py --pattern 01_in_row --row-pairs sequential --start-row 40 --nrows 512 --no-refresh --read_count_range 10e4 10e5 20e4
  ```

## Utilities
## 实用工具

Some of the scripts are simple and do not take command line arguments, others will provide help via `<script_name>.py --help` or `<script_name>.py -h`.

一些脚本很简单，不接受命令行参数，其他脚本将通过 `<script_name>.py --help` 或 `<script_name>.py -h` 提供帮助。

Few of the scripts accept a `--srv` option. With this option enabled, a program will start it's own instance of `litex_server` (the user doesn't need to run `make srv` to {ref}`control the board <controlling the board>`)

少数脚本接受 `--srv` 选项。启用此选项后，程序将启动自己的 `litex_server` 实例（用户不需要运行 `make srv` 来{ref}`控制开发板 <controlling the board>`）

### Run LEDs demo - `leds.py`
### 运行LED演示 - `leds.py`

Displays a simple "bouncing" animation using the LEDs on Arty-A7 board, with the light moving from side to side.

在Arty-A7开发板上使用LED显示简单的"弹跳"动画，光线从一侧移动到另一侧。

`-t TIME_MS` or `--time-ms TIME_MS` option can be used to adjust LED switching interval.

可以使用 `-t TIME_MS` 或 `--time-ms TIME_MS` 选项来调整LED切换间隔。

### Check version - `version.py`
### 检查版本 - `version.py`

Prints the data stored in the LiteX identification memory:

打印存储在LiteX识别内存中的数据：

- hardware platform identifier
- source code git hash
- build date

- 硬件平台标识符
- 源代码git哈希
- 构建日期

Example output:

示例输出：

```sh
(venv) python version.py
Row Hammer Tester SoC on xc7k160tffg676-1, git: e7854fdd16d5f958e616bbb4976a97962ee9197d 2022-07-24 15:46:52
```

```sh
(venv) python version.py
xc7k160tffg676-1上的行锤击测试器SoC，git：e7854fdd16d5f958e616bbb4976a97962ee9197d 2022-07-24 15:46:52
```

### Check CSRs - `dump_regs.py`
### 检查CSR - `dump_regs.py`

Dumps values of all CSRs.
Example output of `dump_regs.py`:

转储所有CSR的值。
`dump_regs.py` 的示例输出：

```sh
0x82000000: 0x00000000 ctrl_reset
0x82000004: 0x12345678 ctrl_scratch
0x82000008: 0x00000000 ctrl_bus_errors
0x82002000: 0x00000000 uart_rxtx
0x82002004: 0x00000001 uart_txfull
0x82002008: 0x00000001 uart_rxempty
0x8200200c: 0x00000003 uart_ev_status
0x82002010: 0x00000000 uart_ev_pending
...
```

```{note}
Note that ctrl_scratch value is 0x12345678. This is the reset value of this register.
If you are getting a different, this may indicate a problem.
```

```{note}
请注意ctrl_scratch值是0x12345678。这是该寄存器的复位值。
如果您得到不同的值，这可能表示存在问题。
```

### Initialize memory - `mem.py`
### 初始化内存 - `mem.py`

Before the DRAM memory can be used, the initialization and leveling must be performed. The `mem.py` script serves this purpose.

在可以使用DRAM内存之前，必须执行初始化和均衡。`mem.py` 脚本用于此目的。

Expected output:

预期输出：

```sh
(venv) $ python mem.py
(LiteX output)
--========== Initialization ============--
Initializing SDRAM @0x40000000...
Switching SDRAM to software control.
Read leveling:
  m0, b0: |11111111111110000000000000000000| delays: 06+-06
  m0, b1: |00000000000000111111111111111000| delays: 21+-08
  m0, b2: |00000000000000000000000000000011| delays: 31+-01
  m0, b3: |00000000000000000000000000000000| delays: -
  m0, b4: |00000000000000000000000000000000| delays: -
  m0, b5: |00000000000000000000000000000000| delays: -
  m0, b6: |00000000000000000000000000000000| delays: -
  m0, b7: |00000000000000000000000000000000| delays: -
  best: m0, b01 delays: 21+-07
  m1, b0: |11111111111111000000000000000000| delays: 07+-07
  m1, b1: |00000000000000111111111111111000| delays: 22+-08
  m1, b2: |00000000000000000000000000000001| delays: 31+-00
  m1, b3: |00000000000000000000000000000000| delays: -
  m1, b4: |00000000000000000000000000000000| delays: -
  m1, b5: |00000000000000000000000000000000| delays: -
  m1, b6: |00000000000000000000000000000000| delays: -
  m1, b7: |00000000000000000000000000000000| delays: -
  best: m1, b01 delays: 22+-08
Switching SDRAM to hardware control.
Memtest at 0x40000000 (2MiB)...
  Write: 0x40000000-0x40200000 2MiB
  Read: 0x40000000-0x40200000 2MiB
Memtest OK
Memspeed at 0x40000000 (2MiB)...
  Write speed: 12MiB/s
  === Initialization succeeded. ===
Proceeding ...

Memtest (basic)
OK

Memtest (random)
OK
```

```sh
(venv) $ python mem.py
（LiteX输出）
--========== 初始化 ============--
在@0x40000000初始化SDRAM...
将SDRAM切换到软件控制。
读取均衡：
  m0, b0: |11111111111110000000000000000000| 延迟：06+-06
  m0, b1: |00000000000000111111111111111000| 延迟：21+-08
  m0, b2: |00000000000000000000000000000011| 延迟：31+-01
  m0, b3: |00000000000000000000000000000000| 延迟：-
  m0, b4: |00000000000000000000000000000000| 延迟：-
  m0, b5: |00000000000000000000000000000000| 延迟：-
  m0, b6: |00000000000000000000000000000000| 延迟：-
  m0, b7: |00000000000000000000000000000000| 延迟：-
  最佳：m0, b01 延迟：21+-07
  m1, b0: |11111111111111000000000000000000| 延迟：07+-07
  m1, b1: |00000000000000111111111111111000| 延迟：22+-08
  m1, b2: |00000000000000000000000000000001| 延迟：31+-00
  m1, b3: |00000000000000000000000000000000| 延迟：-
  m1, b4: |00000000000000000000000000000000| 延迟：-
  m1, b5: |00000000000000000000000000000000| 延迟：-
  m1, b6: |00000000000000000000000000000000| 延迟：-
  m1, b7: |00000000000000000000000000000000| 延迟：-
  最佳：m1, b01 延迟：22+-08
将SDRAM切换到硬件控制。
在0x40000000（2MiB）进行内存测试...
  写入：0x40000000-0x40200000 2MiB
  读取：0x40000000-0x40200000 2MiB
内存测试正常
在0x40000000（2MiB）进行内存速度测试...
  写入速度：12MiB/s
  === 初始化成功。 ===
继续...

内存测试（基本）
正常

内存测试（随机）
正常
```

### Enter BIOS - `bios_console.py`
### 进入BIOS - `bios_console.py`

Sometimes it may happen that memory initialization fails when running the `mem.py` script.
This is most likely due to using boards that allow to swap memory modules, such as ZCU104.

有时在运行 `mem.py` 脚本时可能发生内存初始化失败。
这很可能是由于使用允许交换内存模块的开发板，例如ZCU104。

Memory initialization procedure is performed by the CPU instantiated inside the FPGA fabric.
The CPU runs the LiteX BIOS.
In case of memory training failure it may be helpful to access the LiteX BIOS console.

内存初始化程序由FPGA结构内实例化的CPU执行。
CPU运行LiteX BIOS。
在内存训练失败的情况下，访问LiteX BIOS控制台可能会有帮助。

If the script cannot find a serial terminal emulator program on the host system, it will fall back
to `litex_term` which is shipped with LiteX. It is however advised to install `picocom`/`minicom`
as `litex_term` has worse performance.

如果脚本在主机系统上找不到串行终端仿真程序，它将回退到
LiteX附带的 `litex_term`。但是建议安装 `picocom`/`minicom`，
因为 `litex_term` 性能较差。

In the BIOS console use the `help` command to get information about other available commands.
To re-run memory initialization and training type `reboot`.

在BIOS控制台中使用 `help` 命令获取有关其他可用命令的信息。
要重新运行内存初始化和训练，请输入 `reboot`。

```{note}
To close picocom/minicom enter CTRL+A+X key combination.
```

```{note}
要关闭picocom/minicom，请输入CTRL+A+X组合键。
```
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

i2c_dev                  - List/Set I2C controller(s)
i2c_scan                 - Scan for I2C slaves
i2c_read                 - Read over I2C
i2c_write                - Write over I2C
i2c_reset                - Reset I2C line state

sdram_spd                - Read SDRAM SPD EEPROM
sdram_mr_write           - Write SDRAM Mode Register
sdram_force_bitslip      - Force write leveling Bitslip
sdram_rst_bitslip        - Reset write leveling Bitslip
sdram_force_dat_delay    - Force write leveling Dat delay
sdram_rst_dat_delay      - Reset write leveling Dat delay
sdram_cal                - Calibrate SDRAM
sdram_test               - Test SDRAM
sdram_init               - Initialize SDRAM (Init + Calibration)
sdram_force_cmd_delay    - Force write leveling Cmd delay
sdram_rst_cmd_delay      - Reset write leveling Cmd delay
sdram_force_wrphase      - Force write phase
sdram_force_rdphase      - Force read phase
sdram_hw_test            - Run SDRAM HW-accelerated memtest
sdram_bist               - Run SDRAM Build-In Self-Test

LiteX BIOS，可用命令：

leds                     - 设置LED值
flush_l2_cache           - 刷新L2缓存
flush_cpu_dcache         - 刷新CPU数据缓存
crc                      - 计算地址空间一部分的CRC32
ident                    - 系统标识符
help                     - 打印此帮助

serialboot               - 从串行引导（SFL）
boot                     - 从内存引导

mem_cmp                  - 比较内存内容
mem_speed                - 测试内存速度
mem_test                 - 测试内存访问
mem_copy                 - 复制地址空间
mem_write                - 写入地址空间
mem_read                 - 读取地址空间
mem_list                 - 列出可用内存区域

i2c_dev                  - 列出/设置I2C控制器
i2c_scan                 - 扫描I2C从设备
i2c_read                 - 通过I2C读取
i2c_write                - 通过I2C写入
i2c_reset                - 重置I2C线路状态

sdram_spd                - 读取SDRAM SPD EEPROM
sdram_mr_write           - 写入SDRAM模式寄存器
sdram_force_bitslip      - 强制写均衡位滑移
sdram_rst_bitslip        - 重置写均衡位滑移
sdram_force_dat_delay    - 强制写均衡数据延迟
sdram_rst_dat_delay      - 重置写均衡数据延迟
sdram_cal                - 校准SDRAM
sdram_test               - 测试SDRAM
sdram_init               - 初始化SDRAM（初始化+校准）
sdram_force_cmd_delay    - 强制写均衡命令延迟
sdram_rst_cmd_delay      - 重置写均衡命令延迟
sdram_force_wrphase      - 强制写阶段
sdram_force_rdphase      - 强制读阶段
sdram_hw_test            - 运行SDRAM硬件加速内存测试
sdram_bist               - 运行SDRAM内置自测试
Example:

$ python ddr4_mr_gen.py --cl=17
DDR4 Timing Settings:
cl:  17
cwl: 9
DDR4 Electrical Settings:
rtt_nom: 40ohm
rtt_wr:  120ohm
ron:     34ohm
Commands to be used with LiteX BIOS:
sdram_mr_write 0 100
sdram_mr_write 1 769
sdram_mr_write 2 512
sdram_cal

示例：

$ python ddr4_mr_gen.py --cl=17
DDR4时序设置：
cl：17
cwl：9
DDR4电气设置：
rtt_nom：40ohm
rtt_wr：120ohm
ron：34ohm
与LiteX BIOS一起使用的命令：
sdram_mr_write 0 100
sdram_mr_write 1 769
sdram_mr_write 2 512
sdram_cal



```sh
(venv) $ python bios_console.py
LiteX Crossover UART created: /dev/pts/4
Using serial backend: auto
picocom v3.1

port is        : /dev/pts/4
flowcontrol    : none
baudrate is    : 1000000
parity is      : none
databits are   : 8
stopbits are   : 1
escape is      : C-a
local echo is  : no
noinit is      : no
noreset is     : no
hangup is      : no
nolock is      : no
send_cmd is    : sz -vv
receive_cmd is : rz -vv -E
imap is        :
omap is        :
emap is        : crcrlf,delbs,
logfile is     : none
initstring     : none
exit_after is  : not set
exit is        : no

Type [C-a] [C-h] to see available commands
Terminal ready
ad speed: 9MiB/s

--============== Boot ==================--
Booting from serial...
Press Q or ESC to abort boot completely.
sL5DdSMmkekro
            Timeout
No boot medium found

--============= Console ================--

litex>
```

```sh
(venv) $ python bios_console.py
LiteX交叉UART已创建：/dev/pts/4
使用串行后端：自动
picocom v3.1

端口是        ：/dev/pts/4
流控制        ：无
波特率是      ：1000000
奇偶校验是    ：无
数据位是      ：8
停止位是      ：1
转义是        ：C-a
本地回显是    ：否
noinit是      ：否
noreset是     ：否
挂机是        ：否
nolock是      ：否
发送命令是    ：sz -vv
接收命令是    ：rz -vv -E
imap是        ：
omap是        ：
emap是        ：crcrlf,delbs,
日志文件是    ：无
初始字符串    ：无
exit_after是  ：未设置
退出是        ：否

输入[C-a] [C-h]查看可用命令
终端就绪
ad速度：9MiB/s

--============== 引导 ==================--
从串行引导...
按Q或ESC完全中止引导。
sL5DdSMmkekro
            超时
未找到引导介质

--============= 控制台 ================--

litex>
```

#### Perform memory tests from the BIOS
#### 从BIOS执行内存测试

After entering the BIOS, you may want to perform a memory test using utilities built into the BIOS itself.
There are a couple ways to do such:

进入BIOS后，您可能想要使用BIOS本身内置的实用程序执行内存测试。
有几种方法可以做到这一点：

- `mem_test` - performs a series of writes and reads to check if values read back are the same as those previously written.
  It is limited by a 32-bit address bus, so only 4 GiB of address space can be tested.
  You can get origin of the RAM space using `mem_list` command.
- `sdram_test` - basically `mem_test`, but predefined for first 1/32 of defined RAM region size.
- `sdram_hw_test` - similar to `mem_test`, but accesses the SDRAM directly using DMAs, so it is not limited to 4 GiB.
  It requires passing 2 arguments (`origin` and `size`) with a 3rd optional argument being `burst_length`.
  When using `sdram_hw_test` you don't have to offset the `origin` like in the case of `mem_test`.
  `size` is a number of bytes to test and `burst_length` is a number of full transfer writes to the SDRAM, before reading and checking written content.
  The default value for `burst_length` is 1, which means that after every write, a check is performed.
  Generally, bigger `burst_length` means faster operation.

- `mem_test` - 执行一系列写入和读取操作，以检查读回的值是否与之前写入的值相同。
  它受32位地址总线限制，因此只能测试4 GiB的地址空间。
  您可以使用 `mem_list` 命令获取RAM空间的起始地址。
- `sdram_test` - 基本上是 `mem_test`，但预定义用于已定义RAM区域大小的前1/32。
- `sdram_hw_test` - 类似于 `mem_test`，但使用DMA直接访问SDRAM，因此不限于4 GiB。
  它需要传递2个参数（`origin` 和 `size`），第3个可选参数是 `burst_length`。
  使用 `sdram_hw_test` 时，您不必像 `mem_test` 情况下那样偏移 `origin`。
  `size` 是要测试的字节数，`burst_length` 是在读取和检查写入内容之前向SDRAM执行的完整传输写入次数。
  `burst_length` 的默认值是1，这意味着每次写入后都会执行检查。
  一般来说，较大的 `burst_length` 意味着更快的操作。

### Test with BIST - `mem_bist.py`
### 使用BIST测试 - `mem_bist.py`

A script written to test BIST block functionality. Two tests are available:

编写用于测试BIST块功能的脚本。提供两个测试：

- `test-modules` - memory is initialized and then a series of errors is introduced (on purpose).
  Then BIST is used to check the content of the memory. If the number of errors detected is equal to the number
  of errors introduced, the test is passed.
- `test-memory` - simple test that writes a pattern in the memory, reads it, and checks if the content is correct.
  Both write and read operations are done via BIST.

- `test-modules` - 内存被初始化，然后（故意）引入一系列错误。
  然后使用BIST检查内存内容。如果检测到的错误数等于引入的错误数，则测试通过。
- `test-memory` - 简单测试，在内存中写入模式，读取它，并检查内容是否正确。
  写入和读取操作都通过BIST完成。

### Run benchmarks - `benchmark.py`
### 运行基准测试 - `benchmark.py`

Benchmarks memory access performance. There are two subcommands available:

基准测试内存访问性能。有两个子命令可用：

- `etherbone` - measure performance of the EtherBone bridge
- `bist` - measure performance of DMA DRAM access using the BIST modules

- `etherbone` - 测量EtherBone桥的性能
- `bist` - 使用BIST模块测量DMA DRAM访问性能

Example output:

示例输出：

```sh
(venv) $  python benchmark.py etherbone read 0x10000 --burst 255
Using generated target files in: build/lpddr4_test_board
Running measurement ...
Elapsed = 4.189 sec
Size    = 256.000 KiB
Speed   = 61.114 KiBps

(venv) $  python benchmark.py bist read
Using generated target files in: build/lpddr4_test_board
Filling memory before reading measurements ...
Progress: [========================================] 16777216 / 16777216
Running measurement ...
Progress: [========================================] 16777216 / 16777216 (Errors: 0)
Elapsed = 1.591 sec
Size    = 512.000 MiB
Speed   = 321.797 MiBps
```

```sh
(venv) $  python benchmark.py etherbone read 0x10000 --burst 255
使用生成的目标文件：build/lpddr4_test_board
运行测量...
耗时 = 4.189秒
大小 = 256.000 KiB
速度 = 61.114 KiBps

(venv) $  python benchmark.py bist read
使用生成的目标文件：build/lpddr4_test_board
在读取测量前填充内存...
进度：[========================================] 16777216 / 16777216
运行测量...
进度：[========================================] 16777216 / 16777216（错误：0）
耗时 = 1.591秒
大小 = 512.000 MiB
速度 = 321.797 MiBps
```

### Use logic analyzer - `analyzer.py`
### 使用逻辑分析仪 - `analyzer.py`

This script utilizes the Litescope functionality to gather debug information about
signals in the LiteX system. In-depth Litescope documentation [is here](https://github.com/enjoy-digital/litex/wiki/Use-LiteScope-To-Debug-A-SoC).

该脚本利用Litescope功能收集LiteX系统中信号的调试信息。详细的Litescope文档[在这里](https://github.com/enjoy-digital/litex/wiki/Use-LiteScope-To-Debug-A-SoC)。

As you can see in Litescope documentation, Litescope analyzer needs to be instantiated in your design. Example design with analyzer added was provided as `arty_litescope` TARGET.
As the name implies it can be run using Arty board. You can use `rowhammer_tester/targets/arty_litescope.py` as a reference for your own Litescope-enabled targets.

如Litescope文档中所示，需要在您的设计中实例化Litescope分析仪。提供了一个添加了分析仪的示例设计作为 `arty_litescope` 目标。
如名称所示，它可以使用Arty开发板运行。您可以使用 `rowhammer_tester/targets/arty_litescope.py` 作为您自己启用Litescope目标的参考。

To build `arty_litescope` example and upload it to device, follow instructions below:

要构建 `arty_litescope` 示例并将其上传到设备，请按照以下说明操作：

1. In root directory run:

   ```sh
   export TARGET=arty_litescope
   make build
   make upload
   ```

   `analyzer.csv` file will be created in the root directory.

1. 在根目录中运行：

   ```sh
   export TARGET=arty_litescope
   make build
   make upload
   ```

   将在根目录中创建 `analyzer.csv` 文件。

2. We need to copy it to target's build dir before using `analyzer.py`.

   ```sh
   cp analyzer.csv build/arty_litescope/
   ```

2. 在使用 `analyzer.py` 之前，我们需要将其复制到目标的构建目录。

   ```sh
   cp analyzer.csv build/arty_litescope/
   ```

3. Then start litex-server with:

   ```sh
   make srv
   ```

4. And execute analyzer script in a separate shell:

   ```sh
   export TARGET=arty_litescope
   python rowhammer_tester/scripts/analyzer.py
   ```

   Results will be stored in `dump.vcd` file and can be viewed with gtkwave:

   ```sh
   gtkwave dump.vcd
   ```

3. 然后启动litex-server：

   ```sh
   make srv
   ```

4. 在单独的shell中执行分析仪脚本：

   ```sh
   export TARGET=arty_litescope
   python rowhammer_tester/scripts/analyzer.py
   ```

   结果将存储在 `dump.vcd` 文件中，可以使用gtkwave查看：

   ```sh
   gtkwave dump.vcd
   ```

## Simulation
## 仿真

Select `TARGET`, generate intermediate files & run simulation:

选择 `TARGET`，生成中间文件并运行仿真：

```sh
export TARGET=arty # (or zcu104)
make sim
```

```sh
export TARGET=arty # （或zcu104）
make sim
```

This command will generate intermediate files & simulate them with Verilator.
After simulation has finished, a signals dump can be investigated using [gtkwave](http://gtkwave.sourceforge.net/):

该命令将生成中间文件并使用Verilator进行仿真。
仿真完成后，可以使用[gtkwave](http://gtkwave.sourceforge.net/)检查信号转储：

```sh
gtkwave build/$TARGET/gateware/sim.fst
```

```{warning}
The repository contains a wrapper script around `sudo` which disallows LiteX to interfere with
the host network configuration. This forces the user to manually configure a TUN interface for valid
communication with the simulated device.
```

```{warning}
该仓库包含一个 `sudo` 包装脚本，禁止LiteX干扰
主机网络配置。这迫使用户手动配置TUN接口以实现与
仿真设备的有效通信。
```

1. Create the TUN interface:

   ```sh
   tunctl -u $USER -t litex-sim
   ```

1. 创建TUN接口：

   ```sh
   tunctl -u $USER -t litex-sim
   ```

2. Configure the IP address of the interface:

   ```sh
   ifconfig litex-sim 192.168.100.1/24 up
   ```

2. 配置接口的IP地址：

   ```sh
   ifconfig litex-sim 192.168.100.1/24 up
   ```

3. Optionally allow network traffic on this interface:

   ```sh
   iptables -A INPUT -i litex-sim -j ACCEPT
   iptables -A OUTPUT -o litex-sim -j ACCEPT
   ```

3. 可选择允许此接口上的网络流量：

   ```sh
   iptables -A INPUT -i litex-sim -j ACCEPT
   iptables -A OUTPUT -o litex-sim -j ACCEPT
   ```

```{note}
Typing `make ARGS="--sim"` will cause LiteX to generate only intermediate files and stop right after that.
```

```{note}
输入 `make ARGS="--sim"` 将导致LiteX仅生成中间文件，然后立即停止。
```
