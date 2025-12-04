# Rowhammer攻击流程与地址映射详细分析

## 概述

本文档详细分析了rowhammer-tester项目中的攻击流程、地址映射机制、bit翻转检测和硬件实现。通过深入阅读项目源码，本文档解释了从攻击执行到结果分析的完整技术流程。

## 项目架构

```
rowhammer-tester/
├── rowhammer_tester/
│   ├── gateware/              # FPGA硬件逻辑
│   │   ├── rowhammer.py       # DMA攻击模块
│   │   ├── bist.py            # Built-In Self Test模块
│   │   └── payload_executor.py # 有载荷执行器
│   ├── scripts/               # Python控制脚本
│   │   ├── hw_rowhammer.py    # 硬件加速攻击
│   │   ├── rowhammer.py       # 基础攻击类
│   │   ├── utils.py           # 工具函数和地址转换
│   │   └── convert_address.py # 地址映射转换
│   └── payload/               # 攻击负载库
└── doc/                       # 文档
```

---

## 第一部分：地址映射机制

### 1.1 DRAM地址结构

在DDR3内存中，一个物理地址需要映射为以下组件：
- **Bank**: 独立的存储区域（通常3-bit，8个Bank）
- **Row**: 行地址（通常14-bit，16384行）
- **Column**: 列地址（通常10-bit，1024列）

### 1.2 地址编码/解码实现

**核心类：`DRAMAddressConverter` (`utils.py`)**

```python
class DRAMAddressConverter:
    def __init__(self, *, colbits, rowbits, bankbits, address_align, 
                 dram_port_width, address_mapping='ROW_BANK_COL'):
        # 地址映射格式：| ROW | BANK | COL |
```

#### 编码过程 (逻辑地址 → 物理地址)
```python
def _encode(self, bank, row, col):
    # 地址格式: [ROW][BANK][COL]
    return reduce(or_, [
        masked(row, self.rowbits, self.bankbits + self.colbits),
        masked(bank, self.bankbits, self.colbits),  
        masked(col, self.colbits, 0),
    ])
```

#### 解码过程 (物理地址 → 逻辑地址)
```python  
def _decode(self, address):
    row = extract(address, self.rowbits, self.bankbits + self.colbits)
    bank = extract(address, self.bankbits, self.colbits)
    col = extract(address, self.colbits, 0)
    return bank, row, col
```

### 1.3 地址转换类型

1. **Bus地址** (`encode_bus/decode_bus`): CPU总线访问地址
2. **DMA地址** (`encode_dma/decode_dma`): DMA控制器使用的地址
3. **物理芯片地址**: 通过`convert_address.py`进一步转换

#### 物理芯片地址转换公式
```python
def convert_physical_address(original_bank, original_row, original_col, original_bit):
    new_bank = original_bank  # bank保持不变
    chip = original_bit // 64 + 1  # 计算chip值
    new_row = original_row  # row不变
    new_col = original_col + (original_bit % 64) // 8 + 1
    new_bit = (original_bit % 64) % 8
    return new_bank, new_row, new_col, new_bit, chip
```

---

## 第二部分：攻击执行流程

### 2.1 攻击类层次结构

```
RowHammer (基类)
    ↓
HwRowHammer (硬件加速)
```

### 2.2 基础攻击流程 (`RowHammer.run()`)

```python
def run(self, row_pairs, pattern_generator, read_count, row_progress=16, verify_initial=False):
    """主要攻击流程"""
    # 1. 准备阶段
    print('\nPreparing ...')
    row_patterns = pattern_generator(self.rows)
    
    # 2. 填充内存
    print('\nFilling memory with data ...')
    for row, n, base in self.row_access_iterator():
        memfill(self.wb, n, pattern=row_patterns[row], base=base, burst=255)
    
    # 3. 初始验证（可选）
    if verify_initial:
        errors = self.check_errors(row_patterns, row_progress=row_progress)
        
    # 4. 禁用刷新
    if self.no_refresh:
        self.wb.regs.controller_settings_refresh.write(0)
    
    # 5. 执行攻击
    if self.no_attack_time is not None:
        self.no_attack_sleep()  # 数据保持性测试
    else:
        for row_tuple in row_pairs:
            if self.payload_executor:
                self.payload_executor_attack(read_count=read_count, row_tuple=row_tuple)
            else:
                self.attack(row_tuple, read_count=read_count, progress_header=s)
    
    # 6. 重新启用刷新
    if self.no_refresh:
        self.wb.regs.controller_settings_refresh.write(1)
    
    # 7. 检测错误
    errors = self.check_errors(row_patterns, row_progress=row_progress)
    return self.display_errors(errors, read_count, bool(self.log_directory))
```

