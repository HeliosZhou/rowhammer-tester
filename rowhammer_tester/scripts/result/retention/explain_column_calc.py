#!/usr/bin/env python3
"""
解释列地址计算逻辑的示例脚本
"""

def calculate_real_column(col_key, bitflip_position):
    """
    计算真实列地址的函数
    
    公式：实际列 = col_key + bitflip_position // 64
    
    Args:
        col_key: JSON中的列键值（字符串形式的数字）
        bitflip_position: 位翻转在该列中的位置
        
    Returns:
        real_col: 计算出的真实列地址
    """
    col = int(col_key)
    real_col = col + bitflip_position // 64
    return real_col

def explain_column_calculation():
    """用具体例子解释列地址计算"""
    print("列地址计算逻辑解释")
    print("=" * 50)
    print("公式：实际列 = col_key + bitflip_position // 64")
    print()
    
    # 从实际JSON数据中的例子
    examples = [
        ("360", 56),   # 来自JSON数据
        ("840", 120), 
        ("176", 281),
        ("480", 385),
        ("632", 109),
        ("1008", 251),
        ("128", 488),
    ]
    
    print(f"{'col_key':<8} {'bitflip_pos':<12} {'pos//64':<8} {'real_col':<10} {'计算过程':<30}")
    print("-" * 80)
    
    for col_key, bitflip_pos in examples:
        col = int(col_key)
        pos_div_64 = bitflip_pos // 64
        real_col = calculate_real_column(col_key, bitflip_pos)
        
        calc_process = f"{col} + {bitflip_pos}//64 = {col} + {pos_div_64}"
        print(f"{col_key:<8} {bitflip_pos:<12} {pos_div_64:<8} {real_col:<10} {calc_process:<30}")
    
    print()
    print("理解这个映射关系：")
    print("1. col_key 是JSON中存储的列标识符")
    print("2. bitflip_position 是在该列标识符内部具体哪个位发生了翻转")
    print("3. 真实的物理列地址 = col_key + bitflip_position // 64")
    print("4. bitflip_position // 64 表示在64位为一组的情况下，位于哪一组")
    
    print()
    print("验证范围检查：")
    print(f"- DRAM总列数: 1024")
    print(f"- col_key范围: 0-1016 (都是8的倍数)")
    print(f"- bitflip_position范围: 0-511")
    print(f"- bitflip_position // 64的范围: 0-{511//64} = 0-7")
    print(f"- 最大real_col: 1016 + 7 = 1023 (刚好在范围内!)")
    
    print()
    print("实际例子:")
    print(f"- 当col_key=360, bitflip_pos=56时: real_col = {calculate_real_column('360', 56)}")
    print(f"  详细计算: 360 + 56//64 = 360 + 0 = 360")
    print(f"- 当col_key=1000, bitflip_pos=448时: real_col = {calculate_real_column('1000', 448)}")
    print(f"  详细计算: 1000 + 448//64 = 1000 + 7 = 1007")
    
    # 检查是否会超出范围
    print()
    print("可能的边界情况：")
    large_examples = [("2000", 100), ("1800", 200), ("2048", 0)]
    for col_key, bitflip_pos in large_examples:
        real_col = calculate_real_column(col_key, bitflip_pos)
        status = "在范围内" if real_col < 1024 else "超出范围"
        print(f"col_key={col_key}, bitflip_pos={bitflip_pos} -> real_col={real_col} ({status})")

if __name__ == "__main__":
    explain_column_calculation()
