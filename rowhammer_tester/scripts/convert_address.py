#!/usr/bin/env python3

import json
import argparse
import os
import sys
from collections import defaultdict

def convert_physical_address(original_bank, original_row, original_col, original_bit):
    """
    将逻辑地址转换为物理地址
    
    Args:
        original_bank: 原始bank值
        original_row: 原始row值
        original_col: 原始col值 
        original_bit: 原始bit值
        
    Returns:
        tuple: (new_bank, new_row, new_col, new_bit, chip)
    """
    # 转换公式
    new_bank = original_bank  # bank保持不变
    chip = original_bit // 64 + 1  # 计算chip值
    new_row = original_row  # row不变
    new_col = original_col + (original_bit % 64) // 8 + 1
    new_bit = (original_bit % 64) % 8
    
    return new_bank, new_row, new_col, new_bit, chip

def process_retention_error_data(errors_data):
    """
    处理retention格式的错误数据，转换地址
    
    Args:
        errors_data: 原始错误数据字典 (row -> error_info)
        
    Returns:
        dict: 转换后的错误数据
    """
    converted_data = {}
    
    for row_key, row_data in errors_data.items():
        if isinstance(row_data, dict) and 'bank' in row_data:
            original_bank = row_data.get('bank', 0)
            
            # 解析行键，去掉可能的_bank或_chip后缀
            try:
                if '_bank' in row_key:
                    original_row = int(row_key.split('_bank')[0])
                elif '_chip' in row_key:
                    original_row = int(row_key.split('_chip')[0])
                else:
                    original_row = int(row_key)
            except ValueError:
                # 如果无法解析，使用row字段的值
                original_row = row_data.get('row', 0)
            
            # 按新的chip分组数据
            bank_groups = defaultdict(lambda: {
                'bank': original_bank,  # 保持原始bank值
                'row': original_row,
                'col': {},
                'bitflips': 0
            })
            
            # 处理列数据
            for col_key, col_data in row_data.get('col', {}).items():
                original_col = int(col_key)
                
                if 'bitflip_positions' in col_data:
                    # 新格式：有bitflip_positions
                    bit_positions = col_data['bitflip_positions']
                    for bit_value in bit_positions:
                        # 转换地址
                        new_bank, new_row, new_col, new_bit, chip = convert_physical_address(
                            original_bank, original_row, original_col, bit_value
                        )
                        
                        # 按chip分组数据，但使用原始bank值
                        chip_key = chip
                        if chip_key not in bank_groups:
                            bank_groups[chip_key] = {
                                'bank': new_bank,  # 保持原始bank值
                                'row': new_row,
                                'col': {},
                                'bitflips': 0,
                                'chip': chip
                            }
                        
                        # 添加到对应列
                        col_str = str(new_col)
                        if col_str not in bank_groups[chip_key]['col']:
                            bank_groups[chip_key]['col'][col_str] = {
                                'bitflip_positions': [],
                                'total_bitflips': 0
                            }
                        
                        bank_groups[chip_key]['col'][col_str]['bitflip_positions'].append(new_bit)
                        bank_groups[chip_key]['col'][col_str]['total_bitflips'] += 1
                        bank_groups[chip_key]['bitflips'] += 1
                else:
                    # 旧格式：直接是bit值列表
                    if isinstance(col_data, list):
                        for bit_value in col_data:
                            new_bank, new_row, new_col, new_bit, chip = convert_physical_address(
                                original_bank, original_row, original_col, bit_value
                            )
                            
                            # 按chip分组数据，但使用原始bank值
                            chip_key = chip
                            if chip_key not in bank_groups:
                                bank_groups[chip_key] = {
                                    'bank': new_bank,  # 保持原始bank值
                                    'row': new_row,
                                    'col': {},
                                    'bitflips': 0,
                                    'chip': chip
                                }
                            
                            col_str = str(new_col)
                            if col_str not in bank_groups[chip_key]['col']:
                                bank_groups[chip_key]['col'][col_str] = {
                                    'bitflip_positions': [],
                                    'total_bitflips': 0
                                }
                            
                            bank_groups[chip_key]['col'][col_str]['bitflip_positions'].append(new_bit)
                            bank_groups[chip_key]['col'][col_str]['total_bitflips'] += 1
                            bank_groups[chip_key]['bitflips'] += 1
            
            # 排序并添加到结果
            for chip_id, bank_data in bank_groups.items():
                for col_key in bank_data['col']:
                    bank_data['col'][col_key]['bitflip_positions'].sort()
                
                if len(bank_groups) == 1:
                    # 只有一个chip，使用原始行键
                    converted_data[row_key] = bank_data
                else:
                    # 多个chip，创建新的行键
                    new_row_key = f"{row_key}_chip{chip_id}"
                    converted_data[new_row_key] = bank_data
        else:
            # 简单的bitflips计数，保持原样
            converted_data[row_key] = row_data
    
    return converted_data