### 2.3 攻击方式对比

#### 2.3.1 标准DMA攻击 (`RowHammer.attack()`)

```python
def attack(self, row_tuple, read_count, progress_header=''):
    """使用标准rowhammer模块进行攻击"""
    # 配置攻击地址
    addresses = [self.converter.encode_dma(bank=self.bank, col=self.column, row=r) 
                for r in row_tuple]
    self.wb.regs.rowhammer_address1.write(addresses[0])
    self.wb.regs.rowhammer_address2.write(addresses[1])
    
    # 启动攻击
    self.wb.regs.rowhammer_enabled.write(1)
    
    # 等待完成
    while self.wb.regs.rowhammer_count.read() < read_count:
        time.sleep(0.001)
```

#### 2.3.2 硬件加速攻击 (`HwRowHammer.attack()`)

```python  
def attack(self, row_tuple, read_count, progress_header=''):
    """使用BIST模块进行硬件加速攻击"""
    # 配置攻击地址
    addresses = [self.converter.encode_dma(bank=self.bank, col=self.column, row=r) 
                for r in row_tuple]
    memwrite(self.wb, addresses, base=self.wb.mems.pattern_addr.base)
    
    # 配置BIST参数
    self.wb.regs.reader_mem_mask.write(0x00000000)  # 不递增地址
    self.wb.regs.reader_data_mask.write(len(row_tuple) - 1)  # 地址轮换
    self.wb.regs.reader_count.write(int(read_count))
    
    # 启动攻击
    self.wb.regs.reader_start.write(1)
    
    # 监控进度
    while not self.wb.regs.reader_ready.read():
        progress_count = self.wb.regs.reader_done.read()
        time.sleep(0.01)
```

#### 2.3.3 Payload执行器攻击

```python
def payload_executor_attack(self, read_count, row_tuple):
    """使用payload执行器进行精确控制的攻击"""
    payload = generate_payload_from_row_list(
        read_count=read_count,
        row_sequence=row_tuple,
        timings=self.settings.timing,
        bankbits=self.settings.geom.bankbits,
        bank=self.bank,
        payload_mem_size=self.wb.mems.payload.size,
        refresh=not self.no_refresh,
        sys_clk_freq=sys_clk_freq,
        verbose=self.verbose,
    )
    execute_payload(self.wb, payload)
```

---

## 第三部分：Bit翻转检测机制

### 3.1 错误检测流程

#### 3.1.1 标准检测 (`RowHammer.check_errors()`)

```python
def check_errors(self, row_patterns, row_progress=16):
    """检查指定行中的错误"""
    row_errors = {}
    for row, n, base in self.row_access_iterator():
        # 逐行检查
        errors = memcheck(self.wb, n, pattern=row_patterns[row], 
                         base=base, burst=255)
        row_errors[row] = [(addr, data, row_patterns[row]) for addr, data in errors]
    return row_errors
```

#### 3.1.2 硬件加速检测 (`HwRowHammer.check_errors()`)

```python
def check_errors(self, row_pattern):
    """使用硬件BIST模块检测错误"""
    errors = hw_memtest(self.wb, 0x0, self.wb.mems.main_ram.size, [row_pattern])
    
    row_errors = defaultdict(list)
    for e in errors:
        # 将错误地址解码为bank/row/col
        addr = self.wb.mems.main_ram.base + e.offset * dma_data_bytes
        bank, row, col = self.converter.decode_bus(addr)
        base_addr = min(self.addresses_per_row(row))
        row_errors[row].append(((addr - base_addr) // 4, e.data, e.expected))
    
    return dict(row_errors)
```

