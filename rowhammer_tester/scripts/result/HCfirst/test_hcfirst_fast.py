#!/usr/bin/env python3
"""
HCfirst快速测试脚本 - 性能优化版本
专注于快速获取HCfirst值，不记录详细错误信息

特点：
- 使用指数搜索+二分搜索算法提高效率
- 简化JSON输出格式
- 减少日志记录以提高性能
- 适用于大批量测试
"""

import os
import sys
import subprocess
import json
import argparse
import tempfile
import shutil
from datetime import datetime

# 添加脚本路径以便导入hw_rowhammer
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='HCfirst快速测试工具')
    parser.add_argument('--start', type=int, default=0, help='起始行号 (默认: 0)')
    parser.add_argument('--count', type=int, default=100, help='测试行数 (默认: 100)')
    parser.add_argument('--max-hc', type=int, default=30000, help='最大hammer count (默认: 30000)')
    parser.add_argument('--min-hc', type=int, default=1000, help='最小hammer count (默认: 1000)')
    parser.add_argument('--timeout', type=int, default=30, help='单次测试超时时间(秒) (默认: 30)')
    parser.add_argument('--output', type=str, help='输出文件名 (默认: 自动生成)')
    parser.add_argument('--test', action='store_true', help='测试模式：只处理前3行')
    return parser.parse_args()

