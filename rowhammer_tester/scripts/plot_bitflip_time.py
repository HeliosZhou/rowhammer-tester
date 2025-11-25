#!/usr/bin/env python3
"""
绘制bit翻转数量随开启时间变化的曲线图
"""

import os
import sys
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def load_test_data(filepath):
    """
    加载测试数据
    
    Args:
        filepath: JSON测试数据文件路径
        
    Returns:
        dict: 测试数据
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"加载数据文件失败: {e}")
        return None

def create_bitflip_time_plot(data, output_dir=None, show_plot=True):
    """
    创建bit翻转随时间变化的图表
    
    Args:
        data: 测试数据字典
        output_dir: 输出目录路径，如果为None则不保存
        show_plot: 是否显示图表
    """
    
    # 提取数据
    time_points = []
    mean_values = []
    std_values = []
    min_values = []
    max_values = []
    raw_data_all = []
    
    # 按时间排序
    sorted_stats = sorted(data['statistics'].items(), key=lambda x: float(x[1]['attack_time']))
    
    for time_key, stats in sorted_stats:
        time_points.append(stats['attack_time'])
        mean_values.append(stats['mean'])
        std_values.append(stats['std'])
        min_values.append(stats['min'])
        max_values.append(stats['max'])
        
        # 获取原始重复数据
        raw_data = data['raw_data'][time_key]['repeat_results']
        raw_data_all.append(raw_data)
    
    time_points = np.array(time_points)
    mean_values = np.array(mean_values)
    std_values = np.array(std_values)
    min_values = np.array(min_values)
    max_values = np.array(max_values)
    
    # 创建图表
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # 主图：平均值和误差条
    ax1.errorbar(time_points, mean_values, yerr=std_values, 
                capsize=5, capthick=2, marker='o', markersize=8, 
                linewidth=2, label='Mean ± Std')
    
    # 填充最小值到最大值的区域
    ax1.fill_between(time_points, min_values, max_values, 
                    alpha=0.2, label='Min-Max Range')
    
    # 绘制个别测试点
    for i, (t, raw_data) in enumerate(zip(time_points, raw_data_all)):
        x_scatter = np.full(len(raw_data), t)
        # 添加小的随机偏移以避免重叠
        x_scatter += np.random.normal(0, 0.05, len(raw_data))
        ax1.scatter(x_scatter, raw_data, alpha=0.6, s=30, color='red', zorder=3)
    
    ax1.set_xlabel('Attack Time (seconds)', fontsize=12)
    ax1.set_ylabel('Number of Bit Flips', fontsize=12)
    ax1.set_title('Bit Flips vs Attack Time', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xscale('log')  # 使用对数刻度更好地显示时间范围
    
    # 子图：显示每个时间点的分布（箱线图）
    positions = np.arange(len(time_points))
    box_data = [raw_data for raw_data in raw_data_all]
    
    bp = ax2.boxplot(box_data, positions=positions, patch_artist=True)
    
    # 美化箱线图
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    ax2.set_xlabel('Time Point Index', fontsize=12)
    ax2.set_ylabel('Number of Bit Flips', fontsize=12)
    ax2.set_title('Distribution of Bit Flips at Each Time Point', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # 设置x轴标签为实际时间值
    ax2.set_xticks(positions)
    ax2.set_xticklabels([f'{t:.2f}s' for t in time_points], rotation=45)
    
    plt.tight_layout()
    
    # 保存图表
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_filename = f"bitflip_time_plot_{timestamp}.png"
        plot_path = output_dir / plot_filename
        
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {plot_path}")
        
        # 同时保存高分辨率PDF版本
        pdf_path = output_dir / plot_filename.replace('.png', '.pdf')
        plt.savefig(pdf_path, bbox_inches='tight')
        print(f"PDF版本已保存到: {pdf_path}")
    
    # 显示图表
    if show_plot:
        plt.show()
    
    return fig

def create_summary_table(data, output_dir=None):
    """
    创建数据摘要表格
    
    Args:
        data: 测试数据字典
        output_dir: 输出目录路径
    """
    
    # 创建DataFrame
    summary_data = []
    
    # 按时间排序
    sorted_stats = sorted(data['statistics'].items(), key=lambda x: float(x[1]['attack_time']))
    
    for time_key, stats in sorted_stats:
        raw_data = data['raw_data'][time_key]['repeat_results']
        
        summary_data.append({
            'Attack Time (s)': stats['attack_time'],
            'Mean Bit Flips': stats['mean'],
            'Std Dev': stats['std'],
            'Min': stats['min'],
            'Max': stats['max'],
            'Coefficient of Variation': stats['std'] / stats['mean'] if stats['mean'] > 0 else 0,
            'Raw Data': ', '.join(map(str, raw_data))
        })
    
    df = pd.DataFrame(summary_data)
    
    # 打印摘要表格
    print("\n" + "=" * 80)
    print("测试结果摘要表")
    print("=" * 80)
    
    # 格式化打印
    for i, row in df.iterrows():
        print(f"Time: {row['Attack Time (s)']:6.2f}s | "
              f"Mean: {row['Mean Bit Flips']:7.1f} | "
              f"Std: {row['Std Dev']:6.1f} | "
              f"Range: [{row['Min']:4.0f}, {row['Max']:4.0f}] | "
              f"CV: {row['Coefficient of Variation']:5.3f}")
    
    # 保存到文件
    if output_dir:
        output_dir = Path(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        table_filename = f"bitflip_summary_{timestamp}.csv"
        table_path = output_dir / table_filename
        
        df.to_csv(table_path, index=False)
        print(f"\n摘要表格已保存到: {table_path}")
    
    return df

def find_latest_test_file(result_dir):
    """
    在result目录中找到最新的测试文件
    
    Args:
        result_dir: result/retention目录路径
        
    Returns:
        str: 最新测试文件的路径，如果没找到则返回None
    """
    
    result_path = Path(result_dir)
    if not result_path.exists():
        return None
    
    # 查找所有JSON测试文件
    json_files = list(result_path.glob("bitflip_time_test_*.json"))
    
    if not json_files:
        return None
    
    # 按修改时间排序，返回最新的
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    return str(latest_file)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='绘制bit翻转随时间变化的图表')
    parser.add_argument('--input', '-i', type=str, 
                       help='输入的JSON测试数据文件路径 (如果不指定，将自动查找最新的测试文件)')
    parser.add_argument('--output', '-o', type=str,
                       help='输出目录路径 (默认为result/retention)')
    parser.add_argument('--no-show', action='store_true',
                       help='不显示图表窗口，只保存到文件')
    
    args = parser.parse_args()
    
    # 确定输入文件
    if args.input:
        input_file = args.input
    else:
        # 自动查找最新的测试文件
        script_dir = Path(__file__).parent
        result_dir = script_dir.parent / 'result' / 'retention'
        
        input_file = find_latest_test_file(result_dir)
        if not input_file:
            print("错误: 未找到测试数据文件")
            print("请先运行 bitflip_time_test.py 生成测试数据，或使用 --input 参数指定文件")
            return
        
        print(f"自动找到最新测试文件: {input_file}")
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        return
    
    # 确定输出目录
    if args.output:
        output_dir = args.output
    else:
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent / 'result' / 'retention'
    
    print(f"加载测试数据: {input_file}")
    
    # 加载数据
    data = load_test_data(input_file)
    if data is None:
        return
    
    print(f"数据加载成功")
    print(f"测试配置:")
    print(f"  时间范围: {data['metadata']['start_time']}s - {data['metadata']['end_time']}s")
    print(f"  测试点数: {data['metadata']['num_points']}")
    print(f"  重复次数: {data['metadata']['num_repeats']}")
    print(f"  测试时间: {data['metadata']['test_timestamp']}")
    
    # 创建图表
    print(f"\n生成图表...")
    fig = create_bitflip_time_plot(data, output_dir, not args.no_show)
    
    # 创建摘要表格
    print(f"\n生成摘要表格...")
    df = create_summary_table(data, output_dir)
    
    print(f"\n可视化完成!")

if __name__ == "__main__":
    main()
