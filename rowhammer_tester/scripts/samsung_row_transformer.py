#!/usr/bin/env python3
"""
Samsung芯片特殊地址映射变换器

基于图片中显示的三星芯片地址映射规律：
- 每16行为1组
- 行1-6保持不变
- 行7-16按照特定的变换规则进行变换

变换规则分析：
- 若n是奇数(在7..16内): 7,9,11,13,15，映射是向前加4(模10)
- 若n是偶数(8,10,12,14,16)，映射是向前加6(模10)，等价于向后减4

公式: f(n) = 7 + ((n-7) + Δ(n)) mod 10
其中: Δ(n) = {4, n为奇数; 6, n为偶数}

并且f(1) = 1, ..., f(6) = 6

python samsung_row_transformer.py result/a-hammer/a-hammer_single_side_r0-1000_rc40K.json
"""

import json
import random
from collections import defaultdict


class SamsungRowTransformer:
    """三星芯片行地址变换器"""
    
    def __init__(self):
        """初始化变换器"""
        pass
    
    def transform_victim_row(self, row):
        """
        对受害者行进行地址变换（物理地址→逻辑地址）
        
        基于图片分析的三星芯片地址映射规律的反向映射:
        - 每16行为一组  
        - 行1-6保持不变
        - 行7-16按照下面的反向映射表变换:
        
        从图片可以看出正向映射：
        奇位列 A = [7,9,11,13,15], 循环: 7→11→15→9→13→7
        偶位列 B = [8,10,12,14,16], 循环: 8→14→10→16→12→8
        
        我们需要反向映射（物理→逻辑）:
        奇位列反向: 11→7, 15→11, 9→15, 13→9, 7→13
        偶位列反向: 14→8, 10→14, 16→10, 12→16, 8→12
        
        Args:
            row: 物理行号
            
        Returns:
            transformed_row: 逻辑行号
        """
        # 处理边界情况：行号为0或负数时保持不变
        if row <= 0:
            return row
            
        # 计算在16行组内的位置
        group_offset = row % 16
        group_base = row - group_offset
        
        # 行1-6不变 (group_offset 1-6)  
        if 1 <= group_offset <= 6:
            return row
        
        # 行7-16按特殊规则变换 (group_offset 7-15, 0代表16)  
        if group_offset == 0:  # 第16行对应group_offset=0
            # 根据偶数序列反向循环: 16→10，所以16→10
            return (row - 16) + 10  # 将第16行映射到同组的第10行
            
        if 7 <= group_offset <= 15:
            # 基于图片分析的精确映射 - 反向映射（物理→逻辑）
            # 分别处理奇数位置和偶数位置的循环映射
            if group_offset in [7, 9, 11, 13, 15]:  # 奇数序列
                # 奇位列反向循环: 11→7, 15→11, 9→15, 13→9, 7→13
                odd_reverse_mapping = {11: 7, 15: 11, 9: 15, 13: 9, 7: 13}
                transformed_offset = odd_reverse_mapping[group_offset]
            else:  # [8, 10, 12, 14] 偶数序列
                # 偶位列反向循环: 14→8, 10→14, 16→10, 12→16, 8→12  
                even_reverse_mapping = {14: 8, 10: 14, 16: 10, 12: 16, 8: 12}
                transformed_offset = even_reverse_mapping[group_offset]
                
            return group_base + transformed_offset
            
        return row  # 默认不变换
    
    def transform_result_data(self, result_data):
        """
        变换结果数据中的受害者行地址
        
        Args:
            result_data: 原始结果数据字典
            
        Returns:
            transformed_data: 变换后的结果数据字典
        """
        transformed_data = {}
        
        for read_count_key, read_count_data in result_data.items():
            transformed_read_data = {
                "read_count": read_count_data.get("read_count", 0)
            }
            
            # 处理每个pair
            for pair_key, pair_data in read_count_data.items():
                if pair_key == "read_count":
                    continue
                    
                if "hammer_row_1" in pair_data and "hammer_row_2" in pair_data:
                    # 复制攻击者行信息（不需要变换）
                    transformed_pair_data = {
                        "hammer_row_1": pair_data["hammer_row_1"],
                        "hammer_row_2": pair_data["hammer_row_2"]
                    }
                    
                    # 变换受害者行
                    if "errors_in_rows" in pair_data:
                        transformed_errors = {}
                        for victim_row_str, error_data in pair_data["errors_in_rows"].items():
                            victim_row = int(victim_row_str)
                            transformed_victim_row = self.transform_victim_row(victim_row)
                            
                            # 更新错误数据中的行号
                            transformed_error_data = error_data.copy()
                            transformed_error_data["row"] = transformed_victim_row
                            
                            transformed_errors[str(transformed_victim_row)] = transformed_error_data
                        
                        transformed_pair_data["errors_in_rows"] = transformed_errors
                    
                    transformed_read_data[pair_key] = transformed_pair_data
                else:
                    # 如果没有hammer_row信息，直接复制
                    transformed_read_data[pair_key] = pair_data
            
            transformed_data[read_count_key] = transformed_read_data
        
        return transformed_data
    
    def get_transformation_mapping(self, max_row=32):
        """
        获取变换映射表（用于验证）
        
        Args:
            max_row: 最大行号
            
        Returns:
            mapping: 原始行号到变换后行号的映射字典
        """
        mapping = {}
        for row in range(1, max_row + 1):
            transformed = self.transform_victim_row(row)
            mapping[row] = transformed
        return mapping


