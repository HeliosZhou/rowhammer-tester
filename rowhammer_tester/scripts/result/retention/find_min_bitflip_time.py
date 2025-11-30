#!/usr/bin/env python3
"""
Rowhammer位翻转最短时间查找工具
使用二分查找算法找到引起第一次位翻转所需的最短时间

用法示例:
    python find_min_bitflip_time.py
    python find_min_bitflip_time.py --start-time 0.1 --end-time 3.0 --precision 0.00001
    python find_min_bitflip_time.py --max-iterations 20 --pattern all_0
"""

import argparse
import subprocess
import sys
import time
import os
from pathlib import Path

# ============= 配置参数 =============
# 默认测试时间范围 (秒)
DEFAULT_START_TIME = 0.1    # 100ms
DEFAULT_END_TIME = 3.0     # 3s

# 默认精度或最大迭代次数
DEFAULT_PRECISION = 0.00001   # 0.01ms精度
DEFAULT_MAX_ITERATIONS = 25  # 最大迭代次数

# 重复测试配置
DEFAULT_REPEAT_COUNT = 5    # 每个时间点的重复测试次数

# 测试参数
DEFAULT_PATTERN = "all_1"   # 数据模式
DEFAULT_EXTRA_ARGS = ["--no-refresh"]  # 额外的hw_rowhammer.py参数

# 结果保存路径
DEFAULT_RESULT_DIR = "result/retention"  # 默认结果保存目录
# ===================================

def run_bitflip_test(test_time_ns, pattern="all_1", extra_args=None, repeat_count=1):
    """
    执行位翻转测试
    
    Args:
        test_time_ns: 测试时间(纳秒)
        pattern: 数据模式
        extra_args: 额外参数列表
        repeat_count: 重复测试次数
    
    Returns:
        tuple: (是否发现位翻转, 所有测试输出, 位翻转统计)
    """
    if extra_args is None:
        extra_args = []
    
    cmd = [
        "python", "hw_rowhammer.py",
        "--no-attack-time", str(int(test_time_ns)),
        "--pattern", pattern
    ] + extra_args
    
    all_outputs = []
    bitflip_results = []
    
    print(f"    执行 {repeat_count} 次重复测试...")
    
    for repeat in range(repeat_count):
        try:
            if repeat_count > 1:
                print(f"      第 {repeat + 1}/{repeat_count} 次: {' '.join(cmd)}")
            else:
                print(f"    执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=120  # 2分钟超时
            )
            
            output = result.stdout + result.stderr
            has_bitflips = "Bit-flips" in output
            
            # 提取位翻转数量
            bitflip_count = 0
            if has_bitflips:
                for line in output.split('\n'):
                    if "Bit-flips for row" in line:
                        try:
                            # 解析 "Bit-flips for row XXX: N" 格式
                            bitflip_count += int(line.split(':')[-1].strip())
                        except (ValueError, IndexError):
                            pass
            
            all_outputs.append(output)
            bitflip_results.append({
                'has_bitflips': has_bitflips,
                'bitflip_count': bitflip_count,
                'repeat': repeat + 1
            })
            
            if repeat_count > 1:
                status = f"发现 {bitflip_count} 个位翻转" if has_bitflips else "无位翻转"
                print(f"      结果: {status}")
                
        except subprocess.TimeoutExpired:
            print(f"      ⚠️ 第 {repeat + 1} 次测试超时 (>120s)")
            all_outputs.append("测试超时")
            bitflip_results.append({
                'has_bitflips': False,
                'bitflip_count': 0,
                'repeat': repeat + 1
            })
        except Exception as e:
            print(f"      ❌ 第 {repeat + 1} 次执行错误: {e}")
            all_outputs.append(str(e))
            bitflip_results.append({
                'has_bitflips': False,
                'bitflip_count': 0,
                'repeat': repeat + 1
            })
    
    # 分析重复测试结果
    has_any_bitflips = any(r['has_bitflips'] for r in bitflip_results)
    total_bitflips = sum(r['bitflip_count'] for r in bitflip_results)
    success_count = sum(1 for r in bitflip_results if r['has_bitflips'])
    
    return has_any_bitflips, all_outputs, {
        'total_bitflips': total_bitflips,
        'success_count': success_count,
        'total_tests': repeat_count,
        'success_rate': success_count / repeat_count if repeat_count > 0 else 0,
        'details': bitflip_results
    }

