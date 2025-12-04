#!/usr/bin/env python3
"""
HCfirst数据可视化脚本
读取多个HCfirst测试结果文件，汇总数据并绘制分布图

基本使用方法:
  python plot_hcfirst.py                              # 自动查找所有HCfirst结果文件
  python plot_hcfirst.py file1.json file2.json       # 指定特定文件
  python plot_hcfirst.py --pattern "HCfirst_fast_*"   # 使用通配符模式

输出定制选项:
  python plot_hcfirst.py --output my_plot.png         # 指定输出文件名
  python plot_hcfirst.py --format pdf                 # 指定格式(png/pdf/svg/jpg)
  python plot_hcfirst.py --dpi 600                    # 设置分辨率
  python plot_hcfirst.py --figsize 16,10              # 设置图片尺寸(宽,高)

图表定制选项:
  python plot_hcfirst.py --title "Memory Test Results"  # 自定义标题
  python plot_hcfirst.py --no-stats                   # 不显示统计信息
  python plot_hcfirst.py --compact                    # 紧凑模式：自动分段显示
  python plot_hcfirst.py --compact --gap-threshold 100 # 自定义分段阈值

常用组合示例:
  python plot_hcfirst.py *.json --output summary.pdf --format pdf --dpi 600
  python plot_hcfirst.py --pattern "HCfirst_detailed_*" --title "Detailed Analysis" --figsize 20,12
  python plot_hcfirst.py HCfirst_*.json --output hcfirst_plot.jpg --format jpg
  python plot_hcfirst.py --compact --output compact_view.png  # 紧凑视图，自动分段显示

"""

import os
import sys
import json
import glob
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime

# 设置字体支持，避免中文字体警告
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='HCfirst数据可视化工具')
    parser.add_argument('files', nargs='*', 
                       help='JSON结果文件路径（可指定多个文件）')
    parser.add_argument('--pattern', type=str, default="HCfirst_*.json",
                       help='文件匹配模式 (默认: HCfirst_*.json)')
    parser.add_argument('--output', type=str, 
                       help='输出图片文件名 (默认: 自动生成)')
    parser.add_argument('--format', type=str, default='png', 
                       choices=['png', 'pdf', 'svg', 'jpg'],
                       help='输出图片格式 (默认: png)')
    parser.add_argument('--dpi', type=int, default=300,
                       help='图片分辨率 (默认: 300)')
    parser.add_argument('--figsize', type=str, default='12,8',
                       help='图片尺寸 宽,高 (默认: 12,8)')
    parser.add_argument('--title', type=str,
                       help='图表标题 (默认: 自动生成)')
    parser.add_argument('--no-stats', action='store_true',
                       help='不显示统计信息')
    parser.add_argument('--compact', action='store_true',
                       help='紧凑模式：自动检测数据段并紧密排列')
    parser.add_argument('--gap-threshold', type=int, default=200,
                       help='数据段分割阈值：行号间隔超过此值则分段 (默认: 200)')
    return parser.parse_args()

