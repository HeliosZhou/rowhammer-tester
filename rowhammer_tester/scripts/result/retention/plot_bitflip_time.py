#!/usr/bin/env python3
"""
绘制内存错误分析结果的可视化图表

此脚本用于分析和可视化rowhammer攻击随时间变化的内存错误模式。
支持处理分析结果JSON文件，生成错误趋势图和统计摘要。

输入: *_analysis.json 分析结果文件
输出: 
- 内存错误趋势图 (PNG/PDF)
- 错误统计摘要表 (CSV)
python plot_bitflip_time.py --input result/retention/bitflip_time_test_20251126_182933_analysis.json --no-show
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
    
    # 检查数据格式，判断是原始数据还是分析结果
    if 'statistics' in data and 'raw_data' in data:
        # 原始数据格式
        use_raw_data = True
        print("检测到原始测试数据格式，使用统计信息和原始数据")
    elif 'error_patterns' in data:
        # 分析结果格式
        use_raw_data = False
        print("检测到分析结果格式，使用错误模式数据")
    else:
        print("错误：未识别的数据格式")
        return None
    
    # 提取数据
    time_points = []
    mean_values = []
    std_values = []
    min_values = []
    max_values = []
    raw_data_all = []
    
    if use_raw_data:
        # 使用原始数据的统计信息
        sorted_stats = sorted(data['statistics'].items(), key=lambda x: x[1]['attack_time'])
        
        for time_key, stats in sorted_stats:
            time_points.append(stats['attack_time'])
            mean_values.append(stats['mean'])
            std_values.append(stats['std'])
            min_values.append(stats['min'])
            max_values.append(stats['max'])
            
            # 获取原始重复数据
            raw_data = data['raw_data'][time_key]['repeat_results']
            raw_data_all.append(raw_data)
    else:
        # 使用分析结果数据（向后兼容）
        sorted_patterns = sorted(data['error_patterns'].items(), key=lambda x: x[1]['attack_time'])
        
        for time_key, pattern_data in sorted_patterns:
            time_points.append(pattern_data['attack_time'])
            
            # 计算总错误数量
            total_errors = sum(pattern_data['bank_error_counts'].values())
            mean_values.append(total_errors)
            std_values.append(0)  # 分析结果没有标准差信息
            min_values.append(total_errors)
            max_values.append(total_errors)
            raw_data_all.append([total_errors])
    
    time_points = np.array(time_points)
    mean_values = np.array(mean_values)
    std_values = np.array(std_values)
    min_values = np.array(min_values)
    max_values = np.array(max_values)
    
    # 创建单个图表
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # 主折线图：平均值和误差条
    ax.errorbar(time_points, mean_values, yerr=std_values, 
                capsize=8, capthick=2, marker='o', markersize=10, 
                linewidth=3, label='Mean ± Std', color='blue', elinewidth=2)
    
    # 绘制最大值和最小值的连线区域（不显示线条，只填充区域）
    ax.fill_between(time_points, min_values, max_values, 
                    alpha=0.35, label='Min-Max Range', color='steelblue',
                    interpolate=True)
    
    # 注释：移除原始测试点散点图以获得更清洁的外观
    # 原来的红色散点图代码已被移除
    
    # 在每个数据点上添加数值标注
    for i, (t, mean, std) in enumerate(zip(time_points, mean_values, std_values)):
        if mean > 0:  # 只标注非零数据点
            ax.annotate(f'{mean:.1f}±{std:.1f}', 
                       (t, mean), 
                       textcoords="offset points", 
                       xytext=(0, 15), 
                       ha='center', va='bottom',
                       fontsize=9, 
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    # 设置坐标轴和标题
    ax.set_xlabel('Retention Time (seconds)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Bit Flips', fontsize=14, fontweight='bold')
    ax.set_title('Bit Flip Errors vs Retention Time', fontsize=16, fontweight='bold', pad=20)
    
    # 美化网格
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=12, loc='upper left')
    
    # 设置坐标轴范围和格式
    ax.set_xlim(min(time_points) * 0.9, max(time_points) * 1.1)
    if max(mean_values) > 0:
        ax.set_ylim(0, max(max_values) * 1.1)
    
    # 美化坐标轴
    ax.tick_params(axis='both', which='major', labelsize=11)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)
    
    # 添加坐标轴箭头
    # X轴箭头
    ax.annotate('', xy=(max(time_points) * 1.08, 0), xytext=(max(time_points) * 1.02, 0),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    
    # Y轴箭头
    if max(mean_values) > 0:
        y_max = max(max_values) * 1.1
        ax.annotate('', xy=(0, y_max * 0.98), xytext=(0, y_max * 0.92),
                    arrowprops=dict(arrowstyle='->', color='black', lw=1.5))
    
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
    
    # 检查数据格式
    if 'statistics' in data and 'raw_data' in data:
        # 原始数据格式
        print("使用原始测试数据生成摘要")
        sorted_stats = sorted(data['statistics'].items(), key=lambda x: x[1]['attack_time'])
        
        for time_key, stats in sorted_stats:
            raw_data = data['raw_data'][time_key]['repeat_results']
            
            summary_data.append({
                'Retention Time (s)': stats['attack_time'],
                'Mean Bit Flips': stats['mean'],
                'Std Dev': stats['std'],
                'Min': stats['min'],
                'Max': stats['max'],
                'Coefficient of Variation': stats['std'] / stats['mean'] if stats['mean'] > 0 else 0,
                'Raw Data': ', '.join(map(str, raw_data))
            })
        
        # 打印摘要表格
        print("\n" + "=" * 90)
        print("Bit翻转测试结果摘要表")
        print("=" * 90)
        
        # 格式化打印
        for i, row in enumerate(summary_data):
            print(f"Time: {row['Retention Time (s)']:6.2f}s | "
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
            
            df = pd.DataFrame(summary_data)
            df.to_csv(table_path, index=False)
            print(f"\n摘要表格已保存到: {table_path}")
        
    else:
        # 分析结果格式（向后兼容）
        print("使用分析结果数据生成摘要")
        sorted_patterns = sorted(data['error_patterns'].items(), key=lambda x: x[1]['attack_time'])
        
        for time_key, pattern_data in sorted_patterns:
            total_errors = sum(pattern_data['bank_error_counts'].values())
            unique_rows = len(pattern_data['unique_error_rows'])
            
            # 找到最易受攻击的行
            most_vulnerable = []
            if pattern_data['row_error_counts']:
                sorted_rows = sorted(pattern_data['row_error_counts'].items(), 
                                   key=lambda x: x[1], reverse=True)
                most_vulnerable = [f"Row {row}({count})" for row, count in sorted_rows[:3]]
            
            summary_data.append({
                'Retention Time (s)': pattern_data['attack_time'],
                'Total Errors': total_errors,
                'Unique Affected Rows': unique_rows,
                'Most Vulnerable Rows': '; '.join(most_vulnerable) if most_vulnerable else 'None',
                'Banks Affected': len(pattern_data['bank_error_counts']),
                'Bank Error Distribution': ', '.join([f"Bank{k}:{v}" for k, v in pattern_data['bank_error_counts'].items()])
            })
        
        # 打印摘要表格
        print("\n" + "=" * 100)
        print("内存错误分析摘要表")
        print("=" * 100)
        
        df = pd.DataFrame(summary_data)
        # 格式化打印
        for i, row in df.iterrows():
            print(f"Time: {row['Retention Time (s)']:6.2f}s | "
                  f"Total Errors: {row['Total Errors']:6d} | "
                  f"Unique Rows: {row['Unique Affected Rows']:4d} | "
                  f"Banks: {row['Banks Affected']:1d}")
            if row['Most Vulnerable Rows'] != 'None':
                print(f"         Most Vulnerable: {row['Most Vulnerable Rows']}")
        
        # 保存到文件
        if output_dir:
            output_dir = Path(output_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            table_filename = f"memory_error_summary_{timestamp}.csv"
            table_path = output_dir / table_filename
            
            df.to_csv(table_path, index=False)
            print(f"\n摘要表格已保存到: {table_path}")
    
    # 打印总体统计
    print("\n" + "=" * 50)
    print("总体统计信息:")
    print(f"测试时间范围: {data['metadata']['start_time']}s - {data['metadata']['end_time']}s")
    print(f"测试点数量: {data['metadata']['num_points']}")
    print(f"重复测试次数: {data['metadata']['num_repeats']}")
    
    if 'summary' in data:
        print(f"总测试次数: {data['summary']['total_tests']}")
    if 'bank_summary' in data:
        print(f"受影响的银行总数: {data['bank_summary']['total_affected_banks']}")
    
    return pd.DataFrame(summary_data) if summary_data else None

def find_latest_test_file(result_dir):
    """
    在result目录中找到最新的测试文件，优先选择原始数据文件
    
    Args:
        result_dir: result/retention目录路径
        
    Returns:
        str: 最新测试文件的路径，如果没找到则返回None
    """
    
    result_path = Path(result_dir)
    
    if not result_path.exists():
        return None
    
    # 首先查找原始测试数据文件（不含_analysis的JSON文件）
    json_files = list(result_path.glob("bitflip_time_test_*.json"))
    raw_files = [f for f in json_files if not f.name.endswith('_analysis.json')]
    
    if raw_files:
        # 找到原始数据文件，返回最新的
        latest_file = max(raw_files, key=lambda x: x.stat().st_mtime)
        return str(latest_file)
    
    # 如果没有原始数据文件，查找分析结果文件
    analysis_files = list(result_path.glob("bitflip_time_test_*_analysis.json"))
    
    if analysis_files:
        # 找到分析结果文件
        latest_file = max(analysis_files, key=lambda x: x.stat().st_mtime)
        return str(latest_file)
    
    return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='绘制内存错误分析结果的可视化图表')
    parser.add_argument('--input', '-i', type=str, 
                       help='输入的分析结果JSON文件路径 (如果不指定，将自动查找最新的分析文件)')
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
        result_dir = script_dir  # 脚本就在result/retention目录下
        
        input_file = find_latest_test_file(result_dir)
        if not input_file:
            print("错误: 未找到测试数据文件")
            print("请先运行 bitflip_time_test.py 生成测试数据，")
            print("或使用 --input 参数指定数据文件路径")
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
    print(f"  测试类型: {data['metadata']['test_type']}")
    
    # 根据数据格式显示不同的统计信息
    if 'summary' in data:
        print(f"  总测试次数: {data['summary']['total_tests']}")
    if 'bank_summary' in data:
        print(f"  受影响银行: {data['bank_summary']['total_affected_banks']}")
    
    # 创建图表
    print(f"\n生成Bit翻转分析图表...")
    fig = create_bitflip_time_plot(data, output_dir, not args.no_show)
    
    # 创建摘要表格
    print(f"\n生成统计摘要表格...")
    df = create_summary_table(data, output_dir)
    
    print(f"\nBit翻转分析可视化完成!")

if __name__ == "__main__":
    main()