def binary_search_min_time(start_time, end_time, precision=None, max_iterations=None, 
                          pattern="all_1", extra_args=None, repeat_count=3):
    """
    二分查找最短位翻转时间
    
    Args:
        start_time: 起始时间(秒)
        end_time: 结束时间(秒) 
        precision: 时间精度(秒)，与max_iterations二选一
        max_iterations: 最大迭代次数，与precision二选一
        pattern: 数据模式
        extra_args: 额外参数
        repeat_count: 每个时间点的重复测试次数
    
    Returns:
        tuple: (最短时间(秒), 测试日志列表)
    """
    if extra_args is None:
        extra_args = []
    
    low_ns = int(start_time * 1e9)  # 转换为纳秒
    high_ns = int(end_time * 1e9)
    best_time_ns = -1
    iteration = 0
    test_log = []
    
    print(f"\n🔍 开始二分查找位翻转最短时间")
    print(f"   时间范围: {start_time:.3f}s - {end_time:.3f}s")
    if precision:
        print(f"   目标精度: {precision:.6f}s")
    if max_iterations:
        print(f"   最大迭代: {max_iterations}次")
    print(f"   重复测试: 每个时间点测试 {repeat_count} 次")
    print(f"   数据模式: {pattern}")
    print(f"   额外参数: {' '.join(extra_args)}")
    print("=" * 70)
    
    while low_ns <= high_ns:
        iteration += 1
        
        # 检查停止条件
        if max_iterations and iteration > max_iterations:
            print(f"\n⏹️ 达到最大迭代次数 ({max_iterations})")
            break
            
        if precision and (high_ns - low_ns) < precision * 1e9:
            print(f"\n⏹️ 达到目标精度 ({precision:.6f}s)")
            break
        
        mid_ns = (low_ns + high_ns) // 2
        mid_sec = mid_ns / 1e9
        
        print(f"\n--- 第 {iteration} 次迭代 ---")
        print(f"测试时间: {mid_sec:.6f}s ({mid_ns}ns)")
        print(f"当前范围: [{low_ns/1e9:.6f}s, {high_ns/1e9:.6f}s]")
        
        has_bitflips, outputs, bitflip_stats = run_bitflip_test(
            mid_ns, pattern, extra_args, repeat_count
        )
        
        log_entry = {
            'iteration': iteration,
            'test_time_ns': mid_ns,
            'test_time_s': mid_sec,
            'has_bitflips': has_bitflips,
            'bitflip_stats': bitflip_stats,
            'range_low_s': low_ns/1e9,
            'range_high_s': high_ns/1e9
        }
        test_log.append(log_entry)
        
        if has_bitflips:
            success_rate = bitflip_stats['success_rate'] * 100
            total_flips = bitflip_stats['total_bitflips']
            print(f"✅ 发现位翻转: {total_flips} 个 (成功率 {success_rate:.1f}%)，缩短时间范围")
            best_time_ns = mid_ns
            high_ns = mid_ns - 1
        else:
            print(f"❌ 未发现位翻转，延长时间范围") 
            low_ns = mid_ns + 1
    
    print("\n" + "=" * 70)
    
    if best_time_ns != -1:
        best_time_s = best_time_ns / 1e9
        print(f"🎯 找到最短位翻转时间: {best_time_s:.6f}s ({best_time_ns}ns)")
        
        # 验证结果
        print(f"\n🔬 验证结果...")
        has_bitflips, _, verify_stats = run_bitflip_test(
            best_time_ns, pattern, extra_args, repeat_count
        )
        if has_bitflips:
            verify_rate = verify_stats['success_rate'] * 100
            print(f"✅ 验证成功: 总计 {verify_stats['total_bitflips']} 个位翻转 (成功率 {verify_rate:.1f}%)")
        else:
            print(f"⚠️ 验证失败: 可能存在随机性，建议增加重复次数")
        
        return best_time_s, test_log
    else:
        print(f"⚠️ 在测试范围 [{start_time:.3f}s, {end_time:.3f}s] 内未找到位翻转")
        return None, test_log