### 3.2 错误统计和报告

```python
def display_errors(self, row_errors, read_count, do_error_summary=False):
    """显示和统计bit翻转错误"""
    err_dict = {}
    for row in row_errors:
        if len(row_errors[row]) > 0:
            # 计算bit翻转数量
            flips = sum(self.bitflips(value, expected) 
                       for addr, value, expected in row_errors[row])
            print(f"Bit-flips for row {row}: {flips}")
            
            # 详细分析每个错误
            cols = {}
            for i, word, expected in row_errors[row]:
                base_addr = min(self.addresses_per_row(row))
                addr = base_addr + 4 * i
                bank, _row, col = self.converter.decode_bus(addr)
                
                # 记录bit翻转位置
                bitflips = self.bitflip_list(word, expected)
                cols[col] = bitflips
                
            # 构建错误摘要
            if do_error_summary:
                err_dict[str(row)] = {
                    'bank': bank,
                    'row': _row,
                    'col': cols,
                    'bitflips': flips
                }
    
    return err_dict
```

---

## 第四部分：FPGA硬件实现

### 4.1 Rowhammer DMA模块 (`rowhammer.py`)

```python
class RowHammerDMA(Module, AutoCSR, AutoDoc, ModuleDoc):
    """Row Hammer DMA攻击器
    
    配置两个不同行的地址，启用后交替读取，
    导致DRAM控制器反复开启/关闭行"""
    
    def __init__(self, dma):
        # CSR寄存器
        self.enabled = CSRStorage()      # 启用/禁用攻击
        self.address1 = CSRStorage()     # 攻击地址1
        self.address2 = CSRStorage()     # 攻击地址2  
        self.count = CSRStatus()         # 攻击计数
        
        # 地址轮换逻辑
        self.comb += Case(counter[0], {
            0: address.eq(self.address1.storage),
            1: address.eq(self.address2.storage),
        })
```

### 4.2 BIST模块 (`bist.py`)

```python
class BISTModule(Module):
    """Built-In Self Test模块
    
    提供模式化的内存访问，支持复杂的攻击序列"""
    
    # 核心组件：
    # - PatternMemory: 存储攻击模式
    # - AddressSelector: 地址选择器  
    # - RowDataInverter: 数据反转器
```

#### BIST写入器

```python
class BISTWriter(BISTModule, AutoCSR):
    """BIST内存写入器"""
    def __init__(self, dram_port, pattern_mem, **kwargs):
        # DMA写入逻辑
        self.submodules.dma = LiteDRAMDMAWriter(dram_port)
        # 模式内存连接
        # 地址掩码配置
```

#### BIST读取器

```python  
class BISTReader(BISTModule, AutoCSR):
    """BIST内存读取器，支持错误检测"""
    def __init__(self, dram_port, pattern_mem, **kwargs):
        # DMA读取逻辑
        self.submodules.dma = LiteDRAMDMAReader(dram_port)
        # 错误检测FIFO
        self.submodules.error_fifo = SyncFIFO([...], 32)
        # 数据比较逻辑
```

### 4.3 Payload执行器 (`payload_executor.py`)

#### 指令格式
```
指令格式 (32-bit):
- OP_CODE   (3-bit): 操作类型
- TIMESLICE (6-bit): 执行周期  
- ADDRESS   (23-bit): 目标地址

支持的操作:
- NOOP: 空操作
- ACT:  激活行
- PRE:  预充电
- REF:  刷新
- READ: 读取
- LOOP: 循环
```

#### 指令编码器
```python  
class Encoder:
    """Payload指令编码器"""
    def encode(self, op_code, **kwargs):
        if op_code == OpCode.LOOP:
            # 循环指令格式
            return encode_loop(count, jump)
        elif op_code == OpCode.ACT:
            # 激活指令格式  
            return encode_act(timeslice, bank, row)
```

---

## 第五部分：攻击模式和策略

### 5.1 行对选择策略

#### 单边攻击 (Single-sided)
```python
# 攻击单一行，检测相邻行的bit翻转
row_pairs = [(target_row, target_row)]  # --row-pair-distance 0
```

