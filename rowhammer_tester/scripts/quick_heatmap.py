#!/usr/bin/env python3
"""
简化的位翻转热力图绘制脚本

快速验证和测试用途
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import argparse
from collections import defaultdict

def calculate_real_column(col_key, bitflip_position):
    """计算真实列地址: 实际列 = col/2 + bitflip_positions%8"""
    col = int(col_key)
    real_col = col // 2 + bitflip_position % 8
    return real_col

def extract_bitflip_positions(raw_data, dram_rows=8192, dram_cols=1024):
    """提取位翻转位置信息"""
    all_positions = {}
    
    for time_key, time_data in raw_data.items():
        attack_time = time_data['attack_time']
        repeat_details = time_data['repeat_details']
        
        position_counts = defaultdict(int)
        
        for repeat_data in repeat_details:
            for row_key, row_info in repeat_data.items():
                row_num = int(row_key)
                
                if 'col' in row_info:
                    for col_key, col_info in row_info['col'].items():
                        if 'bitflip_positions' in col_info:
                            for bitflip_pos in col_info['bitflip_positions']:
                                real_col = calculate_real_column(col_key, bitflip_pos)
                                
                                if 0 <= row_num < dram_rows and 0 <= real_col < dram_cols:
                                    position_counts[(row_num, real_col)] += 1
        
        all_positions[time_key] = {
            'attack_time': attack_time,
            'positions': dict(position_counts)
        }
        
        print(f"时间点 {attack_time:.2f}s: {len(position_counts)} 个位翻转位置")
    
    return all_positions

def plot_quick_heatmap(json_file, time_point=None):
    """快速绘制热力图"""
    print(f"加载文件: {json_file}")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # 提取数据
    raw_data = data.get('raw_data', {})
    metadata = data.get('metadata', {})
    
    # 提取位翻转位置
    all_positions = extract_bitflip_positions(raw_data)
    
    # 选择要绘制的时间点
    if time_point is None:
        # 找到位翻转最多的时间点
        max_flips = 0
        best_time_key = None
        for time_key, time_data in all_positions.items():
            total_flips = sum(time_data['positions'].values())
            if total_flips > max_flips:
                max_flips = total_flips
                best_time_key = time_key
    else:
        # 查找最接近指定时间点的数据
        best_time_key = None
        min_diff = float('inf')
        for time_key, time_data in all_positions.items():
            diff = abs(time_data['attack_time'] - time_point)
            if diff < min_diff:
                min_diff = diff
                best_time_key = time_key
    
    if best_time_key is None:
        print("没有找到有效的数据")
        return
    
    # 创建热力图矩阵
    time_data = all_positions[best_time_key]
    attack_time = time_data['attack_time']
    positions = time_data['positions']
    
    matrix = np.zeros((8192, 1024))
    for (row, col), count in positions.items():
        matrix[row, col] = count / metadata.get('num_repeats', 1)
    
    # 绘制热力图
    plt.figure(figsize=(12, 10))
    
    # 过滤零值
    matrix_filtered = np.where(matrix > 0, matrix, np.nan)
    
    if np.nanmax(matrix_filtered) > 0:
        plt.imshow(matrix_filtered, cmap='viridis', aspect='auto', 
                  interpolation='nearest',
                  norm=LogNorm(vmin=max(0.01, np.nanmin(matrix_filtered)), 
                              vmax=np.nanmax(matrix_filtered)))
    else:
        plt.imshow(matrix, cmap='viridis', aspect='auto', interpolation='nearest')
    
    plt.title(f'位翻转热力图 - 攻击时间: {attack_time:.2f}s', fontsize=14)
    plt.xlabel('列 (Column)')
    plt.ylabel('行 (Row)')
    plt.colorbar(label='平均位翻转次数')
    
    # 添加统计信息
    total_bitflips = np.sum(matrix)
    affected_positions = np.sum(matrix > 0)
    
    stats_text = f'总位翻转: {int(total_bitflips * metadata.get("num_repeats", 1))}\n受影响位置: {int(affected_positions)}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
             verticalalignment='top', 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.show()
    
    # 输出一些统计信息
    print(f"\n统计信息:")
    print(f"攻击时间: {attack_time:.2f}s")
    print(f"总位翻转数: {int(total_bitflips * metadata.get('num_repeats', 1))}")
    print(f"受影响位置: {int(affected_positions)}")
    print(f"重复次数: {metadata.get('num_repeats', 1)}")

def main():
    parser = argparse.ArgumentParser(description='快速绘制位翻转热力图')
    parser.add_argument('json_file', help='输入的JSON测试结果文件')
    parser.add_argument('--time', '-t', type=float, help='指定时间点 (秒)')
    
    args = parser.parse_args()
    
    plot_quick_heatmap(args.json_file, args.time)

if __name__ == '__main__':
    main()
