#!/usr/bin/env python3
"""
测试bit翻转数量随开启时间变化的脚本
使用 hw_rowhammer.py --no-attack-time <time> --no-refresh --pattern all_1 命令
"""

import os
import sys
import json
import time
import numpy as np
import subprocess
from pathlib import Path
from datetime import datetime

# 测试参数配置
START_TIME = 0.1      # 起始时间（秒）
END_TIME = 20.0       # 终止时间（秒）
NUM_POINTS = 15       # 测试点数
NUM_REPEATS = 5       # 每个时间点重复测试次数

def generate_time_points(start, end, num_points):
    """生成均匀分布的时间点"""
    return np.linspace(start, end, num_points)

def run_rowhammer_test(attack_time_sec):
    """
    运行单次rowhammer测试
    
    Args:
        attack_time_sec: 攻击时间（秒）
        
    Returns:
        tuple: (总bit翻转数量, 错误详情)
    """
    # 将秒转换为纳秒
    attack_time_ns = int(attack_time_sec * 1e9)
    
    # 构建命令
    cmd = [
        'python3', 'hw_rowhammer.py',
        '--no-attack-time', str(attack_time_ns),
        '--no-refresh',
        '--pattern', 'all_1',
        '--nrows', '512',
        '--verbose'
    ]
    
    print(f"运行命令: {' '.join(cmd)}")
    
    try:
        # 运行命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode != 0:
            print(f"命令执行失败，返回码: {result.returncode}")
            print(f"错误输出: {result.stderr}")
            return 0, {}
        
        # 解析输出中的bit翻转信息
        output_lines = result.stdout.split('\n')
        total_bitflips = 0
        error_details = {}
        
        for line in output_lines:
            if 'Bit-flips for row' in line:
                # 解析类似 "Bit-flips for row   123: 45" 的行
                parts = line.split(':')
                if len(parts) == 2:
                    try:
                        bitflips = int(parts[1].strip())
                        total_bitflips += bitflips
                        row_info = parts[0].strip()
                        row_num = int(row_info.split()[-1])
                        error_details[row_num] = bitflips
                    except ValueError:
                        continue
        
        print(f"检测到 {total_bitflips} 个bit翻转")
        return total_bitflips, error_details
        
    except subprocess.TimeoutExpired:
        print(f"测试超时 (attack_time: {attack_time_sec}s)")
        return 0, {}
    except Exception as e:
        print(f"运行测试时发生错误: {e}")
        return 0, {}

def run_time_series_test():
    """运行完整的时间序列测试"""
    
    # 生成时间点
    time_points = generate_time_points(START_TIME, END_TIME, NUM_POINTS)
    
    # 结果存储
    test_results = {
        'metadata': {
            'start_time': START_TIME,
            'end_time': END_TIME,
            'num_points': NUM_POINTS,
            'num_repeats': NUM_REPEATS,
            'test_timestamp': datetime.now().isoformat(),
            'time_points': time_points.tolist()
        },
        'raw_data': {},
        'statistics': {}
    }
    
    print(f"开始时间序列测试")
    print(f"时间范围: {START_TIME}s - {END_TIME}s")
    print(f"测试点数: {NUM_POINTS}")
    print(f"重复次数: {NUM_REPEATS}")
    print(f"时间点: {time_points}")
    print("=" * 60)
    
    # 对每个时间点进行测试
    for i, attack_time in enumerate(time_points):
        print(f"\n[{i+1}/{NUM_POINTS}] 测试时间点: {attack_time:.2f}s")
        
        # 存储该时间点的所有重复测试结果
        repeat_results = []
        repeat_details = []
        
        # 重复测试
        for repeat in range(NUM_REPEATS):
            print(f"  重复 {repeat+1}/{NUM_REPEATS}...")
            
            bitflips, details = run_rowhammer_test(attack_time)
            repeat_results.append(bitflips)
            repeat_details.append(details)
            
            print(f"  结果: {bitflips} bit翻转")
            
            # 短暂延时避免硬件过热
            time.sleep(2)
        
        # 计算统计数据
        mean_bitflips = np.mean(repeat_results)
        std_bitflips = np.std(repeat_results)
        min_bitflips = np.min(repeat_results)
        max_bitflips = np.max(repeat_results)
        
        # 存储结果
        test_results['raw_data'][f'{attack_time:.2f}'] = {
            'attack_time': attack_time,
            'repeat_results': repeat_results,
            'repeat_details': repeat_details
        }
        
        test_results['statistics'][f'{attack_time:.2f}'] = {
            'attack_time': attack_time,
            'mean': mean_bitflips,
            'std': std_bitflips,
            'min': min_bitflips,
            'max': max_bitflips
        }
        
        print(f"  统计结果: 平均={mean_bitflips:.2f}, 标准差={std_bitflips:.2f}, 范围=[{min_bitflips}, {max_bitflips}]")
    
    return test_results

def save_results(results):
    """保存测试结果到文件"""
    
    # 确保输出目录存在
    output_dir = Path(__file__).parent.parent / 'result' / 'retention'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bitflip_time_test_{timestamp}.json"
    filepath = output_dir / filename
    
    # 保存JSON数据
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 同时保存简化的CSV格式数据
    csv_filename = f"bitflip_time_test_{timestamp}.csv"
    csv_filepath = output_dir / csv_filename
    
    with open(csv_filepath, 'w', encoding='utf-8') as f:
        f.write("attack_time,mean_bitflips,std_bitflips,min_bitflips,max_bitflips,raw_data\n")
        
        for time_key, stats in results['statistics'].items():
            attack_time = stats['attack_time']
            mean = stats['mean']
            std = stats['std']
            min_val = stats['min']
            max_val = stats['max']
            raw_data = results['raw_data'][time_key]['repeat_results']
            raw_str = ';'.join(map(str, raw_data))
            
            f.write(f"{attack_time},{mean},{std},{min_val},{max_val},\"{raw_str}\"\n")
    
    print(f"\n结果已保存到:")
    print(f"  JSON详细数据: {filepath}")
    print(f"  CSV简化数据: {csv_filepath}")
    
    return filepath, csv_filepath

def main():
    """主函数"""
    print("=" * 60)
    print("Bit翻转随时间变化测试脚本")
    print("=" * 60)
    
    # 检查是否在正确的目录
    if not os.path.exists('hw_rowhammer.py'):
        print("错误: 找不到 hw_rowhammer.py 文件")
        print("请确保在 rowhammer_tester/scripts 目录下运行此脚本")
        sys.exit(1)
    
    try:
        # 运行测试
        results = run_time_series_test()
        
        # 保存结果
        json_path, csv_path = save_results(results)
        
        # 显示测试摘要
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        print(f"测试时间范围: {START_TIME}s - {END_TIME}s")
        print(f"测试点数: {NUM_POINTS}")
        print(f"重复次数: {NUM_REPEATS}")
        
        print("\n测试结果摘要:")
        for time_key, stats in results['statistics'].items():
            print(f"  {stats['attack_time']:6.2f}s: 平均 {stats['mean']:6.1f} ± {stats['std']:5.1f} bit翻转")
        
        print(f"\n详细数据已保存到: {json_path}")
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