def transform_file(input_file_path, output_file_path=None):
    """
    变换rowhammer结果文件
    
    Args:
        input_file_path: 输入文件路径
        output_file_path: 输出文件路径(可选，默认在同一目录生成)
    
    Returns:
        bool: 是否成功
    """
    import os
    
    try:
        # 加载输入数据
        with open(input_file_path, 'r') as f:
            data = json.load(f)
        
        # 初始化变换器
        transformer = SamsungRowTransformer()
        
        # 执行变换
        transformed_data = transformer.transform_result_data(data)
        
        # 确定输出文件路径
        if output_file_path is None:
            input_dir = os.path.dirname(input_file_path)
            input_name = os.path.basename(input_file_path)
            name, ext = os.path.splitext(input_name)
            output_file_path = os.path.join(input_dir, f"{name}_samsung_transformed{ext}")
        
        # 保存变换后的数据
        with open(output_file_path, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        
        print(f"✓ 文件变换成功")
        print(f"  输入: {input_file_path}")
        print(f"  输出: {output_file_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ 文件变换失败: {e}")
        return False


def create_simple_test():
    """创建简单的变换测试"""
    print("=== Samsung芯片行地址变换器 ===\n")
    
    transformer = SamsungRowTransformer()
    
    # 显示变换规律说明
    print("变换规律（物理→逻辑）:")
    print("- 每16行为一组")
    print("- 行1-6保持不变")
    print("- 行7-16按反向循环映射：")
    print("  奇数序列反向: 11→7, 15→11, 9→15, 13→9, 7→13")
    print("  偶数序列反向: 14→8, 10→14, 16→10, 12→16, 8→12")
    
    # 测试几个典型例子
    print("\n示例变换:")
    test_rows = [1, 7, 8, 11, 12, 15, 16]
    for row in test_rows:
        transformed = transformer.transform_victim_row(row)
        status = "不变" if row == transformed else "变换"
        print(f"  行{row:2d} -> 行{transformed:2d} ({status})")
    
    print("\n✓ 变换器已准备就绪")


def create_test_data():
    """创建随机测试数据"""
    print("\n=== 创建随机测试数据 ===")
    
    # 生成随机rowhammer测试数据
    test_data = {
        "10000": {
            "read_count": 10000,
        }
    }
    
    # 随机生成几个pair的数据
    for pair_id in range(5):
        hammer_row_1 = random.randint(100, 200)
        hammer_row_2 = hammer_row_1 + 2
        
        pair_data = {
            "hammer_row_1": hammer_row_1,
            "hammer_row_2": hammer_row_2,
            "errors_in_rows": {}
        }
        
        # 随机生成一些受害者行的错误
        victim_rows = [hammer_row_1 + 1, hammer_row_1 + 3, hammer_row_1 + 5]
        for victim_row in victim_rows:
            if random.random() > 0.5:  # 随机决定是否有错误
                error_data = {
                    "bank": 0,
                    "row": victim_row,
                    "col": {
                        str(random.randint(0, 1000)): [random.randint(0, 500)]
                    },
                    "bitflips": random.randint(1, 10)
                }
                pair_data["errors_in_rows"][str(victim_row)] = error_data
        
        test_data["10000"][f"pair_{pair_id}_{pair_id}"] = pair_data
    
    return test_data


def main():
    """主函数"""
    import sys
    import os
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if os.path.exists(input_file):
            print(f"=== 处理文件: {input_file} ===")
            transform_file(input_file)
            return
        else:
            print(f"错误：文件不存在: {input_file}")
            return
    else:
        print("用法: python3 samsung_row_transformer.py <输入文件>")
        print("示例: python3 samsung_row_transformer.py result/a-hammer/a-hammer_single_side_r0-1000_rc40K.json")
        return
    
    # 创建测试数据
    original_data = create_test_data()
    print(f"\n原始测试数据:")
    print(json.dumps(original_data, indent=2))
    
    # 应用变换
    transformed_data = transformer.transform_result_data(original_data)
    print(f"\n变换后数据:")
    print(json.dumps(transformed_data, indent=2))
    
    # 保存测试文件到scripts目录
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    original_file = os.path.join(script_dir, "test_original_data.json")
    transformed_file = os.path.join(script_dir, "test_transformed_data.json")
    
    with open(original_file, "w") as f:
        json.dump(original_data, f, indent=2)
    
    with open(transformed_file, "w") as f:
        json.dump(transformed_data, f, indent=2)
    
    print(f"\n测试文件已保存:")
    print(f"- 原始数据: {original_file}")
    print(f"- 变换数据: {transformed_file}")
    
    # 简单的变换对比
    print(f"\n=== 变换对比 ===")
    for read_count_key, read_count_data in original_data.items():
        for pair_key, pair_data in read_count_data.items():
            if pair_key == "read_count":
                continue
            
            if "errors_in_rows" in pair_data and len(pair_data["errors_in_rows"]) > 0:
                print(f"\n{pair_key}:")
                print(f"攻击者行: {pair_data['hammer_row_1']}, {pair_data['hammer_row_2']}")
                
                original_victims = list(pair_data["errors_in_rows"].keys())
                transformed_victims = list(transformed_data[read_count_key][pair_key]["errors_in_rows"].keys())
                
                print("受害者行变换:")
                for orig, trans in zip(original_victims, transformed_victims):
                    if orig != trans:
                        print(f"  {orig} -> {trans} ✓")
                    else:
                        print(f"  {orig} -> {trans} -")


if __name__ == "__main__":
    main()
