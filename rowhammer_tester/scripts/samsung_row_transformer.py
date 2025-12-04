#!/usr/bin/env python3
"""
Samsung芯片特殊地址映射变换器

基于新的三星芯片地址映射规律：
- 每16行为1组
- 前8行保持不变（相对位置0-7）  
- 后8行按照位反转规则变换（相对位置8-15）

变换规则：
当第4位为1时，将第2、3位取反，第1位不动

具体映射（以400开始的组为例）：
400-407: 保持不变
408(8) -> 414, 409(9) -> 415, 410(10) -> 412, 411(11) -> 413
412(12) -> 410, 413(13) -> 411, 414(14) -> 408, 415(15) -> 409

二进制位操作（相对位置8-15）：
8(1000) -> 14(1110)  # 第2、3位取反：10 -> 11
9(1001) -> 15(1111)  # 第2、3位取反：10 -> 11
10(1010) -> 12(1100) # 第2、3位取反：01 -> 10
11(1011) -> 13(1101) # 第2、3位取反：01 -> 10
12(1100) -> 10(1010) # 第2、3位取反：11 -> 00
13(1101) -> 11(1011) # 第2、3位取反：11 -> 00
14(1110) -> 8(1000)  # 第2、3位取反：11 -> 00
15(1111) -> 9(1001)  # 第2、3位取反：11 -> 00

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
        
        基于新的三星芯片地址映射规律：
        - 每16行为一组
        - 前8行保持不变（相对位置0-7）
        - 后8行按照位反转规则变换（相对位置8-15）
        - 当第4位为1时，将第2、3位取反，第1位不动
        
        具体映射（以相对位置为例）：
        8(1000) -> 14(1110)  # 第2、3位取反：10 -> 11
        9(1001) -> 15(1111)  # 第2、3位取反：10 -> 11  
        10(1010) -> 12(1100) # 第2、3位取反：01 -> 10
        11(1011) -> 13(1101) # 第2、3位取反：01 -> 10
        12(1100) -> 10(1010) # 第2、3位取反：11 -> 00 
        13(1101) -> 11(1011) # 第2、3位取反：11 -> 00
        14(1110) -> 8(1000)  # 第2、3位取反：11 -> 00
        15(1111) -> 9(1001)  # 第2、3位取反：11 -> 00
        
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
        
        # 前8行保持不变（相对位置0-7）
        if 0 <= group_offset <= 7:
            return row
        
        # 后8行按位反转规则变换（相对位置8-15）
        if 8 <= group_offset <= 15:
            # 当第4位为1时（即相对位置8-15），将第2、3位取反
            # 提取第1、2、3位
            bit_0 = group_offset & 1      # 第1位（最低位）
            bit_1 = (group_offset >> 1) & 1  # 第2位  
            bit_2 = (group_offset >> 2) & 1  # 第3位
            bit_3 = (group_offset >> 3) & 1  # 第4位（应该为1）
            
            # 第2、3位取反，第1位不动，第4位保持为1
            new_bit_1 = 1 - bit_1  # 取反
            new_bit_2 = 1 - bit_2  # 取反
            
            # 重新组合
            transformed_offset = (bit_3 << 3) | (new_bit_2 << 2) | (new_bit_1 << 1) | bit_0
            
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
                    # 变换攻击者行信息（同样需要变换）
                    hammer_row_1 = pair_data["hammer_row_1"]
                    hammer_row_2 = pair_data["hammer_row_2"]
                    transformed_pair_data = {
                        "hammer_row_1": self.transform_victim_row(hammer_row_1),
                        "hammer_row_2": self.transform_victim_row(hammer_row_2)
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
    print("- 前8行（相对位置0-7）保持不变")
    print("- 后8行（相对位置8-15）按位反转规则变换：")
    print("  当第4位为1时，将第2、3位取反，第1位不动")
    
    # 测试一个完整的16行组（以400-415为例）
    print("\n示例变换（行400-415）:")
    base_row = 400
    for offset in range(16):
        row = base_row + offset
        transformed = transformer.transform_victim_row(row)
        if row == transformed:
            status = "不变"
        else:
            status = f"变换 ({offset:04b} -> {transformed-base_row:04b})"
        print(f"  行{row:3d} -> 行{transformed:3d} ({status})")
    
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
