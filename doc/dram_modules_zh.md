dram_modules_zh.md
# DRAM 模块
# DRAM modules

当构建[rowhammer_tester/targets](https://github.com/antmicro/rowhammer-tester/tree/master/rowhammer_tester/targets)中的目标时，
可以使用 `--module` 参数指定自定义的 DRAM 模块。要查找每个目标的默认模块，请查看 `--help` 的输出结果。
When building one of the targets in [rowhammer_tester/targets](https://github.com/antmicro/rowhammer-tester/tree/master/rowhammer_tester/targets), a custom DRAM module can be specified using the `--module` argument. To find the default modules for each target, check the output of `--help`.

```{note}
指定不同的 DRAM 模块在允许轻松更换 DRAM 模块的板子上最有意义，
例如在 ZCU104 上。在其他板子上则需要拆除 DRAM 芯片并焊接新的芯片。
```
```{note}
Specifying different DRAM module makes most sense on boards that allow to easily replace the DRAM module,
such as on ZCU104. On other boards it would be necessary to desolder the DRAM chip and solder a new one.
```

(adding-new-modules)=

## 添加新模块
## Adding new modules

[LiteDRAM](https://github.com/enjoy-digital/litedram) 控制器提供了对许多 DRAM 模块的开箱即用支持。
支持的模块可以在 [litedram/modules.py](https://github.com/enjoy-digital/litedram/blob/master/litedram/modules.py) 中找到。
如果某个模块未在此列出，则可以添加新的定义。
[LiteDRAM](https://github.com/enjoy-digital/litedram) controller provides out-of-the-box support for many DRAM modules.
Supported modules can be found in [litedram/modules.py](https://github.com/enjoy-digital/litedram/blob/master/litedram/modules.py).
If a module is not listed there, you can add a new definition.

为了使开发更加方便，可以直接在 rowhammer-tester 仓库中的文件 [rowhammer_tester/targets/modules.py](https://github.com/antmicro/rowhammer-tester/blob/master/rowhammer_tester/targets/modules.py) 中添加模块。
这些定义将在 LiteDRAM 中的定义之前使用。
To make development more convenient, modules can be added in the rowhammer-tester repository directly in file [rowhammer_tester/targets/modules.py](https://github.com/antmicro/rowhammer-tester/blob/master/rowhammer_tester/targets/modules.py). These definitions will be used before definitions in LiteDRAM.

```{note}
确保模块正常工作后，应向 LiteDRAM 提交拉取请求以添加对该模块的支持。
```
```{note}
After ensuring that the module works correctly, a Pull Request to LiteDRAM should be created to add support for the module.
```

要添加新的模块定义，请参考现有的定义。新模块类应该继承自 `SDRAMModule`（或辅助类，如 `DDR4Module`）。
模块的时序/几何值必须从相关的 DRAM 模块数据手册中获取。继承自 `SDRAMModule` 的类中的时序以纳秒为单位指定。
时序值也可以指定为二元组 `(ck, ns)`，其中 `ck` 是时钟周期数，`ns` 是纳秒数（可以为 `None`）。将使用最高的时序值。
To add a new module definition, use the existing ones as a reference. New module class should derive from `SDRAMModule` (or the helper classes, e.g. `DDR4Module`). Timing/geometry values for a module have to be obtained from the relevant DRAM module's datasheet. The timings in classes deriving from `SDRAMModule` are specified in nanoseconds. The timing value can also be specified as a 2-element tuple `(ck, ns)`, in which case `ck` is the number of clock cycles and `ns` is the number of nanoseconds (and can be `None`). The highest of the resulting timing values will be used.

## SPD EEPROM

在使用 DIMM/SO-DIMM 模块的板子上（例如 ZCU104），可以读取 DRAM 模块的 [SPD EEPROM 内存](https://en.wikipedia.org/wiki/Serial_presence_detect)内容。
SPD 包含内存控制器使用 DRAM 模块所需的几个重要参数。
SPD EEPROM 可以通过 I2C 总线读取。
On boards that use DIMM/SO-DIMM modules (e.g. ZCU104) it is possible to read the contents of the DRAM modules's [SPD EEPROM memory](https://en.wikipedia.org/wiki/Serial_presence_detect).
SPD contains several essential module parameters that the memory controller needs in order to use the DRAM module.
SPD EEPROM can be read over I2C bus.

### 读取 SPD EEPROM
### Reading SPD EEPROM

要读取 SPD 内存，请使用脚本 `rowhammer_tester/scripts/spd_eeprom.py`。
首先按照 {ref}`controlling-the-board` 中描述准备环境。
然后使用以下命令读取 SPD EEPROM 的内容并保存到文件中，例如：
To read the SPD memory use the script `rowhammer_tester/scripts/spd_eeprom.py`.
First prepare the environment as described in {ref}`controlling-the-board`.
Then use the following command to read the contents of SPD EEPROM and save it to a file, for example:

```sh
python rowhammer_tester/scripts/spd_eeprom.py read MTA4ATF51264HZ-3G2J1.bin
```

文件的内容可用于获取 DRAM 模块参数。
使用以下命令检查参数：
The contents of the file can then be used to get DRAM module parameters.
Use the following command to examine the parameters:

```sh
python rowhammer_tester/scripts/spd_eeprom.py show MTA4ATF51264HZ-3G2J1.bin 125e6
```

请注意，必须将系统时钟频率作为参数传递以确定控制器时钟周期中的时序值。
Note that system clock frequency must be passed as an argument to determine timing values in controller clock cycles.

### 使用 SPD 数据
### Using SPD data

内存控制器能够在系统启动期间设置从 SPD EEPROM 读取的时序。
这里唯一的要求是 SoC 构建了 I2C 控制器，并且 I2C 引脚路由到 (R)DIMM 模块。
系统用户无需额外操作。
时序将自动设置。
The memory controller is able to set the timings read from an SPD EEPROM during system boot.
The only requirement here is that the SoC is built with I2C controller, and I2C pins are routed to the (R)DIMM module.
There is no additional action required from system user.
The timings will be set automatically.