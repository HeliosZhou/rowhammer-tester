# HCfirst测试脚本使用说明

## 概述
这个脚本用于测试0-8192行的HCfirst（第一个bit翻转需要的最小锤击数）。

## 脚本文件
- `test_hcfirst_simple.py`: 简化版本，推荐使用
- `test_hcfirst_all_rows.py`: 完整版本，功能更丰富

## 主要特性
1. **自适应起始值**: 使用前几次成功测试的平均值作为后续测试的起始值
2. **二分查找**: 高效找到最小的read_count值
3. **重复验证**: 对找到的HCfirst值进行多次验证确保准确性
4. **进度保存**: 每10行自动保存结果，支持中断恢复
5. **统计信息**: 自动计算成功率和HCfirst值的统计信息

## 可自定义参数

在脚本开头可以修改以下参数：

```python
# ===== 可自定义配置参数 =====
INITIAL_READ_COUNT = 20000        # 起始read_count值 (可自定义)
VERIFICATION_TIMES = 2            # 重复验证次数 (可自定义)
```

## 使用方法

### 1. 进入正确目录并激活虚拟环境
```bash
cd /home/hc/rowhammer-tester
source .venv/bin/activate
```

### 2. 启动litex服务器
```bash
# 在一个终端启动服务器
make srv
```

### 3. 在另一个终端运行测试脚本
```bash
# 激活虚拟环境
source .venv/bin/activate

# 使用简化版本（推荐）
python /home/hc/rowhammer-tester/rowhammer_tester/scripts/result/HCfirst/test_hcfirst_simple.py

# 或者直接执行
/home/hc/rowhammer-tester/rowhammer_tester/scripts/result/HCfirst/test_hcfirst_simple.py
```

## 输出说明

### 测试过程输出示例:
```
HCfirst测试开始
测试范围: 行 0-8191 (8192行)
初始read_count: 20,000
验证次数: 2
结果文件: /home/hc/rowhammer-tester/rowhammer_tester/scripts/result/HCfirst/HCfirst_all_rows_0-8191_20231130_143052.json
============================================================

[   1/8192] 测试行     0
  测试起始值: 20,000
    ✓ 有bit翻转，向下搜索
  [ 1] 测试 10,000
      ✓ 有翻转，HCfirst <= 10,000
  [ 2] 测试 5,000
      ✗ 无翻转，HCfirst > 5,000
  [ 3] 测试 7,500
      ✓ 有翻转，HCfirst <= 7,500
  验证 HCfirst=7,500
    [1/2] ✓
    [2/2] ✓
  验证结果: 2/2 通过
  结果: HCfirst = 7,500 (已验证)
  用时: 45.2s, 成功率: 1/1
```

### 结果文件格式:
```json
{
  "test_config": {
    "initial_read_count": 20000,
    "verification_times": 2,
    "total_rows": 8192,
    "test_time": "2023-11-30T14:30:52.123456"
  },
  "statistics": {
    "tested_rows": 100,
    "successful_rows": 95,
    "success_rate": "95.0%"
  },
  "results": {
    "0": {
      "row": 0,
      "hcfirst": 7500,
      "verified": true,
      "time": 45.2
    },
    ...
  }
}
```

## 注意事项

1. **测试时间**: 完整测试8192行可能需要数小时到数十小时
2. **中断恢复**: 脚本会每10行保存一次结果，可以安全中断
3. **内存要求**: 确保系统有足够内存运行测试
4. **服务器状态**: 确保litex服务器正常运行
5. **文件权限**: 确保有写入结果目录的权限

## 故障排除

### 常见问题:
1. **"hw_rowhammer.py 不存在"**: 检查当前目录是否正确
2. **"测试超时"**: 可能是硬件问题或read_count值太大
3. **"验证失败"**: 硬件状态不稳定，可以增加验证次数

### 调试建议:
1. 先用小范围测试几行验证脚本工作正常
2. 检查硬件连接和litex服务器状态
3. 查看详细的错误输出

## 结果分析

测试完成后，可以使用生成的JSON文件进行进一步分析:
- 查看每行的HCfirst值分布
- 分析验证成功率
- 找出特别脆弱或坚固的内存行
