#!/usr/bin/env python3
"""
简化的位翻转热力图绘制脚本
python3 quick_heatmap.py bitflip_time_test_20251126_182933.json
快速验证和测试用途
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import argparse
from collections import defaultdict

def calculate_real_column(col_key, bitflip_position):
    """计算真实列地址: 实际列 = col_key + bitflip_position // 64"""
    col = int(col_key)
    real_col = col + bitflip_position // 64
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
        
        print(f"时间点 {attack_time:.2f}s: {len(position_counts)} bitflip positions")
        
        all_positions[time_key] = {
            'attack_time': attack_time,
            'positions': dict(position_counts)
        }
    return all_positions

def plot_quick_heatmap(json_file, time_point=None, save_plot=True):
    """快速绘制热力图"""
    print(f"Loading file: {json_file}")
    
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
        print("No valid data found")
        return
    
    # 创建散点图数据
    time_data = all_positions[best_time_key]
    attack_time = time_data['attack_time']
    positions = time_data['positions']
    
    print(f"Creating scatter plot for {len(positions)} positions")
    
    # 绘制散点图 - 显示整个DRAM的位翻转位置
    plt.figure(figsize=(15, 12))
    
    if len(positions) > 0:
        # 提取行、列、翻转次数
        rows = []
        cols = []
        counts = []
        
        for (row, col), count in positions.items():
            rows.append(row)
            cols.append(col)
            counts.append(count / metadata.get('num_repeats', 1))  # 标准化为平均值
        
        # 创建散点图，缩小点的大小
        sizes = [c * 20 + 5 for c in counts]  # 减小点的大小：从50+10改为20+5
        scatter = plt.scatter(cols, rows, c=counts, s=sizes, cmap='Reds', 
                             alpha=0.8, edgecolors='black', linewidth=0.2,
                             vmin=0, vmax=max(counts) if counts else 1)
        
        # 添加颜色条
        cbar = plt.colorbar(scatter, shrink=0.8)
        cbar.set_label('Avg Bitflips per Repeat', rotation=270, labelpad=15)
        
        print(f"Plotted {len(positions)} bitflip positions")
        
        # 显示数据范围信息
        if len(rows) > 0:
            min_row, max_row = min(rows), max(rows)
            min_col, max_col = min(cols), max(cols)
            print(f"Data range: rows {min_row}-{max_row}, cols {min_col}-{max_col}")
    else:
        print("No bitflip positions to plot")
        # 如果没有数据，显示空的图表背景
        plt.scatter([], [], c=[], s=[], cmap='Reds')
    
    plt.title(f'Bitflip Scatter Plot - Attack Time: {attack_time:.2f}s (Full DRAM View)', fontsize=14)
    plt.xlabel('Column')
    plt.ylabel('Row')
    
    # 设置坐标轴范围和刻度
    plt.xlim(0, 1024)
    plt.ylim(0, 8192)
    
    # 设置合理的坐标轴刻度
    plt.xticks(np.linspace(0, 1024, 9))
    plt.yticks(np.linspace(0, 8192, 9))
    
    # 添加网格帮助定位
    plt.grid(True, alpha=0.3)
    
    # 添加统计信息
    if len(positions) > 0:
        total_bitflips = sum(positions.values())
        affected_positions = len(positions)
        
        stats_text = f'Total Bitflips: {int(total_bitflips)}\nAffected Positions: {int(affected_positions)}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                 verticalalignment='top', 
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    else:
        stats_text = f'Total Bitflips: 0\nAffected Positions: 0'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                 verticalalignment='top', 
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # 保存图片
    if save_plot:
        import os
        from pathlib import Path
        
        # 获取输入文件的基本名称
        input_path = Path(json_file)
        base_name = input_path.stem
        
        # 设置输出目录为result/result/retention/
        output_dir = Path("/home/hc/rowhammer-tester/rowhammer_tester/scripts/result/result/retention/")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建输出文件名 - 去掉时间戳，只保留关键信息
        output_filename = f"bitflip_heatmap_{attack_time:.2f}s.png"
        output_path = output_dir / output_filename
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Heatmap saved to: {output_path}")
    
    plt.show()
    
    # 输出一些统计信息
    print(f"\nStatistics:")
    print(f"Attack time: {attack_time:.2f}s")
    print(f"Total bitflips: {int(sum(positions.values())) if len(positions) > 0 else 0}")
    print(f"Affected positions: {len(positions)}")
    print(f"Number of repeats: {metadata.get('num_repeats', 1)}")

def generate_all_heatmaps(json_file, save_plot=True):
    """为所有时间点生成热力图"""
    print(f"Loading file: {json_file}")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # 获取所有时间点
    metadata = data.get('metadata', {})
    time_points = metadata.get('time_points', [])
    
    print(f"Found {len(time_points)} time points, generating heatmaps for all...")
    
    for i, time_point in enumerate(time_points):
        print(f"\nGenerating heatmap {i+1}/{len(time_points)} for time point: {time_point:.2f}s")
        try:
            plot_quick_heatmap(json_file, time_point, save_plot=save_plot)
        except Exception as e:
            print(f"Error generating heatmap for {time_point:.2f}s: {e}")
    
    print(f"\nCompleted! Generated {len(time_points)} heatmaps.")

def main():
    parser = argparse.ArgumentParser(description='Quick bitflip heatmap visualization')
    parser.add_argument('json_file', help='输入的JSON测试结果文件')
    parser.add_argument('--time', '-t', type=float, help='Specify time point (seconds)')
    parser.add_argument('--save', '-s', action='store_true', help='Save plot to file')
    parser.add_argument('--all', '-a', action='store_true', help='Generate heatmaps for all time points')
    
    args = parser.parse_args()
    
    if args.all:
        # 生成所有时间点的热力图
        generate_all_heatmaps(args.json_file, save_plot=args.save)
    else:
        plot_quick_heatmap(args.json_file, args.time, save_plot=args.save)

if __name__ == '__main__':
    main()