class HCFirstFastTester:
    def __init__(self, min_hc=1000, max_hc=50000, timeout=30):
        self.min_hc = min_hc
        self.max_hc = max_hc
        self.timeout = timeout
        self.python_path = None
        self.find_python()
        
    def find_python(self):
        """查找Python可执行文件路径"""
        # 检查是否在虚拟环境中
        venv_paths = [
            "/home/hc/rowhammer-tester-ZCU104/.venv/bin/python",
            "/home/hc/rowhammer-tester/.venv/bin/python",
            "python3",
            "python"
        ]
        
        for path in venv_paths:
            try:
                result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.python_path = path
                    print(f"使用Python: {path}")
                    if "3.10" in result.stdout:
                        print(f"Python版本: {result.stdout.strip()}")
                    return
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        print("错误: 未找到可用的Python解释器")
        sys.exit(1)
    
    def run_hw_rowhammer(self, row, read_count):
        """运行hw_rowhammer.py测试"""
        cmd = [
            self.python_path, "hw_rowhammer.py",
            "--row-pairs", "const",
            "--const-rows-pair", str(row), str(row),
            "--read_count", str(read_count),
            "--no-refresh",
            "--nrows", "8192",
            "--payload-executor"
        ]
        
        # hw_rowhammer.py 在 scripts 目录中
        scripts_path = "/home/hc/rowhammer-tester/rowhammer_tester/scripts"
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, cwd=scripts_path)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"测试超时 (>{self.timeout}s)"
        except Exception as e:
            return False, "", str(e)
    
    def has_bitflips(self, stdout, stderr):
        """检查是否有bit flip（改进版本）"""
        # 检查输出中的错误计数
        lines = stdout.strip().split('\n')
        
        # 查找Progress行中的错误计数 - 找最后一个Progress行
        error_count = 0
        for line in lines:
            if "progress:" in line.lower() and "errors:" in line.lower():
                # 提取错误数量
                import re
                error_match = re.search(r'errors:\s*(\d+)', line.lower())
                if error_match:
                    error_count = int(error_match.group(1))
                    # 不要break，继续找下一个，这样找到的是最后一个
        
        # 也检查是否有"Bit-flips for row"这样的输出
        bitflip_detected = any("bit-flips for row" in line.lower() for line in lines)
        
        return error_count > 0 or bitflip_detected
    
    def exponential_search(self, row):
        """指数搜索找到大致范围"""
        print(f"行 {row}: 开始指数搜索...")
        
        # 从最小值开始，指数增长
        current = self.min_hc
        while current <= self.max_hc:
            print(f"  测试 HC={current:,}")
            success, stdout, stderr = self.run_hw_rowhammer(row, current)
            
            if not success:
                print(f"    测试失败: {stderr}")
                current *= 2
                continue
            
            if self.has_bitflips(stdout, stderr):
                print(f"    发现bit flip! 范围: {current//2} - {current}")
                # 返回搜索范围
                return max(current // 2, self.min_hc), current
            
            current *= 2
        
        print(f"  未在最大范围 {self.max_hc:,} 内找到bit flip")
        return None, None
    
    def binary_search(self, row, low, high):
        """二分搜索精确值"""
        print(f"行 {row}: 二分搜索 {low:,} - {high:,}")
        
        last_no_flip = low
        first_flip = high
        
        while low <= high:
            mid = (low + high) // 2
            print(f"  测试 HC={mid:,}")
            
            success, stdout, stderr = self.run_hw_rowhammer(row, mid)
            
            if not success:
                print(f"    测试失败: {stderr}")
                low = mid + 1
                continue
            
            if self.has_bitflips(stdout, stderr):
                print(f"    有bit flip")
                first_flip = mid
                high = mid - 1
            else:
                print(f"    无bit flip")
                last_no_flip = mid
                low = mid + 1
        
        return first_flip if first_flip != high else None
    
    def find_hcfirst(self, row):
        """查找单行的HCfirst"""
        print(f"\n=== 测试行 {row} ===")
        
        # 1. 指数搜索确定范围
        low, high = self.exponential_search(row)
        if low is None:
            print(f"行 {row}: 未找到HCfirst")
            return None
        
        # 2. 二分搜索精确值
        hcfirst = self.binary_search(row, low, high)
        
        if hcfirst:
            print(f"行 {row}: HCfirst = {hcfirst:,}")
        else:
            print(f"行 {row}: 二分搜索失败")
            
        return hcfirst
    
    def test_rows(self, start_row, count, test_mode=False):
        """测试多行"""
        if test_mode:
            count = min(count, 3)
            print(f"测试模式：只测试前 {count} 行")
        
        results = {}
        failed_rows = []
        
        total_rows = count
        for i in range(count):
            row = start_row + i
            progress = f"[{i+1}/{total_rows}]"
            print(f"\n{progress} 开始测试行 {row}")
            
            hcfirst = self.find_hcfirst(row)
            if hcfirst is not None:
                results[row] = hcfirst
                print(f"{progress} 行 {row} 完成: HCfirst = {hcfirst:,}")
            else:
                failed_rows.append(row)
                print(f"{progress} 行 {row} 失败")
        
        return results, failed_rows

def main():
    args = parse_args()
    
    # 创建测试器
    tester = HCFirstFastTester(
        min_hc=args.min_hc,
        max_hc=args.max_hc,
        timeout=args.timeout
    )
    
    print("HCfirst快速测试工具")
    print(f"测试范围: 行 {args.start} - {args.start + args.count - 1}")
    print(f"HammerCount范围: {args.min_hc:,} - {args.max_hc:,}")
    print(f"超时时间: {args.timeout}s")
    if args.test:
        print("*** 测试模式 ***")
    print()
    
    # 开始测试
    start_time = datetime.now()
    results, failed_rows = tester.test_rows(args.start, args.count, args.test)
    end_time = datetime.now()
    
    # 统计结果
    success_count = len(results)
    total_count = args.count if not args.test else min(args.count, 3)
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n" + "="*50)
    print("测试完成!")
    print(f"成功: {success_count}/{total_count}")
    print(f"用时: {duration:.1f}秒")
    if results:
        hcfirst_values = list(results.values())
        print(f"HCfirst范围: {min(hcfirst_values):,} - {max(hcfirst_values):,}")
        print(f"平均值: {sum(hcfirst_values)/len(hcfirst_values):,.0f}")
    
    if failed_rows:
        print(f"失败行: {failed_rows}")
    
    # 保存结果
    if results:
        if args.output:
            output_file = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode_suffix = "_test" if args.test else ""
            output_file = f"HCfirst_fast_{args.start}-{args.start+total_count-1}_{timestamp}{mode_suffix}.json"
        
        # 简化的JSON格式
        output_data = {
            "metadata": {
                "type": "HCfirst_fast",
                "timestamp": datetime.now().isoformat(),
                "range": f"{args.start}-{args.start+total_count-1}",
                "success_count": success_count,
                "total_count": total_count,
                "duration_seconds": round(duration, 1),
                "parameters": {
                    "min_hc": args.min_hc,
                    "max_hc": args.max_hc,
                    "timeout": args.timeout
                }
            },
            "results": results
        }
        
        if failed_rows:
            output_data["failed_rows"] = failed_rows
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n结果已保存: {output_file}")
            file_size = os.path.getsize(output_file)
            print(f"文件大小: {file_size} 字节")
            
        except Exception as e:
            print(f"\n保存失败: {str(e)}")
            return 1
    else:
        print("\n没有成功的测试结果，未生成文件。")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