def process_repeat_details(repeat_details_list):
    """
    处理repeat_details列表
    
    Args:
        repeat_details_list: repeat_details数组
        
    Returns:
        list: 转换后的repeat_details数组
    """
    converted_list = []
    
    for repeat_detail in repeat_details_list:
        if isinstance(repeat_detail, dict):
            converted_detail = process_retention_error_data(repeat_detail)
            converted_list.append(converted_detail)
        else:
            converted_list.append(repeat_detail)
    
    return converted_list

def convert_retention_json_file(input_file, output_file=None):
    """
    转换retention JSON文件中的地址数据
    
    Args:
        input_file: 输入JSON文件路径
        output_file: 输出JSON文件路径，如果为None则生成默认名称
    """
    # 读取原始JSON文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading input file: {e}")
        return False
    
    # 处理数据
    converted_data = {
        'metadata': data.get('metadata', {}),
        'raw_data': {}
    }
    
    # 处理raw_data
    for time_key, time_data in data.get('raw_data', {}).items():
        converted_time_data = {
            'attack_time': time_data.get('attack_time'),
            'repeat_results': time_data.get('repeat_results', []),
            'repeat_details': process_repeat_details(time_data.get('repeat_details', [])),
            'errors_summary': time_data.get('errors_summary', {})
        }
        
        converted_data['raw_data'][time_key] = converted_time_data
    
    # 确定输出文件路径
    if output_file is None:
        # 在原文件名前加上fix前缀
        dir_path = os.path.dirname(input_file)
        base_name = os.path.basename(input_file)
        name, ext = os.path.splitext(base_name)
        output_file = os.path.join(dir_path, f"fix_{name}{ext}")
    
    # 写入转换后的数据
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, indent=2, ensure_ascii=False)
        print(f"Converted data written to: {output_file}")
        return True
    except Exception as e:
        print(f"Error writing output file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert logical addresses to physical addresses in retention JSON files')
    parser.add_argument('input_file', help='Input JSON file path')
    parser.add_argument('-o', '--output', help='Output JSON file path (default: add fix_ prefix)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' does not exist")
        return 1
    
    success = convert_retention_json_file(args.input_file, args.output)
    return 0 if success else 1

def test_conversion():
    """测试转换函数"""
    # 测试用例：bank=0,row=0,col=0,bit=156
    bank, row, col, bit, chip = convert_physical_address(0, 0, 0, 156)
    print(f"Test conversion: bank=0,row=0,col=0,bit=156")
    print(f"Result: bank={bank},row={row},col={col},bit={bit},chip={chip}")
    
    # 验证结果
    expected_bank = 0  # bank保持不变
    expected_chip = 156 // 64 + 1  # 3
    expected_row = 0
    expected_col = 0 + (156 % 64) // 8 + 1  # 4
    expected_bit = (156 % 64) % 8  # 4
    
    print(f"Expected: bank={expected_bank},row={expected_row},col={expected_col},bit={expected_bit},chip={expected_chip}")
    assert bank == expected_bank, f"Bank mismatch: got {bank}, expected {expected_bank}"
    assert row == expected_row, f"Row mismatch: got {row}, expected {expected_row}"
    assert col == expected_col, f"Col mismatch: got {col}, expected {expected_col}"
    assert bit == expected_bit, f"Bit mismatch: got {bit}, expected {expected_bit}"
    assert chip == expected_chip, f"Chip mismatch: got {chip}, expected {expected_chip}"
    print("✓ Test passed!")

if __name__ == "__main__":
    # 如果没有命令行参数，运行测试
    if len(sys.argv) == 1:
        test_conversion()
    else:
        sys.exit(main())
