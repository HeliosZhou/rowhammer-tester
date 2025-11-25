#!/usr/bin/env python3

def parse_spd_data(file_path):
    """
    解析SPD数据文本文件并转换为二进制数据
    """
    spd_bytes = []
    
    with open(file_path, 'r') as f:
        for line in f:
            # 跳过空行
            if not line.strip():
                continue
                
            # 提取十六进制数据部分
            # 格式: 0x00000000  23 11 0c 03 85 21 00 08 00 60 00 03 01 03 00 00  #....!...`......
            parts = line.strip().split()
            if len(parts) < 2 or not parts[0].startswith('0x'):
                continue
                
            # 提取16个字节的十六进制值
            for i in range(1, 17):
                if i < len(parts):
                    try:
                        # 移除可能存在的标点符号
                        byte_str = parts[i].replace(',', '').replace('.', '')
                        if len(byte_str) == 2 and all(c in '0123456789abcdefABCDEF' for c in byte_str):
                            spd_bytes.append(int(byte_str, 16))
                    except ValueError:
                        # 跳过无效值
                        pass
    
    return spd_bytes

def main():
    # 解析SPD数据
    spd_bytes = parse_spd_data('spd_data.txt')
    
    print(f"解析了 {len(spd_bytes)} 字节的SPD数据")
    
    # 保存为二进制文件
    with open('spd_data.bin', 'wb') as f:
        f.write(bytes(spd_bytes))
    
    print("SPD数据已保存到 spd_data.bin")
    
    # 显示前几个字节作为验证
    print("前32字节:")
    for i in range(min(32, len(spd_bytes))):
        if i % 16 == 0:
            print()
            print(f"0x{i:08x} ", end="")
        print(f"{spd_bytes[i]:02x} ", end="")
    print()

if __name__ == "__main__":
    main()