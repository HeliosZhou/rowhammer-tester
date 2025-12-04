#!/usr/bin/env python3
"""
生成大规模HCfirst样本数据
用于测试可视化脚本和验证数据处理能力
"""

import json
import random
import numpy as np
from datetime import datetime

def generate_mock_errors(hammer_row):
    """生成模拟的bit翻转错误数据"""
    errors_in_rows = {}
    
    # 通常受影响的是相邻行
    victim_rows = []
    if random.random() < 0.7:  # 70%概率有上邻居受影响
        victim_rows.append(hammer_row - 1)
    if random.random() < 0.7:  # 70%概率有下邻居受影响
        victim_rows.append(hammer_row + 1)
    
    for victim_row in victim_rows:
        if victim_row >= 0 and victim_row < 8192:  # 确保行号有效
            # 生成随机的列和bit位置
            num_cols = random.randint(1, 3)  # 1-3个列受影响
            col_data = {}
            
            for _ in range(num_cols):
                col = random.randint(0, 1023)  # DRAM通常有1024列
                bits = [random.randint(0, 511)]  # 生成bit位置
                col_data[str(col)] = bits
            
            errors_in_rows[str(victim_row)] = {
                "bank": 0,
                "row": victim_row,
                "col": col_data,
                "bitflips": sum(len(bits) for bits in col_data.values())
            }
    
    return errors_in_rows

def generate_hcfirst_data(start_row=0, end_row=8191, mean=20000, std=5000, min_hc=5000, max_hc=50000):
    """生成HCfirst样本数据，格式与实测数据一致
    
    Args:
        start_row: 起始行号
        end_row: 结束行号  
        mean: HCfirst均值
        std: HCfirst标准差
        min_hc: 最小HCfirst值
        max_hc: 最大HCfirst值
    """
    results = {}
    row_count = 0
    
    print(f"生成样本数据: 行 {start_row}-{end_row}")
    print(f"HCfirst分布: 均值={mean:,}, 标准差={std:,}")
    
    for row in range(start_row, end_row + 1):
        # 模拟一些行没有找到HCfirst的情况（约10%的概率）
        if random.random() < 0.9:  # 90%成功率，只包含成功的测试
            # 使用正态分布生成HCfirst值
            hcfirst = int(np.random.normal(mean, std))
            
            # 限制在合理范围内
            hcfirst = max(min_hc, min(max_hc, hcfirst))
            
            # 生成符合实测格式的数据结构
            row_data = {
                "row": row,
                "status": "success",
                "hcfirst": hcfirst,
                "hammer_row_1": row,
                "hammer_row_2": row,
                "errors_in_rows": generate_mock_errors(row)
            }
            results[str(row)] = row_data
            row_count += 1
        
        if (row - start_row + 1) % 1000 == 0:
            print(f"  已生成 {row - start_row + 1} 行数据")
    
    print(f"完成! 总共 {row_count} 行有效数据")
    
    return results, row_count

def create_metadata(start_row, end_row, success_count, total_count):
    """创建元数据"""
    return {
        "type": "HCfirst_sample_large",
        "timestamp": datetime.now().isoformat(),
        "range": f"{start_row}-{end_row}",
        "success_count": success_count,
        "total_count": total_count,
        "duration_seconds": "simulated",
        "parameters": {
            "min_hc": 5000,
            "max_hc": 50000,
            "distribution": "normal",
            "mean": 20000,
            "std": 5000
        },
        "note": "这是模拟的测试数据，格式与实测数据一致，用于验证可视化和分析功能"
    }

def save_sample_data(filename, results, metadata=None):
    """保存样本数据，格式与实测数据一致"""
    # 实测数据格式直接是结果字典，不包含metadata
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"数据已保存: {filename}")
    
    # 显示统计信息
    success_values = []
    success_count = 0
    total_count = len(results)
    
    for row_data in results.values():
        if row_data.get('status') == 'success' and row_data.get('hcfirst') is not None:
            success_values.append(row_data['hcfirst'])
            success_count += 1
    
    print(f"统计信息:")
    print(f"  总行数: {total_count}")
    print(f"  成功测试: {success_count} ({success_count/total_count*100:.1f}%)")
    if success_values:
        print(f"  HCfirst范围: {min(success_values):,} - {max(success_values):,}")
        print(f"  平均值: {np.mean(success_values):,.0f}")
        print(f"  标准差: {np.std(success_values):,.0f}")

def generate_segmented_data():
    """生成分段数据用于测试多文件合并"""
    print("\n=== 生成分段数据 ===")
    
    segments = [
        (0, 2047, "segment_0-2047"),      # 第一段
        (2048, 4095, "segment_2048-4095"), # 第二段  
        (4096, 6143, "segment_4096-6143"), # 第三段
    ]
    
    for start, end, name in segments:
        print(f"\n生成 {name}...")
        results, success_count = generate_hcfirst_data(
            start_row=start, 
            end_row=end,
            mean=15000 + start // 10,  # 不同段有不同的均值
            std=3000
        )
        
        total_count = end - start + 1
        metadata = create_metadata(start, end, success_count, total_count)
        
        filename = f"large_sample_hcfirst_{name}.json"
        save_sample_data(filename, results)

def main():
    print("HCfirst大规模样本数据生成器")
    print("="*50)
    
    # 生成完整的大规模数据集
    print("1. 生成完整数据集 (0-8191)")
    results, success_count = generate_hcfirst_data(
        start_row=0, 
        end_row=8191, 
        mean=22000, 
        std=4000
    )
    
    total_count = 8192
    metadata = create_metadata(0, 8191, success_count, total_count)
    
    filename = "large_sample_hcfirst_0-8191.json"
    save_sample_data(filename, results)
    
    # 生成分段数据
    generate_segmented_data()
    
    print("\n" + "="*50)
    print("所有样本数据生成完成!")
    print("可以使用以下命令测试可视化:")
    print("  python plot_hcfirst.py large_sample_hcfirst_0-8191.json")
    print("  python plot_hcfirst.py large_sample_hcfirst_segment_*.json")

if __name__ == "__main__":
    main()