class HCFirstPlotter:
    def __init__(self):
        self.data = {}  # {row_number: hcfirst_value}
        self.file_info = []  # 记录处理的文件信息
        
    def load_json_file(self, file_path):
        """加载单个JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_data = {}
            file_stats = {"rows": 0, "format": "unknown"}
            
            # 检测文件格式并提取数据
            if "results" in data and isinstance(data["results"], dict):
                # 快速版本格式: {"results": {"row": hcfirst}}
                for row_str, hcfirst in data["results"].items():
                    if row_str.isdigit():
                        file_data[int(row_str)] = hcfirst
                file_stats["format"] = "fast"
                file_stats["rows"] = len(file_data)
                
            elif isinstance(data, dict):
                # 检查是否为新的行号组织格式: {"row": {"row": int, "hcfirst": int, ...}}
                found_data = False
                for row_key, row_data in data.items():
                    if row_key.isdigit() and isinstance(row_data, dict) and "hcfirst" in row_data:
                        try:
                            row = int(row_key)
                            hcfirst = row_data["hcfirst"]
                            file_data[row] = hcfirst
                            found_data = True
                        except (ValueError, TypeError):
                            continue
                
                if found_data:
                    file_stats["format"] = "row-organized"
                    file_stats["rows"] = len(file_data)
                else:
                    # 检查是否为旧的详细版本格式
                    for read_count_key, read_count_data in data.items():
                        if read_count_key.isdigit() and isinstance(read_count_data, dict):
                            for pair_key, pair_data in read_count_data.items():
                                if pair_key.startswith("pair_") and isinstance(pair_data, dict):
                                    # 提取行号
                                    parts = pair_key.split("_")
                                    if len(parts) >= 3:
                                        try:
                                            row = int(parts[1])
                                            hcfirst = int(read_count_key)
                                            file_data[row] = hcfirst
                                            found_data = True
                                        except ValueError:
                                            continue
                    
                    if found_data:
                        file_stats["format"] = "detailed"
                        file_stats["rows"] = len(file_data)
                    else:
                        # 尝试简单的 {row: hcfirst} 格式
                        for key, value in data.items():
                            try:
                                row = int(key)
                                hcfirst = int(value)
                                file_data[row] = hcfirst
                            except (ValueError, TypeError):
                                continue
                        
                        if file_data:
                            file_stats["format"] = "simple"
                            file_stats["rows"] = len(file_data)
            
            if file_data:
                # 合并到主数据集
                self.data.update(file_data)
                
                # 记录文件信息
                file_stats.update({
                    "file": os.path.basename(file_path),
                    "path": file_path,
                    "row_range": f"{min(file_data.keys())}-{max(file_data.keys())}" if file_data else "empty"
                })
                self.file_info.append(file_stats)
                
                print(f"✓ 加载文件: {os.path.basename(file_path)}")
                print(f"  格式: {file_stats['format']}, 行数: {file_stats['rows']}, 范围: {file_stats['row_range']}")
                
                return True
            else:
                print(f"✗ 文件格式不支持或无数据: {file_path}")
                return False
                
        except Exception as e:
            print(f"✗ 加载文件失败: {file_path} - {str(e)}")
            return False
    
    def find_result_files(self, pattern):
        """查找结果文件"""
        # 在当前目录查找
        files = glob.glob(pattern)
        
        # 如果当前目录没有，在脚本目录查找
        if not files:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            files = glob.glob(os.path.join(script_dir, pattern))
        
        return sorted(files)
    
    def load_data(self, file_paths=None, pattern="HCfirst_*.json"):
        """加载数据"""
        if file_paths:
            # 使用指定的文件
            files_to_load = file_paths
        else:
            # 自动查找文件
            files_to_load = self.find_result_files(pattern)
        
        if not files_to_load:
            print(f"错误: 未找到匹配的文件: {pattern}")
            return False
        
        print(f"发现 {len(files_to_load)} 个文件:")
        for f in files_to_load:
            print(f"  {f}")
        print()
        
        success_count = 0
        for file_path in files_to_load:
            if self.load_json_file(file_path):
                success_count += 1
        
        print(f"\n成功加载 {success_count}/{len(files_to_load)} 个文件")
        print(f"总数据点: {len(self.data)}")
        
        if self.data:
            rows = list(self.data.keys())
            print(f"行号范围: {min(rows)} - {max(rows)}")
            print(f"HCfirst范围: {min(self.data.values()):,} - {max(self.data.values()):,}")
        
        return len(self.data) > 0
    
    def detect_data_segments(self, gap_threshold=200):
        """检测数据段，将相邻的行分组"""
        if not self.data:
            return []
        
        # 按行号排序
        sorted_rows = sorted(self.data.keys())
        segments = []
        current_segment = [sorted_rows[0]]
        
        for i in range(1, len(sorted_rows)):
            current_row = sorted_rows[i]
            prev_row = sorted_rows[i-1]
            
            # 如果间隔小于阈值，归入当前段
            if current_row - prev_row <= gap_threshold:
                current_segment.append(current_row)
            else:
                # 间隔过大，开始新的段
                segments.append(current_segment)
                current_segment = [current_row]
        
        # 添加最后一段
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def create_compact_mapping(self, segments, segment_gap=50):
        """创建紧凑的坐标映射"""
        mapping = {}  # {original_row: new_x_position}
        x_ticks = []  # [(position, label)]
        x_position = 0
        
        for i, segment in enumerate(segments):
            segment_start = x_position
            
            # 为当前段的每个行号分配x坐标
            for j, row in enumerate(segment):
                mapping[row] = x_position
                x_position += 1
            
            segment_end = x_position - 1
            
            # 添加段标签（显示原始行号范围）
            segment_center = (segment_start + segment_end) / 2
            segment_label = f"{segment[0]}-{segment[-1]}" if len(segment) > 1 else str(segment[0])
            x_ticks.append((segment_center, segment_label))
            
            # 如果不是最后一段，添加间隔
            if i < len(segments) - 1:
                x_position += segment_gap
        
        return mapping, x_ticks
    
    def create_plot(self, figsize=(12, 8), title=None, show_stats=True, compact_mode=False, gap_threshold=200):
        """创建图表"""
        if not self.data:
            print("错误: 无数据可绘制")
            return None
        
        fig, ax = plt.subplots(figsize=figsize, dpi=100)
        
        # 准备数据
        rows = list(self.data.keys())
        hcfirst_values = list(self.data.values())
        
        if compact_mode:
            # 检测数据段
            segments = self.detect_data_segments(gap_threshold)
            print(f"检测到 {len(segments)} 个数据段:")
            for i, segment in enumerate(segments):
                print(f"  段 {i+1}: 行号 {segment[0]} - {segment[-1]} ({len(segment)} 个数据点)")
            
            if len(segments) > 1:
                # 创建紧凑映射
                row_mapping, x_ticks = self.create_compact_mapping(segments)
                
                # 转换x坐标
                x_coords = [row_mapping[row] for row in rows]
                
                # 绘制散点图
                ax.scatter(x_coords, hcfirst_values, s=8, alpha=0.8, color='#1E5F8B', edgecolors='none')
                
                # 设置x轴标签
                tick_positions, tick_labels = zip(*x_ticks)
                ax.set_xticks(tick_positions)
                ax.set_xticklabels(tick_labels, rotation=0, ha='center')
                ax.set_xlabel('Memory Row Range', fontsize=12)
                
                # 添加段边界分割线
                for i, segment in enumerate(segments):
                    # 每个段的开始和结束位置
                    segment_start_row = segment[0]
                    segment_end_row = segment[-1]
                    segment_start_x = row_mapping[segment_start_row]
                    segment_end_x = row_mapping[segment_end_row]
                    
                    # 在段开始前画分割线
                    ax.axvline(x=segment_start_x - 0.5, color='gray', linestyle='--', alpha=0.7, linewidth=1)
                    # 在段结束后画分割线
                    ax.axvline(x=segment_end_x + 0.5, color='gray', linestyle='--', alpha=0.7, linewidth=1)
                
                # 设置x轴范围
                ax.set_xlim(-10, max(x_coords) + 10)
            else:
                # 只有一个段，使用普通模式
                ax.scatter(rows, hcfirst_values, s=8, alpha=0.8, color='#1E5F8B', edgecolors='none')
                ax.set_xlim(min(rows) - 50, max(rows) + 50)
                ax.set_xlabel('Memory Row Number', fontsize=12)
        else:
            # 普通模式：绘制散点图（小点）
            ax.scatter(rows, hcfirst_values, s=8, alpha=0.8, color='#1E5F8B', edgecolors='none')
            ax.set_xlim(min(rows) - 50, max(rows) + 50)
            ax.set_xlabel('Memory Row Number', fontsize=12)
        
        # 设置标题
        if title is None:
            mode_suffix = " (Compact)" if compact_mode else ""
            if len(self.file_info) == 1:
                title = f"HCfirst Distribution - {self.file_info[0]['file']}{mode_suffix}"
            else:
                title = f"HCfirst Distribution - {len(self.file_info)} files merged{mode_suffix}"
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_ylabel('HCfirst Value (Hammer Count)', fontsize=12)
        
        # 格式化y轴刻度
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 设置y轴范围
        y_margin = (max(hcfirst_values) - min(hcfirst_values)) * 0.05
        ax.set_ylim(min(hcfirst_values) - y_margin, max(hcfirst_values) + y_margin)
        
        # 添加统计信息
        if show_stats:
            stats_text = self.get_stats_text()
            if compact_mode and len(segments) > 1:
                stats_text += f"\nSegments: {len(segments)}"
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   verticalalignment='top', fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        return fig
    
    def get_stats_text(self):
        """生成统计信息文本"""
        values = list(self.data.values())
        stats = [
            f"Data points: {len(values)}",
            f"Min: {min(values):,}",
            f"Max: {max(values):,}",
            f"Mean: {np.mean(values):,.0f}",
            f"Median: {np.median(values):,.0f}",
            f"Std Dev: {np.std(values):,.0f}"
        ]
        return "\n".join(stats)
    
    def save_plot(self, fig, output_path, format='png', dpi=300):
        """保存图表"""
        try:
            fig.savefig(output_path, format=format, dpi=dpi, bbox_inches='tight')
            print(f"✓ 图表已保存: {output_path}")
            return True
        except Exception as e:
            print(f"✗ 保存失败: {str(e)}")
            return False

def main():
    args = parse_args()
    
    # 解析图片尺寸
    try:
        figsize = tuple(map(float, args.figsize.split(',')))
    except:
        figsize = (12, 8)
        print("警告: 图片尺寸格式错误，使用默认值 (12,8)")
    
    # 创建绘图器
    plotter = HCFirstPlotter()
    
    # 加载数据
    if not plotter.load_data(args.files, args.pattern):
        sys.exit(1)
    
    # 创建图表
    fig = plotter.create_plot(figsize=figsize, title=args.title, show_stats=not args.no_stats, 
                             compact_mode=args.compact, gap_threshold=args.gap_threshold)
    if fig is None:
        sys.exit(1)
    
    # 生成输出文件名
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"hcfirst_plot_{timestamp}.{args.format}"
        
        # 确保保存在当前脚本所在的目录（HCfirst文件夹）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, output_filename)
    
    # 保存图表
    if plotter.save_plot(fig, output_path, args.format, args.dpi):
        print(f"\n绘图完成! 图表保存在: {output_path}")
    
    # 显示图表
    try:
        plt.show()
    except:
        print("注意: 无法显示图表（可能没有图形界面）")

if __name__ == "__main__":
    main()