#### 双边攻击 (Double-sided)  
```python
# 攻击受害行两边的行
row_pairs = [(target_row - 1, target_row + 1)]  # --row-pair-distance 2
```

#### 大半径攻击
```python
# 攻击距离更远的行对
row_pairs = [(target_row - n, target_row + n)]  # --row-pair-distance 2*n
```

### 5.2 数据模式

#### 固定模式
```python
def patterns_const(rows, value):
    """所有行使用相同模式"""
    return {row: value for row in rows}

# 使用示例：
# --pattern all_0: 全0模式 (最敏感)
# --pattern all_1: 全1模式 (最稳定)
```

#### 棋盘格模式
```python  
def patterns_alternating_per_row(rows):
    """偶数行全1，奇数行全0"""
    return {row: 0xffffffff if row % 2 == 0 else 0x00000000 for row in rows}
```

#### 随机模式
```python
def patterns_random_per_row(rows, seed=42):
    """每行随机模式"""
    rng = random.Random(seed)
    return {row: rng.randint(0, 2**32 - 1) for row in rows}
```

### 5.3 特殊测试模式

#### 数据保持性测试
```python
# --no-attack-time 5e9: 等待5秒而不攻击，测试数据自然衰减
if self.no_attack_time is not None:
    self.no_attack_sleep()  # 等待指定时间
```

#### 首次bit翻转测试
```python
# 逐渐增加攻击强度，直到出现第一个bit翻转
for read_count in range(start, stop, step):
    if self.run_attack(read_count):
        print(f"First bitflip at {read_count} reads")
        break
```

---

## 第六部分：结果分析和可视化

### 6.1 错误数据结构

```python
error_summary = {
    "row_number": {
        'bank': bank_id,
        'row': physical_row,
        'col': {
            col_number: {
                'bitflip_positions': [bit0, bit1, ...],
                'total_bitflips': count
            }
        },
        'bitflips': total_count
    }
}
```

### 6.2 地址转换和分析

```python
# convert_address.py: 将逻辑地址转换为物理芯片地址
python convert_address.py input.json -o output.json
```

### 6.3 可视化工具

```python
# logs2plot.py: 生成攻击者vs受害者热力图
python logs2plot.py result.json --aggressors-vs-victims --annotate bitflips

# logs2vis.py: 生成详细的bit翻转分布图
python logs2vis.py result.json --output-dir ./plots/
```

---

## 第七部分：关键技术点总结

### 7.1 攻击原理
1. **物理机制**: 反复激活相邻行导致电荷泄漏
2. **时序要求**: 禁用刷新期间进行高频访问
3. **地址映射**: 确保攻击地址映射到同一Bank的不同行

### 7.2 检测机制
1. **预写入**: 使用已知模式填充内存
2. **攻击执行**: 按指定强度攻击目标行
3. **后验证**: 读取所有行并比较期望值
4. **错误统计**: 记录bit翻转的精确位置

### 7.3 硬件优化
1. **DMA加速**: 减少CPU开销，提高攻击频率  
2. **BIST集成**: 硬件级错误检测，提高精度
3. **Payload执行**: 微秒级时序控制，支持复杂攻击序列

### 7.4 实验控制
1. **刷新控制**: 精确控制内存刷新时机
2. **模式多样**: 支持多种数据模式测试
3. **参数化**: 攻击强度、行距、读取次数可调
4. **统计分析**: 详细的错误统计和可视化

---

## 总结

本项目实现了一个完整的Rowhammer攻击测试平台，从FPGA硬件加速到Python控制脚本，从地址映射到错误检测，提供了研究DDR3内存脆弱性的完整工具链。通过精确的时序控制、灵活的攻击模式和详细的结果分析，该平台能够系统性地评估不同内存芯片的Rowhammer敏感性。

关键创新包括：
- 硬件加速的攻击执行
- 精确的bit级错误定位  
- 灵活的攻击模式配置
- 完整的地址映射转换
- 详细的可视化分析工具

这些技术使得研究人员能够深入理解Rowhammer攻击的物理机制，评估内存系统的安全性，并开发相应的防御措施。