def save_result_summary(min_time, test_params, test_log, result_dir=DEFAULT_RESULT_DIR):
    """保存结果摘要"""
    try:
        result_path = Path(result_dir)
        result_path.mkdir(parents=True, exist_ok=True)
        
        # 生成带时间戳的摘要文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        summary_file = result_path / f"retention_time_result_{timestamp}.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Rowhammer DRAM数据保持时间测试结果\n")
            f.write("=" * 80 + "\n")
            f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("测试参数:\n")
            f.write(f"  起始时间: {test_params['start_time']:.3f}s\n")
            f.write(f"  结束时间: {test_params['end_time']:.3f}s\n")
            f.write(f"  重复次数: {test_params['repeat_count']}次/时间点\n")
            f.write(f"  数据模式: {test_params['pattern']}\n")
            f.write(f"  额外参数: {' '.join(test_params['extra_args'])}\n")
            if test_params.get('precision'):
                f.write(f"  时间精度: {test_params['precision']:.6f}s\n")
            if test_params.get('max_iterations'):
                f.write(f"  最大迭代: {test_params['max_iterations']}次\n")
            f.write(f"  实际迭代: {len(test_log)}次\n\n")
            
            f.write("测试结果:\n")
            if min_time:
                f.write(f"  🎯 最短位翻转时间: {min_time:.6f}s\n")
                f.write(f"     等效纳秒: {min_time*1e9:.0f}ns\n")
                f.write(f"  ✅ 测试状态: 成功找到位翻转临界时间\n")
            else:
                f.write(f"  ⚠️  测试状态: 未在指定范围内发现位翻转\n")
                f.write(f"  💡 建议: 增大测试时间范围或检查硬件配置\n")
            
            f.write(f"\n详细测试过程:\n")
            f.write(f"{'迭代':<4} {'测试时间(s)':<14} {'位翻转':<8} {'成功率':<8} {'总翻转':<8} {'范围下限(s)':<14} {'范围上限(s)':<14}\n")
            f.write("-" * 80 + "\n")
            for entry in test_log:
                stats = entry['bitflip_stats']
                success_rate = f"{stats['success_rate']*100:.1f}%"
                f.write(f"{entry['iteration']:<4} "
                       f"{entry['test_time_s']:<14.6f} "
                       f"{'是' if entry['has_bitflips'] else '否':<8} "
                       f"{success_rate:<8} "
                       f"{stats['total_bitflips']:<8} "
                       f"{entry['range_low_s']:<14.6f} "
                       f"{entry['range_high_s']:<14.6f}\n")
            
            f.write(f"\n重复测试详情:\n")
            f.write(f"{'迭代':<4} {'重复':<4} {'结果':<8} {'位翻转数':<10}\n")
            f.write("-" * 30 + "\n")
            for entry in test_log:
                for detail in entry['bitflip_stats']['details']:
                    result = "成功" if detail['has_bitflips'] else "失败"
                    f.write(f"{entry['iteration']:<4} "
                           f"{detail['repeat']:<4} "
                           f"{result:<8} "
                           f"{detail['bitflip_count']:<10}\n")
        
        print(f"📋 结果摘要已保存到: {summary_file}")
        return str(summary_file)
    except Exception as e:
        print(f"❌ 保存结果摘要失败: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="查找Rowhammer位翻转最短时间",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认参数 (结果保存到 result/retention/)
  python find_min_bitflip_time.py
  
  # 指定时间范围和精度
  python find_min_bitflip_time.py --start-time 0.5 --end-time 5.0 --precision 0.01
  
  # 使用最大迭代次数控制
  python find_min_bitflip_time.py --max-iterations 15 --pattern all_0
  
  # 自定义结果保存目录
  python find_min_bitflip_time.py --result-dir ./my_results
  
  # 添加额外测试参数
  python find_min_bitflip_time.py --extra-args "--bank 1 --column 256"
        """
    )
    
    parser.add_argument('--start-time', type=float, default=DEFAULT_START_TIME,
                       help=f'起始测试时间(秒), 默认: {DEFAULT_START_TIME}')
    parser.add_argument('--end-time', type=float, default=DEFAULT_END_TIME,
                       help=f'结束测试时间(秒), 默认: {DEFAULT_END_TIME}')
    
    precision_group = parser.add_mutually_exclusive_group()
    precision_group.add_argument('--precision', type=float, default=DEFAULT_PRECISION,
                               help=f'时间精度(秒), 默认: {DEFAULT_PRECISION}')
    precision_group.add_argument('--max-iterations', type=int,
                               help=f'最大迭代次数, 默认: {DEFAULT_MAX_ITERATIONS}')
    
    parser.add_argument('--pattern', default=DEFAULT_PATTERN,
                       choices=['all_0', 'all_1', '01_in_row', '01_per_row', 'rand_per_row'],
                       help=f'数据模式, 默认: {DEFAULT_PATTERN}')
    parser.add_argument('--repeat-count', type=int, default=DEFAULT_REPEAT_COUNT,
                       help=f'每个时间点的重复测试次数, 默认: {DEFAULT_REPEAT_COUNT}')
    parser.add_argument('--extra-args', default=' '.join(DEFAULT_EXTRA_ARGS),
                       help=f'额外的hw_rowhammer.py参数, 默认: "{" ".join(DEFAULT_EXTRA_ARGS)}"')
    parser.add_argument('--result-dir', default=DEFAULT_RESULT_DIR,
                       help=f'结果保存目录, 默认: {DEFAULT_RESULT_DIR}')
    parser.add_argument('--no-save', action='store_true',
                       help='不保存结果文件')
    
    args = parser.parse_args()
    
    # 验证参数
    if args.start_time <= 0 or args.end_time <= 0:
        print("❌ 错误: 时间必须大于0")
        sys.exit(1)
        
    if args.start_time >= args.end_time:
        print("❌ 错误: 起始时间必须小于结束时间")
        sys.exit(1)
    
    if args.repeat_count <= 0:
        print("❌ 错误: 重复次数必须大于0")
        sys.exit(1)
    
    # 解析额外参数
    extra_args = args.extra_args.split() if args.extra_args.strip() else []
    
    # 确定停止条件
    precision = args.precision if not args.max_iterations else None
    max_iterations = args.max_iterations if args.max_iterations else DEFAULT_MAX_ITERATIONS
    
    print("🚀 Rowhammer位翻转最短时间查找工具")
    print("=" * 70)
    
    # 执行二分查找
    try:
        min_time, test_log = binary_search_min_time(
            args.start_time, args.end_time, precision, max_iterations,
            args.pattern, extra_args, args.repeat_count
        )
        
        # 准备测试参数用于保存结果
        test_params = {
            'start_time': args.start_time,
            'end_time': args.end_time,
            'pattern': args.pattern,
            'extra_args': extra_args,
            'precision': precision,
            'max_iterations': max_iterations,
            'repeat_count': args.repeat_count
        }
        
        # 保存结果
        summary_path = None
        if not args.no_save and test_log:
            summary_path = save_result_summary(min_time, test_params, test_log, args.result_dir)
        
        # 输出结果摘要
        print(f"\n📊 测试摘要:")
        print(f"   总迭代次数: {len(test_log)}")
        print(f"   时间范围: {args.start_time:.3f}s - {args.end_time:.3f}s")
        print(f"   数据模式: {args.pattern}")
        
        if min_time:
            print(f"   🎯 最短位翻转时间: {min_time:.6f}s")
            if not args.no_log:
                if log_path:
                    print(f"   📄 详细日志: {log_path}")
                if summary_path:
                    print(f"   � 结果摘要: {summary_path}")
            print(f"\n✅ 测试完成！最短位翻转时间为 {min_time:.6f} 秒")
        else:
            print(f"   ⚠️ 未在指定范围内找到位翻转")
            print(f"\n💡 建议: 尝试增大结束时间或检查硬件配置")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ 用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
