#!/usr/bin/env python3
"""
绘制位翻转热力图的脚本

这个脚本用于分析retention测试结果并生成热力图，显示DRAM中不同位置的位翻转情况。
支持8192行 x 1024列的DRAM布局。

列地址映射规则：
实际列 = col/2 + bitflip_positions%8
bitflip_positions = bitflip_positions%8的余数

用法:
    python plot_bitflip_heatmap.py <json_file> [options]
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LogNorm
import seaborn as sns
import argparse
import os
from pathlib import Path
from collections import defaultdict
import warnings

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 忽略一些不重要的警告
warnings.filterwarnings('ignore', category=UserWarning)

class BitflipHeatmapPlotter:
    def __init__(self, dram_rows=8192, dram_cols=1024):
        """
        初始化热力图绘制器
        
        Args:
            dram_rows: DRAM行数 (默认8192)
            dram_cols: DRAM列数 (默认1024)
        """
        self.dram_rows = dram_rows
        self.dram_cols = dram_cols
        
    def calculate_real_column(self, col_key, bitflip_position):
        """
        根据列键值和位翻转位置计算真实的列地址
        
        Args:
            col_key: JSON中的列键值 (如"360")
            bitflip_position: 位翻转位置
            
        Returns:
            真实的列地址
        """
        col = int(col_key)
        real_col = col // 2 + bitflip_position % 8
        return real_col
        
    def load_and_parse_data(self, json_file):
        """
        加载并解析JSON测试结果文件
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            parsed_data: 解析后的数据字典
        """
        print(f"正在加载文件: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        metadata = data.get('metadata', {})
        raw_data = data.get('raw_data', {})
        statistics = data.get('statistics', {})
        
        print(f"测试时间点: {len(metadata.get('time_points', []))}")
        print(f"重复次数: {metadata.get('num_repeats', 0)}")
        print(f"测试类型: {metadata.get('test_type', 'unknown')}")
        
        return {
            'metadata': metadata,
            'raw_data': raw_data,
            'statistics': statistics
        }
    
    def extract_bitflip_positions(self, raw_data):
        """
        从原始数据中提取所有位翻转位置信息
        
        Args:
            raw_data: 原始测试数据
            
        Returns:
            all_positions: 包含所有时间点位翻转位置的字典
        """
        all_positions = {}
        
        for time_key, time_data in raw_data.items():
            attack_time = time_data['attack_time']
            repeat_details = time_data['repeat_details']
            
            # 初始化该时间点的位置统计
            position_counts = defaultdict(int)
            
            # 遍历每次重复实验
            for repeat_idx, repeat_data in enumerate(repeat_details):
                for row_key, row_info in repeat_data.items():
                    row_num = int(row_key)
                    
                    if 'col' in row_info:
                        for col_key, col_info in row_info['col'].items():
                            if 'bitflip_positions' in col_info:
                                for bitflip_pos in col_info['bitflip_positions']:
                                    # 计算真实的列地址
                                    real_col = self.calculate_real_column(col_key, bitflip_pos)
                                    
                                    # 确保行列在有效范围内
                                    if 0 <= row_num < self.dram_rows and 0 <= real_col < self.dram_cols:
                                        position_counts[(row_num, real_col)] += 1
            
            all_positions[time_key] = {
                'attack_time': attack_time,
                'positions': dict(position_counts)
            }
            
            print(f"时间点 {attack_time:.2f}s: 发现 {len(position_counts)} 个位翻转位置")
            
        return all_positions
    
    def create_heatmap_matrix(self, positions, use_average=False, num_repeats=1):
        """
        创建热力图矩阵
        
        Args:
            positions: 位翻转位置数据
            use_average: 是否使用平均值
            num_repeats: 重复次数
            
        Returns:
            热力图矩阵 (rows x cols)
        """
        matrix = np.zeros((self.dram_rows, self.dram_cols))
        
        for (row, col), count in positions.items():
            if use_average and num_repeats > 0:
                matrix[row, col] = count / num_repeats
            else:
                matrix[row, col] = count
                
        return matrix
    
    def plot_single_heatmap(self, matrix, title, output_path=None, vmin=None, vmax=None):
        """
        绘制单个热力图
        
        Args:
            matrix: 热力图矩阵
            title: 图表标题
            output_path: 输出文件路径
            vmin, vmax: 颜色范围
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 过滤掉零值，避免对数刻度问题
        matrix_filtered = np.where(matrix > 0, matrix, np.nan)
        
        # 如果所有值都为0，使用线性刻度
        if np.nanmax(matrix_filtered) == 0:
            im = ax.imshow(matrix, cmap='viridis', aspect='auto', 
                          interpolation='nearest')
        else:
            # 使用对数刻度
            im = ax.imshow(matrix_filtered, cmap='viridis', aspect='auto', 
                          interpolation='nearest', 
                          norm=LogNorm(vmin=max(1, np.nanmin(matrix_filtered)), 
                                     vmax=np.nanmax(matrix_filtered)))
        
        # 设置标题和标签
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('列 (Column)', fontsize=12)
        ax.set_ylabel('行 (Row)', fontsize=12)
        
        # 设置坐标轴刻度
        ax.set_xticks(np.arange(0, self.dram_cols, self.dram_cols//8))
        ax.set_yticks(np.arange(0, self.dram_rows, self.dram_rows//8))
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('位翻转次数', rotation=270, labelpad=15)
        
        # 添加统计信息
        total_bitflips = np.sum(matrix)
        affected_positions = np.sum(matrix > 0)
        
        stats_text = f'总位翻转: {int(total_bitflips)}\n受影响位置: {int(affected_positions)}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"保存热力图到: {output_path}")
        
        plt.show()
    
    def plot_time_progression_heatmaps(self, all_positions, metadata, output_dir=None):
        """
        绘制时间进展热力图
        
        Args:
            all_positions: 所有时间点的位翻转数据
            metadata: 测试元数据
            output_dir: 输出目录
        """
        num_repeats = metadata.get('num_repeats', 1)
        
        # 创建输出目录
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 为每个时间点创建热力图
        for time_key in sorted(all_positions.keys(), key=lambda x: all_positions[x]['attack_time']):
            time_data = all_positions[time_key]
            attack_time = time_data['attack_time']
            positions = time_data['positions']
            
            # 创建矩阵（使用平均值）
            matrix = self.create_heatmap_matrix(positions, use_average=True, num_repeats=num_repeats)
            
            # 设置标题
            title = f'位翻转热力图 - 攻击时间: {attack_time:.2f}s'
            
            # 设置输出路径
            output_path = None
            if output_dir:
                filename = f'heatmap_time_{attack_time:.2f}s.png'
                output_path = os.path.join(output_dir, filename)
            
            # 绘制热力图
            self.plot_single_heatmap(matrix, title, output_path)
    
    def plot_combined_heatmap(self, all_positions, metadata, output_path=None):
        """
        绘制所有时间点的组合热力图
        
        Args:
            all_positions: 所有时间点的位翻转数据
            metadata: 测试元数据
            output_path: 输出文件路径
        """
        # 合并所有时间点的数据
        combined_positions = defaultdict(int)
        
        for time_data in all_positions.values():
            for position, count in time_data['positions'].items():
                combined_positions[position] += count
        
        # 创建矩阵
        matrix = self.create_heatmap_matrix(dict(combined_positions))
        
        # 设置标题
        total_time = metadata.get('end_time', 0) - metadata.get('start_time', 0)
        title = f'累积位翻转热力图 - 总测试时间: {total_time:.1f}s'
        
        # 绘制热力图
        self.plot_single_heatmap(matrix, title, output_path)
    
    def generate_summary_report(self, all_positions, metadata):
        """
        生成分析摘要报告
        
        Args:
            all_positions: 所有时间点的位翻转数据
            metadata: 测试元数据
        """
        print("\n" + "="*60)
        print("测试结果摘要报告")
        print("="*60)
        
        # 基本信息
        print(f"测试类型: {metadata.get('test_type', 'unknown')}")
        print(f"测试时间: {metadata.get('test_timestamp', 'unknown')}")
        print(f"时间范围: {metadata.get('start_time', 0):.1f}s - {metadata.get('end_time', 0):.1f}s")
        print(f"重复次数: {metadata.get('num_repeats', 0)}")
        print(f"DRAM尺寸: {self.dram_rows} x {self.dram_cols}")
        
        # 每个时间点的统计
        print(f"\n时间点统计:")
        print(f"{'时间(s)':<10} {'位翻转总数':<12} {'受影响位置':<12} {'平均值':<10}")
        print("-" * 50)
        
        for time_key in sorted(all_positions.keys(), key=lambda x: all_positions[x]['attack_time']):
            time_data = all_positions[time_key]
            attack_time = time_data['attack_time']
            positions = time_data['positions']
            
            total_flips = sum(positions.values())
            affected_positions = len(positions)
            avg_flips = total_flips / metadata.get('num_repeats', 1) if metadata.get('num_repeats', 1) > 0 else 0
            
            print(f"{attack_time:<10.2f} {total_flips:<12} {affected_positions:<12} {avg_flips:<10.1f}")
        
        # 总体统计
        all_combined = defaultdict(int)
        for time_data in all_positions.values():
            for position, count in time_data['positions'].items():
                all_combined[position] += count
        
        total_unique_positions = len(all_combined)
        total_all_flips = sum(all_combined.values())
        
        print(f"\n总体统计:")
        print(f"总位翻转数: {total_all_flips}")
        print(f"受影响的唯一位置: {total_unique_positions}")
        print(f"DRAM覆盖率: {total_unique_positions/(self.dram_rows * self.dram_cols)*100:.4f}%")

def main():
    parser = argparse.ArgumentParser(description='绘制位翻转热力图')
    parser.add_argument('json_file', help='输入的JSON测试结果文件')
    parser.add_argument('--output-dir', '-o', help='输出目录（可选）')
    parser.add_argument('--rows', type=int, default=8192, help='DRAM行数 (默认8192)')
    parser.add_argument('--cols', type=int, default=1024, help='DRAM列数 (默认1024)')
    parser.add_argument('--combined-only', action='store_true', help='只生成组合热力图')
    parser.add_argument('--time-series', action='store_true', help='生成时间序列热力图')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.json_file):
        print(f"错误: 找不到文件 {args.json_file}")
        return
    
    # 创建绘图器
    plotter = BitflipHeatmapPlotter(dram_rows=args.rows, dram_cols=args.cols)
    
    # 加载和解析数据
    parsed_data = plotter.load_and_parse_data(args.json_file)
    
    # 提取位翻转位置
    all_positions = plotter.extract_bitflip_positions(parsed_data['raw_data'])
    
    # 生成摘要报告
    plotter.generate_summary_report(all_positions, parsed_data['metadata'])
    
    # 设置输出路径
    output_dir = args.output_dir
    if not output_dir:
        # 基于输入文件名创建输出目录
        base_name = Path(args.json_file).stem
        output_dir = f"{base_name}_heatmaps"
    
    # 绘制图表
    if args.combined_only:
        # 只绘制组合热力图
        combined_output = os.path.join(output_dir, 'combined_heatmap.png') if output_dir else None
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        plotter.plot_combined_heatmap(all_positions, parsed_data['metadata'], combined_output)
    
    elif args.time_series:
        # 绘制时间序列热力图
        plotter.plot_time_progression_heatmaps(all_positions, parsed_data['metadata'], output_dir)
    
    else:
        # 绘制所有图表
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 组合热力图
        combined_output = os.path.join(output_dir, 'combined_heatmap.png') if output_dir else None
        plotter.plot_combined_heatmap(all_positions, parsed_data['metadata'], combined_output)
        
        # 时间序列热力图
        plotter.plot_time_progression_heatmaps(all_positions, parsed_data['metadata'], output_dir)

if __name__ == '__main__':
    main()
