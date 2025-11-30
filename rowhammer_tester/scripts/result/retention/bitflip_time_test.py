#!/usr/bin/env python3
"""
内存retention时间测试脚本 - 测试bit翻转数量随保持时间变化。

这个脚本测试DDR4内存的数据保持能力，通过以下步骤：
1. 向内存写入测试模式 (all-1)
2. 关闭内存刷新
3. 等待指定时间让电荷自然衰减
4. 恢复刷新并检测bit翻转

注意：这不是传统的rowhammer攻击测试，而是内存retention特性测试。

使用方法: python bitflip_time_test.py
"""

import os
import sys
import json
import time
import numpy as np
import subprocess
from pathlib import Path
from datetime import datetime

# =============================================================================
# 测试配置 - 直接在这里修改所有参数
# =============================================================================
START_TIME = 0.1      # 起始时间（秒）
END_TIME = 5.0        # 终止时间（秒）
NUM_POINTS = 10       # 测试点数
NUM_REPEATS = 5       # 每个时间点重复测试次数

# 文件保存配置
OUTPUT_DIR = "result/retention"          # 输出目录（scripts/result/retention）
OUTPUT_PREFIX = "bitflip_time_test"      # 文件名前缀
OUTPUT_SUFFIX = ""                       # 文件名后缀
# =============================================================================

def generate_time_points(start, end, num_points):
    """生成均匀分布的时间点"""
    return np.linspace(start, end, num_points)

