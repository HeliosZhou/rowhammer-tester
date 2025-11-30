#!/usr/bin/env python3
"""
HCfirst测试脚本 - 简化版
测试0-8192行的第一个bit翻转需要的最小锤击数

使用方法:
  python test_hcfirst_simple.py                    # 测试所有8192行
  python test_hcfirst_simple.py --test             # 测试模式：只测试3行(180-182)
  python test_hcfirst_simple.py --start 100 --count 50  # 自定义起始行和数量
  python test_hcfirst_simple.py --start 0 --count 127
  python test_hcfirst_simple.py --start 4032 --count 4159
  python test_hcfirst_simple.py --start 8064 --count 8191
  10分钟: 约13-15行
  30分钟: 约40-45行
  1小时: 约80-90行
  2小时: 约160-180行
  半天(12小时): 约960-1080行
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import glob
import shutil
import argparse
from datetime import datetime

# ===== 可自定义配置参数 =====
INITIAL_READ_COUNT = 25000        # 起始read_count值 (可自定义)
# 已移除验证功能，找到bit翻转即确定HCfirst

# ===== 其他配置参数 =====
MIN_READ_COUNT = 1000            # 最小read_count值
MAX_READ_COUNT = 10000000        # 最大read_count值

# 结果保存目录
RESULTS_DIR = "/home/hc/rowhammer-tester/rowhammer_tester/scripts/result/HCfirst"
SCRIPT_DIR = "/home/hc/rowhammer-tester/rowhammer_tester/scripts"
PYTHON_PATH = "/home/hc/rowhammer-tester-ZCU104/.venv/bin/python"  # 虚拟环境Python路径

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='HCfirst测试脚本')
    parser.add_argument('--test', action='store_true', 
                       help='测试模式：只测试3行(180-182)用于调试')
    parser.add_argument('--start', type=int, default=0,
                       help='起始行号 (默认: 0)')
    parser.add_argument('--count', type=int, default=8192,
                       help='测试行数 (默认: 8192)')
    return parser.parse_args()

# 全局变量，在main函数中设置
START_ROW = 0
TOTAL_ROWS = 8192

class SimpleHCFirstTester:
    def __init__(self):
        self.results = {}
        self.tested_count = 0
        self.success_count = 0
        
        # 创建结果目录
        os.makedirs(RESULTS_DIR, exist_ok=True)
        
        # 创建临时目录用于log文件
        self.temp_log_dir = tempfile.mkdtemp(prefix="hcfirst_logs_")
        
        # 生成结果文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.result_file = os.path.join(RESULTS_DIR, f"HCfirst_all_rows_0-8191_{timestamp}.json")
        
        print(f"HCfirst测试开始")
        print(f"测试范围: 行 0-8191 ({TOTAL_ROWS}行)")
        print(f"初始read_count: {INITIAL_READ_COUNT:,}")
        print(f"不进行验证，找到bit翻转即确定HCfirst")
        print(f"临时日志目录: {self.temp_log_dir}")
        print(f"结果文件: {self.result_file}")
        print("=" * 60)

    def run_test(self, row, read_count):
        """运行单次测试并返回详细结果"""
        # 清理之前的临时文件
        self.cleanup_temp_files()
        
        cmd = [
            PYTHON_PATH, "hw_rowhammer.py",
            "--row-pairs", "const",
            "--const-rows-pair", str(row), str(row),
            "--read_count", str(int(read_count)),
            "--pattern", "all_1",
            "--no-refresh",
            "--payload-executor",
            "--log-dir", self.temp_log_dir  # 使用临时目录
        ]
        
        try:
            result = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 检查是否有bit翻转
                lines = result.stdout.strip().split('\n')
                
                # 查找Progress行中的错误计数 - 需要找最后一个Progress行
                error_count = 0
                for line in lines:
                    if "progress:" in line.lower() and "errors:" in line.lower():
                        # 提取错误数量
                        import re
                        error_match = re.search(r'errors:\s*(\d+)', line.lower())
                        if error_match:
                            error_count = int(error_match.group(1))
                            # 不要break，继续找下一个，这样找到的是最后一个
                
                # 如果有错误，读取详细的JSON日志
                detailed_errors = None
                if error_count > 0:
                    detailed_errors = self.get_detailed_errors(row, read_count)
                
                return {
                    'has_bitflips': error_count > 0,
                    'error_count': error_count,
                    'detailed_errors': detailed_errors
                }
            else:
                print(f"      测试失败: {result.stderr.strip()}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"      测试超时")
            return None
        except Exception as e:
            print(f"      异常: {str(e)}")
            return None

    def get_detailed_errors(self, row, read_count):
        """从log目录中获取详细的错误信息"""
        try:
            # 查找最新的error_summary文件
            pattern = os.path.join(self.temp_log_dir, "error_summary_*.json")
            log_files = glob.glob(pattern)
            
            if not log_files:
                return None
                
            # 获取最新的文件
            latest_file = max(log_files, key=os.path.getmtime)
            
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            # 查找对应read_count的数据
            read_count_key = str(read_count)
            if read_count_key in data:
                pair_key = f"pair_{row}_{row}"
                if pair_key in data[read_count_key]:
                    return data[read_count_key][pair_key].get('errors_in_rows', {})
            
            return None
        except Exception as e:
            print(f"      读取详细错误失败: {e}")
            return None

    def cleanup_temp_files(self):
        """清理临时日志文件"""
        try:
            pattern = os.path.join(self.temp_log_dir, "error_summary_*.json")
            for file_path in glob.glob(pattern):
                os.remove(file_path)
        except Exception as e:
            print(f"      清理临时文件失败: {e}")

    def parse_hw_rowhammer_output(self, output, hammer_row, read_count):
        """解析hw_rowhammer.py的输出，提取详细的bit翻转信息"""
        import os
        import glob
        
        lines = output.strip().split('\n')
        
        # 查找最后一个Progress行的错误计数
        error_count = 0
        for line in lines:
            if "progress:" in line.lower() and "errors:" in line.lower():
                import re
                error_match = re.search(r'errors:\s*(\d+)', line.lower())
                if error_match:
                    error_count = int(error_match.group(1))
        
        if error_count == 0:
            return {'has_bitflips': False}
        
        # 尝试读取生成的JSON文件获取详细信息
        errors_in_rows = {}
        
        # 查找最新生成的error_summary文件
        json_files = glob.glob("/tmp/error_summary_*.json")
        if json_files:
            # 选择最新的文件
            latest_file = max(json_files, key=os.path.getmtime)
            try:
                with open(latest_file, 'r') as f:
                    json_data = json.load(f)
                    
                # 提取错误信息
                if str(read_count) in json_data:
                    pair_key = f"pair_{hammer_row}_{hammer_row}"
                    if pair_key in json_data[str(read_count)]:
                        pair_data = json_data[str(read_count)][pair_key]
                        if "errors_in_rows" in pair_data:
                            errors_in_rows = pair_data["errors_in_rows"]
                
                # 删除临时文件
                os.remove(latest_file)
                
            except Exception as e:
                print(f"      读取JSON文件失败: {e}")
        
        # 如果没有从JSON文件获取到详细信息，从标准输出解析基本信息
        if not errors_in_rows:
            for line in lines:
                # 查找"Bit-flips for row XXX: YYY"行
                import re
                row_match = re.match(r'Bit-flips for row\s+(\d+):\s+(\d+)', line.strip())
                if row_match:
                    victim_row = int(row_match.group(1))
                    bitflip_count = int(row_match.group(2))
                    
                    errors_in_rows[victim_row] = {
                        "bank": 0,
                        "row": victim_row,
                        "col": {
                            "0": list(range(bitflip_count))  # 简化的bit位置
                        },
                        "bitflips": bitflip_count
                    }
        
        return {
            'has_bitflips': True,
            'error_count': error_count,
            'errors_in_rows': errors_in_rows
        }

    def find_hcfirst(self, row):
        """为指定行找到HCfirst值"""
        print(f"\n[{self.tested_count+1:4d}/{TOTAL_ROWS}] 测试行 {row:5d}")
        
        # 确定起始read_count
        if self.success_count > 0:
            # 使用最近成功结果的read_count作为起始点
            recent_successes = []
            for read_count_data in list(self.results.values())[-10:]:
                if 'read_count' in read_count_data:
                    recent_successes.append(read_count_data['read_count'])
            
            if recent_successes:
                start_count = int(sum(recent_successes) / len(recent_successes))
                print(f"  使用最近平均值作为起始: {start_count:,}")
            else:
                start_count = INITIAL_READ_COUNT
        else:
            start_count = INITIAL_READ_COUNT
            
        # 二分查找HCfirst
        low, high = MIN_READ_COUNT, MAX_READ_COUNT
        found_hcfirst = None
        
        # 首先测试起始值
        print(f"  测试起始值: {start_count:,}")
        result = self.run_test(row, start_count)
        
        if result is None:
            return None, None  # 测试失败
        elif result['has_bitflips']:
            # 有bit翻转，向下搜索
            high = start_count
            print(f"    ✓ 有bit翻转，向下搜索")
            last_successful_result = result
        else:
            # 没有bit翻转，需要向上搜索
            # 如果起始值不是INITIAL_READ_COUNT，先尝试INITIAL_READ_COUNT
            if start_count != INITIAL_READ_COUNT:
                print(f"    ✗ 无bit翻转，尝试默认值 {INITIAL_READ_COUNT:,}")
                result = self.run_test(row, INITIAL_READ_COUNT)
                
                if result is None:
                    return None, None  # 测试失败
                elif result['has_bitflips']:
                    # 使用INITIAL_READ_COUNT作为新的起始点，向下搜索
                    high = INITIAL_READ_COUNT
                    print(f"    ✓ 默认值有bit翻转，向下搜索")
                    last_successful_result = result
                else:
                    # 连INITIAL_READ_COUNT都没有翻转，向上搜索
                    low = INITIAL_READ_COUNT
                    high = min(INITIAL_READ_COUNT * 10, MAX_READ_COUNT)
                    print(f"    ✗ 默认值也无bit翻转，向上搜索 (最大到 {high:,})")
                    last_successful_result = None
            else:
                # 起始值就是INITIAL_READ_COUNT，直接向上搜索
                low = start_count
                high = min(start_count * 10, MAX_READ_COUNT)
                print(f"    ✗ 无bit翻转，向上搜索 (最大到 {high:,})")
                last_successful_result = None
        
        # 二分查找
        iteration = 0
        found_hcfirst = None
        found_result = None
        
        while low <= high and iteration < 15:  # 最多15次迭代
            iteration += 1
            mid = (low + high) // 2
            
            print(f"  [{iteration:2d}] 测试 {mid:,}")
            result = self.run_test(row, mid)
            
            if result is None:
                break  # 测试失败
            elif result['has_bitflips']:
                # 有bit翻转
                found_hcfirst = mid
                found_result = result
                high = mid - 1
                print(f"      ✓ 有翻转，HCfirst <= {mid:,}")
            else:
                # 没有bit翻转
                low = mid + 1
                print(f"      ✗ 无翻转，HCfirst > {mid:,}")
        
        # 如果没有找到，但初始测试有bit翻转，使用初始结果
        if found_hcfirst is None and last_successful_result is not None:
            found_hcfirst = start_count
            found_result = last_successful_result
        
        return found_hcfirst, found_result

    def test_row(self, row):
        """测试单行 - 无验证版本"""
        start_time = time.time()
        
        # 查找HCfirst
        hcfirst, detailed_result = self.find_hcfirst(row)
        
        if hcfirst is None:
            print(f"  结果: 失败 - 无法找到HCfirst")
        else:
            print(f"  结果: HCfirst = {hcfirst:,}")
            self.success_count += 1
            
            # 按新格式保存结果 - 匹配提供的JSON格式
            read_count_key = str(hcfirst)
            pair_key = f"pair_{row}_{row}"
            
            if read_count_key not in self.results:
                self.results[read_count_key] = {
                    "read_count": hcfirst
                }
            
            # 创建pair数据
            pair_data = {
                "hammer_row_1": row,
                "hammer_row_2": row
            }
            
            # 如果有详细的bit翻转信息，添加到结果中
            if detailed_result and 'detailed_errors' in detailed_result and detailed_result['detailed_errors']:
                pair_data["errors_in_rows"] = detailed_result['detailed_errors']
            else:
                # 如果没有详细信息，创建空的errors_in_rows
                pair_data["errors_in_rows"] = {}
            
            self.results[read_count_key][pair_key] = pair_data
        
        self.tested_count += 1
        elapsed_time = time.time() - start_time
        print(f"  用时: {elapsed_time:.1f}s, 成功率: {self.success_count}/{self.tested_count}")
        
        # 每10行保存一次结果
        if self.tested_count % 10 == 0:
            self.save_results()

    def save_results(self):
        """保存结果 - 新JSON格式"""
        with open(self.result_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)

    def run_all_tests(self):
        """运行所有测试"""
        start_time = time.time()
        
        try:
            for row in range(START_ROW, START_ROW + TOTAL_ROWS):
                self.test_row(row)
                
                # 每100行显示进度
                if (row + 1) % 100 == 0:
                    elapsed = time.time() - start_time
                    estimated_total = elapsed * TOTAL_ROWS / (row + 1)
                    remaining = estimated_total - elapsed
                    print(f"\n>>> 进度: {row+1}/{TOTAL_ROWS} ({(row+1)*100/TOTAL_ROWS:.1f}%)")
                    print(f"    已用: {elapsed/3600:.1f}h, 预计剩余: {remaining/3600:.1f}h\n")
                
        except KeyboardInterrupt:
            print(f"\n>>> 用户中断")
        except Exception as e:
            print(f"\n>>> 异常: {e}")
        finally:
            self.save_results()
            self.print_summary(time.time() - start_time)
            # 清理临时目录
            if os.path.exists(self.temp_log_dir):
                shutil.rmtree(self.temp_log_dir)
                print(f"已清理临时目录: {self.temp_log_dir}")

    def print_summary(self, total_time):
        """打印测试总结"""
        print(f"\n" + "="*60)
        print(f"测试完成!")
        print(f"总用时: {total_time/3600:.2f}小时")
        print(f"成功测试: {self.success_count}/{self.tested_count} ({self.success_count/max(1,self.tested_count)*100:.1f}%)")
        
        if self.success_count > 0:
            # 提取所有HCfirst值
            all_hcfirst = []
            for read_count_data in self.results.values():
                for key, pair_data in read_count_data.items():
                    if key.startswith('pair_') and isinstance(pair_data, dict) and 'hcfirst' in pair_data:
                        all_hcfirst.append(pair_data['hcfirst'])
            
            if all_hcfirst:
                print(f"HCfirst统计:")
                print(f"  最小值: {min(all_hcfirst):,}")
                print(f"  最大值: {max(all_hcfirst):,}")
                print(f"  平均值: {sum(all_hcfirst)/len(all_hcfirst):,.0f}")
        
        print(f"结果已保存: {self.result_file}")


def main():
    global START_ROW, TOTAL_ROWS
    
    # 解析命令行参数
    args = parse_args()
    
    # 设置测试范围
    if args.test:
        START_ROW = 180
        TOTAL_ROWS = 3
        print("=== 测试模式：测试3行(180-182) ===")
    else:
        START_ROW = args.start
        TOTAL_ROWS = args.count
        print(f"=== 正常模式：测试{TOTAL_ROWS}行(从第{START_ROW}行开始) ===")
    
    if not os.path.exists(SCRIPT_DIR):
        print(f"错误: 目录不存在 {SCRIPT_DIR}")
        return
        
    if not os.path.exists(os.path.join(SCRIPT_DIR, "hw_rowhammer.py")):
        print(f"错误: hw_rowhammer.py 不存在")
        return
    
    tester = SimpleHCFirstTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
