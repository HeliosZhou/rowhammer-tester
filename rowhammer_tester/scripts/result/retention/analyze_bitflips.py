#!/usr/bin/env python3
"""
比特翻转数据分析工具
解析bitflip_time_test生成的JSON文件，并提供详细的列映射信息
"""

import json
import sys
from pathlib import Path

def analyze_bitflip_data(json_file_path):
    """分析比特翻转数据并生成详细映射"""
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print("比特翻转数据详细分析")
    print("=" * 80)
    
    # 打印基本信息
    metadata = data['metadata']
    print(f"测试时间范围: {metadata['start_time']}s - {metadata['end_time']}s")
    print(f"测试点数: {metadata['num_points']}")
    print(f"重复次数: {metadata['num_repeats']}")
    print(f"测试行数: {metadata['nrows']}")
    print(f"测试时间: {metadata['test_timestamp']}")
    print()
    
    # DDR4内存配置
    print("=" * 80)
    print("DDR4内存配置")
    print("=" * 80)
    print("逻辑列数: 1024 (0-1023)")
    print("每列数据宽度: 512 bits (64 bytes)")
    print("总行数: 65536")
    print("Bank数: 16")
    print()
    
    # 分析每个时间点的数据
    for time_key, time_data in data['raw_data'].items():
        attack_time = time_data['attack_time']
        repeat_results = time_data['repeat_results']
        repeat_details = time_data['repeat_details']
        
        print("=" * 80)
        print(f"攻击时间: {attack_time}s")
        print("=" * 80)
        
        total_bitflips = sum(repeat_results)
        print(f"检测到的比特翻转总数: {total_bitflips}")
        print(f"重复测试结果: {repeat_results}")
        print()
        
        if total_bitflips == 0:
            print("未检测到比特翻转")
            continue
        
        # 分析每次重复的详细数据
        for repeat_idx, details in enumerate(repeat_details):
            if not details:
                continue
                
            print(f"重复测试 #{repeat_idx + 1} 详细分析:")
            print("-" * 60)
            
            print(f"{'Row':<8} {'Col':<8} {'BitPos':<8} {'ByteCol':<8} {'BitByte':<8} {'AbsByte':<10} {'AbsBit':<10}")
            print("-" * 60)
            
            # 按行号排序
            sorted_rows = sorted(details.items(), key=lambda x: int(x[0]))
            
            for row_str, row_info in sorted_rows:
                row_num = int(row_str)
                col_data = row_info['col']
                
                for col_str, col_info in col_data.items():
                    col_num = int(col_str)
                    bitflip_positions = col_info['bitflip_positions']
                    
                    for bit_pos in bitflip_positions:
                        # 计算详细映射
                        byte_in_col = bit_pos // 8
                        bit_in_byte = bit_pos % 8
                        abs_byte = col_num * 64 + byte_in_col
                        abs_bit = col_num * 512 + bit_pos
                        
                        print(f"{row_num:<8} {col_num:<8} {bit_pos:<8} {byte_in_col:<8} {bit_in_byte:<8} {abs_byte:<10} {abs_bit:<10}")
            
            print()
            print("说明:")
            print("- Row: DDR4行地址")
            print("- Col: DDR4列地址 (0-1023)")
            print("- BitPos: 在该列512位数据中的位位置 (0-511，从左开始)")
            print("- ByteCol: 在该列64字节中的字节位置 (0-63)")
            print("- BitByte: 在该字节内的位位置 (0-7)")
            print("- AbsByte: 在整行中的绝对字节地址")
            print("- AbsBit: 在整行中的绝对位地址")
            print()
    
    # 生成汇总统计
    print("=" * 80)
    print("汇总统计")
    print("=" * 80)
    
    all_affected_rows = set()
    all_affected_cols = set()
    time_vs_bitflips = []
    
    for time_key, time_data in data['raw_data'].items():
        attack_time = time_data['attack_time']
        total_flips = sum(time_data['repeat_results'])
        time_vs_bitflips.append((attack_time, total_flips))
        
        for details in time_data['repeat_details']:
            for row_str, row_info in details.items():
                all_affected_rows.add(int(row_str))
                for col_str in row_info['col'].keys():
                    all_affected_cols.add(int(col_str))
    
    print(f"受影响的行数: {len(all_affected_rows)}")
    if all_affected_rows:
        print(f"受影响的行范围: {min(all_affected_rows)} - {max(all_affected_rows)}")
        print(f"受影响的行: {sorted(all_affected_rows)}")
    
    print(f"受影响的列数: {len(all_affected_cols)}")
    if all_affected_cols:
        print(f"受影响的列范围: {min(all_affected_cols)} - {max(all_affected_cols)}")
        print(f"受影响的列: {sorted(all_affected_cols)}")
    
    print()
    print("时间vs比特翻转趋势:")
    for time, flips in sorted(time_vs_bitflips):
        print(f"  {time:6.2f}s: {flips:4d} bit翻转")

def main():
    if len(sys.argv) != 2:
        print("用法: python analyze_bitflips.py <json_file_path>")
        print("示例: python analyze_bitflips.py result/retention/bitflip_time_test_20251126_162355.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not Path(json_file).exists():
        print(f"错误: 文件 {json_file} 不存在")
        sys.exit(1)
    
    try:
        analyze_bitflip_data(json_file)
    except Exception as e:
        print(f"分析过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