def run_rowhammer_test(attack_time_sec):
    """
    运行单次retention测试 (原rowhammer测试，实际为内存数据保持测试)
    
    Args:
        attack_time_sec: 等待时间（秒）
        
    Returns:
        tuple: (总bit翻转数量, 详细错误信息)
    """
    # 将秒转换为纳秒
    attack_time_ns = int(attack_time_sec * 1e9)
    
    print(f"开始测试时间点: {attack_time_sec:.2f}s (attack_time_ns: {attack_time_ns})")
    
    try:
        # 直接调用Python模块而不是subprocess，以获取详细的错误信息
        import sys
        from pathlib import Path
        
        # 确保能够导入rowhammer模块
        scripts_path = Path(__file__).parent
        sys.path.insert(0, str(scripts_path))
        
        from hw_rowhammer import HwRowHammer
        from rowhammer import main as rowhammer_main
        from utils import RemoteClient, get_litedram_settings
        
        # 创建连接
        wb = RemoteClient()
        wb.open()
        
        # 获取设置
        settings = get_litedram_settings()
        
        # 创建HwRowHammer实例
        row_hammer = HwRowHammer(
            wb=wb,
            settings=settings,
            nrows=0,  # 在no_attack_time模式下无效，使用默认值
            column=0,
            bank=0,
            rows_start=0,
            no_refresh=True,
            verbose=True,
            payload_executor=False,
            no_attack_time=attack_time_ns,
            data_inversion=False
        )
        
        # 生成测试模式
        def pattern_generator(rows):
            return {row: 0xffffffff for row in rows}  # all_1 pattern
        
        # 运行测试
        print(f"  执行retention测试 (等待时间: {attack_time_sec:.2f}s)...")
        errors_in_rows = row_hammer.run(
            row_pairs=[],  # 空的row_pairs，因为使用no_attack_time模式
            pattern_generator=pattern_generator,
            read_count=0,  # 不相关，因为使用no_attack_time
            verify_initial=True
        )
        
        wb.close()
        
        # 计算总的bit翻转数量和整理错误详情
        total_bitflips = 0
        detailed_errors = {}
        
        # errors_in_rows 是从 display_errors 返回的格式:
        # {"row_num_str": {'bank': bank_num, 'row': row_num, 'col': {col_num: [bitflip_positions]}, 'bitflips': count}}
        for row_num_str, error_summary in errors_in_rows.items():
            if error_summary:  # 如果该行有错误
                row_num = error_summary.get('row', int(row_num_str))
                bank_num = error_summary.get('bank', 0)  # 获取bank信息
                row_bitflips = error_summary.get('bitflips', 0)
                col_info = error_summary.get('col', {})
                
                total_bitflips += row_bitflips
                
                # 转换列信息格式，保持与原预期JSON格式一致
                col_details = {}
                for col_num, bitflip_positions in col_info.items():
                    col_details[col_num] = {
                        'bitflip_positions': bitflip_positions,
                        'total_bitflips': len(bitflip_positions) if isinstance(bitflip_positions, list) else 1
                    }
                
                detailed_errors[row_num] = {
                    "bank": bank_num,  # 添加bank信息
                    "row": row_num,
                    "col": col_details,
                    "bitflips": row_bitflips
                }
        
        print(f"  检测到 {total_bitflips} 个bit翻转")
        if detailed_errors:
            print(f"  错误分布在 {len(detailed_errors)} 个行中")
        
        return total_bitflips, detailed_errors
        
    except Exception as e:
        print(f"  运行测试时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 0, {}

def run_time_series_test(start_time, end_time, num_points, num_repeats):
    """运行完整的时间序列retention测试"""
    
    # 生成时间点
    time_points = generate_time_points(start_time, end_time, num_points)
    
    # 结果存储
    test_results = {
        'metadata': {
            'start_time': float(start_time),
            'end_time': float(end_time),
            'num_points': int(num_points),
            'num_repeats': int(num_repeats),
            'test_type': 'retention',  # 明确标识这是retention测试
            'test_timestamp': datetime.now().isoformat(),
            'time_points': [float(x) for x in time_points.tolist()]
        },
        'raw_data': {},
        'statistics': {}
    }
    
    print(f"开始时间序列retention测试")
    print(f"时间范围: {start_time}s - {end_time}s")
    print(f"测试点数: {num_points}")
    print(f"重复次数: {num_repeats}")
    print(f"测试类型: 内存数据保持时间测试 (retention)")
    print(f"时间点: {time_points}")
    print("=" * 60)
    
    # 对每个时间点进行测试
    for i, attack_time in enumerate(time_points):
        print(f"\n[{i+1}/{num_points}] 测试时间点: {attack_time:.2f}s")
        
        # 存储该时间点的所有重复测试结果
        repeat_results = []
        repeat_details = []
        
        # 重复测试
        for repeat in range(num_repeats):
            print(f"  重复 {repeat+1}/{num_repeats}...")
            
            bitflips, details = run_rowhammer_test(attack_time)
            repeat_results.append(bitflips)
            repeat_details.append(details)
            
            print(f"  结果: {bitflips} bit翻转")
            
            # 如果发生错误，增加等待时间让硬件恢复
            if bitflips == 0 and details == {}:
                print("  检测到可能的硬件状态问题，延长等待时间...")
                time.sleep(5)
            else:
                # 正常情况下短暂延时避免硬件过热
                time.sleep(3)
        
        # 计算统计数据
        mean_bitflips = np.mean(repeat_results)
        std_bitflips = np.std(repeat_results)
        min_bitflips = np.min(repeat_results)
        max_bitflips = np.max(repeat_results)
        
        # 存储结果 - 转换为Python原生类型避免JSON序列化问题
        test_results['raw_data'][f'{attack_time:.2f}'] = {
            'attack_time': float(attack_time),
            'repeat_results': [int(x) for x in repeat_results],
            'repeat_details': repeat_details,  # 保留详细的错误信息
            'errors_summary': {
                'total_rows_with_errors': len(set().union(*[details.keys() for details in repeat_details if details])),
                'max_errors_in_single_test': max(repeat_results) if repeat_results else 0,
                'min_errors_in_single_test': min(repeat_results) if repeat_results else 0
            }
        }
        
        test_results['statistics'][f'{attack_time:.2f}'] = {
            'attack_time': float(attack_time),
            'mean': float(mean_bitflips),
            'std': float(std_bitflips),
            'min': int(min_bitflips),
            'max': int(max_bitflips)
        }
        
        print(f"  统计结果: 平均={mean_bitflips:.2f}, 标准差={std_bitflips:.2f}, 范围=[{min_bitflips}, {max_bitflips}]")
    
    return test_results

def save_results(results, output_dir, output_prefix, output_suffix=""):
    """保存测试结果到文件"""
    
    # 处理输出目录路径
    if not os.path.isabs(output_dir):
        # 如果是相对路径，相对于脚本所在目录
        script_dir = Path(__file__).parent
        output_dir = script_dir / output_dir
    else:
        output_dir = Path(output_dir)
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 构建文件名
    if output_suffix:
        base_filename = f"{output_prefix}_{timestamp}_{output_suffix}"
    else:
        base_filename = f"{output_prefix}_{timestamp}"
    
    json_filename = f"{base_filename}.json"
    csv_filename = f"{base_filename}.csv"
    
    json_filepath = output_dir / json_filename
    csv_filepath = output_dir / csv_filename
    
    # 保存JSON数据
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 同时保存简化的CSV格式数据
    with open(csv_filepath, 'w', encoding='utf-8') as f:
        f.write("attack_time,mean_bitflips,std_bitflips,min_bitflips,max_bitflips,total_rows_with_errors,raw_data\n")
        
        for time_key, stats in results['statistics'].items():
            attack_time = stats['attack_time']
            mean = stats['mean']
            std = stats['std']
            min_val = stats['min']
            max_val = stats['max']
            raw_data = results['raw_data'][time_key]['repeat_results']
            raw_str = ';'.join(map(str, raw_data))
            
            # 获取错误行数统计
            errors_summary = results['raw_data'][time_key].get('errors_summary', {})
            total_rows_with_errors = errors_summary.get('total_rows_with_errors', 0)
            
            f.write(f"{attack_time},{mean},{std},{min_val},{max_val},{total_rows_with_errors},\"{raw_str}\"\n")
    
    # 保存详细的错误分析文件
    analysis_filename = f"{base_filename}_analysis.json"
    analysis_filepath = output_dir / analysis_filename
    
    # 生成详细的错误分析
    detailed_analysis = {
        'metadata': results['metadata'],
        'summary': {
            'total_tests': sum(results['metadata']['num_repeats'] for _ in results['statistics']),
            'time_points_tested': len(results['statistics']),
            'attack_time_range': [results['metadata']['start_time'], results['metadata']['end_time']]
        },
        'error_patterns': {},
        'bank_summary': {}  # 新增：bank级别的总体统计
    }
    
    # 收集所有时间点的bank统计
    all_bank_errors = {}
    all_affected_banks = set()
    
    # 分析错误模式
    for time_key, raw_data in results['raw_data'].items():
        attack_time = raw_data['attack_time']
        repeat_details = raw_data['repeat_details']
        
        # 统计该时间点的错误模式
        all_error_rows = set()
        row_error_counts = {}
        bank_error_counts = {}  # 新增：bank级别的错误统计
        bank_row_distribution = {}  # 新增：每个bank中的错误行分布
        
        for repeat_idx, details in enumerate(repeat_details):
            for row_num, row_info in details.items():
                all_error_rows.add(row_num)
                bank_num = row_info.get('bank', 0)
                bitflips = row_info.get('bitflips', 0)
                
                # 行级别统计
                if row_num not in row_error_counts:
                    row_error_counts[row_num] = 0
                row_error_counts[row_num] += bitflips
                
                # Bank级别统计
                if bank_num not in bank_error_counts:
                    bank_error_counts[bank_num] = 0
                    bank_row_distribution[bank_num] = set()
                bank_error_counts[bank_num] += bitflips
                bank_row_distribution[bank_num].add(row_num)
        
        # 转换set为list以便JSON序列化
        bank_row_dist_serializable = {
            bank: list(rows) for bank, rows in bank_row_distribution.items()
        }
        
        detailed_analysis['error_patterns'][time_key] = {
            'attack_time': attack_time,
            'unique_error_rows': list(all_error_rows),
            'row_error_counts': row_error_counts,
            'most_vulnerable_rows': sorted(row_error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'bank_error_counts': bank_error_counts,  # 新增
            'bank_row_distribution': bank_row_dist_serializable,  # 新增
            'most_vulnerable_banks': sorted(bank_error_counts.items(), key=lambda x: x[1], reverse=True)[:5]  # 新增
        }
        
        # 收集bank统计信息用于总体分析
        for bank_num, error_count in bank_error_counts.items():
            if bank_num not in all_bank_errors:
                all_bank_errors[bank_num] = 0
            all_bank_errors[bank_num] += error_count
            all_affected_banks.add(bank_num)
    
    # 生成bank级别的总体统计
    detailed_analysis['bank_summary'] = {
        'total_affected_banks': len(all_affected_banks),
        'bank_error_totals': all_bank_errors,
        'most_vulnerable_banks_overall': sorted(all_bank_errors.items(), key=lambda x: x[1], reverse=True),
        'bank_vulnerability_ranking': {
            bank: rank for rank, (bank, _) in enumerate(
                sorted(all_bank_errors.items(), key=lambda x: x[1], reverse=True), 1
            )
        }
    }
    
    # 临时保存分析数据到results中，供analyze_bank_distribution使用
    results['analysis_cache'] = detailed_analysis
    
    # 保存详细分析
    with open(analysis_filepath, 'w', encoding='utf-8') as f:
        json.dump(detailed_analysis, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到:")
    print(f"  JSON详细数据: {json_filepath}")
    print(f"  CSV统计数据: {csv_filepath}")
    print(f"  详细分析数据: {analysis_filepath}")
    
    return json_filepath, csv_filepath, analysis_filepath

def analyze_bank_distribution(results):
    """分析bank级别的错误分布"""
    print("\n" + "=" * 60)
    print("Bank级别错误分布分析")
    print("=" * 60)
    
    for time_key, stats in results['statistics'].items():
        attack_time = stats['attack_time']
        error_patterns = results.get('analysis_cache', {}).get('error_patterns', {}).get(time_key, {})
        
        bank_counts = error_patterns.get('bank_error_counts', {})
        bank_distribution = error_patterns.get('bank_row_distribution', {})
        
        if bank_counts:
            print(f"\n时间点 {attack_time:.2f}s:")
            print(f"  受影响的Bank数量: {len(bank_counts)}")
            
            # 按错误数量排序显示bank
            sorted_banks = sorted(bank_counts.items(), key=lambda x: x[1], reverse=True)
            for bank_num, error_count in sorted_banks[:5]:  # 显示前5个最严重的bank
                rows_in_bank = len(bank_distribution.get(str(bank_num), []))
                print(f"  Bank {bank_num}: {error_count} bit翻转, 影响 {rows_in_bank} 行")

def main():
    """主函数"""
    print("=" * 60)
    print("内存Retention时间测试脚本")
    print("=" * 60)
    print(f"测试配置:")
    print(f"  时间范围: {START_TIME}s - {END_TIME}s")
    print(f"  测试点数: {NUM_POINTS}")
    print(f"  重复次数: {NUM_REPEATS}")
    print(f"  测试类型: 内存数据保持时间测试 (retention)")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"  文件前缀: {OUTPUT_PREFIX}")
    if OUTPUT_SUFFIX:
        print(f"  文件后缀: {OUTPUT_SUFFIX}")
    print("=" * 60)
    
    # 检查是否在正确的目录
    if not os.path.exists('hw_rowhammer.py'):
        print("错误: 找不到 hw_rowhammer.py 文件")
        print("请确保在 rowhammer_tester/scripts 目录下运行此脚本")
        sys.exit(1)
    
    try:
        # 运行测试
        results = run_time_series_test(
            START_TIME, 
            END_TIME, 
            NUM_POINTS, 
            NUM_REPEATS
        )
        
        # 保存结果
        json_path, csv_path, analysis_path = save_results(
            results, 
            OUTPUT_DIR, 
            OUTPUT_PREFIX, 
            OUTPUT_SUFFIX
        )
        
        # 显示测试摘要
        print("\n" + "=" * 60)
        print("Retention测试完成!")
        print("=" * 60)
        print(f"测试时间范围: {START_TIME}s - {END_TIME}s")
        print(f"测试点数: {NUM_POINTS}")
        print(f"重复次数: {NUM_REPEATS}")
        print(f"测试类型: 内存数据保持时间测试")
        
        print("\n测试结果摘要:")
        for time_key, stats in results['statistics'].items():
            raw_data = results['raw_data'][time_key]
            total_rows = raw_data['errors_summary']['total_rows_with_errors']
            print(f"  {stats['attack_time']:6.2f}s: 平均 {stats['mean']:6.1f} ± {stats['std']:5.1f} bit翻转, 影响 {total_rows} 行")
        
        # 显示bank级别的分析
        analyze_bank_distribution(results)
        
        print(f"\n详细数据已保存到:")
        print(f"  完整数据: {json_path}")
        print(f"  统计汇总: {csv_path}") 
        print(f"  错误分析: {analysis_path}")
        print(f"可使用配套的绘图脚本进行可视化")
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
