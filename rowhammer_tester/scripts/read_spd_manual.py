#!/usr/bin/env python3

import time
import serial
import sys
import re
import argparse

def wait_for_prompt(ser, timeout=5):
    """等待命令提示符，返回捕获到的文本（可能为空）"""
    start_time = time.time()
    response = ""
    # 以小片段读取，累积并检查提示符
    while time.time() - start_time < timeout:
        try:
            while ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                response += chunk
                # 快速返回以便上层能继续
                if 'litex>' in response:
                    return response
        except Exception:
            # 串口可能在读时抛出，忽略并重试直到 timeout
            pass
        time.sleep(0.05)
    return response

def send_command(ser, command, wait=True, timeout=5):
    """发送命令到串口，可设置等待超时（秒）。返回在等待期内捕获的输出。"""
    ser.write((command + '\n').encode())
    if wait:
        return wait_for_prompt(ser, timeout=timeout)
    return ""

def parse_spd_data(response):
    """解析SPD数据"""
    lines = response.split('\n')
    spd_data = []
    
    # 查找内存转储部分
    in_dump = False
    for line in lines:
        if 'Memory dump:' in line:
            in_dump = True
            continue
        elif in_dump and re.match(r'0x[0-9a-fA-F]{8}', line):
            # 提取数据行
            parts = line.split()
            if len(parts) >= 17:  # 地址 + 16字节数据
                for i in range(1, 17):
                    try:
                        byte_val = int(parts[i], 16)
                        spd_data.append(byte_val)
                    except ValueError:
                        pass
        elif in_dump and not line.strip().startswith('0x') and line.strip():
            # 遇到非数据行，结束解析
            break
    
    return spd_data

def main():
    parser = argparse.ArgumentParser(description='Read SPD via LiteX BIOS (sdram_spd 1).')
    parser.add_argument('--port', '-p', default='/dev/ttyUSB1', help='serial device (e.g. /dev/pts/13)')
    parser.add_argument('--baud', '-b', type=int, default=115200, help='baudrate (e.g. 1000000)')
    parser.add_argument('--tries', type=int, default=60, help='number of newline attempts when waiting for litex>')
    args = parser.parse_args()

    # 尝试连接到串口
    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.5)
        print(f"Connected to serial port: {args.port} @ {args.baud}")
    except Exception as e:
        print(f"Failed to connect to serial port {args.port}: {e}")
        return

    try:
        # 清空输入缓冲区
        ser.reset_input_buffer()

        # 自动循环发送回车，直到检测到 litex> 提示符（避免被 Linux login 打断）
        print("Waiting for litex> prompt (auto send enter)...")
        max_tries = args.tries
        found = False
        accumulated = ''
        for i in range(max_tries):
            # 发送一个回车，等待短时间，检查累计输出
            ser.write(b'\n')
            chunk = wait_for_prompt(ser, timeout=1)
            if chunk:
                accumulated += chunk
                # 打印少量调试信息，帮助定位问题
                if i == 0:
                    print('Initial response snippet:')
                    print(chunk[:200])
                # 如果看到 Buildroot 登录提示，自动尝试以 root 登录一次
                low = chunk.lower()
                if ('buildroot login' in low or '\nbuildroot login:' in low or 'buildroot' in low and 'login' in low) and 'root' not in accumulated:
                    try:
                        print('Detected Buildroot login prompt, sending root...')
                        ser.write(b'root\n')
                        # 给系统一点时间响应并捕获输出
                        more = wait_for_prompt(ser, timeout=1)
                        if more:
                            accumulated += more
                            print('Post-login snippet:')
                            print(more[:200])
                    except Exception:
                        pass
            if 'litex>' in accumulated:
                found = True
                print("Received litex> prompt")
                break
            time.sleep(0.2)
        if not found:
            print("Did not detect litex> prompt, aborting")
            print('Last captured output (truncated):')
            print(accumulated[-1000:])
            return

        # 确保没有其他程序占用串口输出
        ser.reset_output_buffer()

        # 按照正确流程：先选通 I2C mux 通道，再让 BIOS 读取 SPD
        print("Selecting I2C mux channel: i2c_write 0x74 0x80 1")
        mux_out = send_command(ser, "i2c_write 0x74 0x80 1", timeout=2)
        if mux_out:
            print('i2c_write response (truncated):')
            print(mux_out[:400])
        time.sleep(0.1)

        # 读取 SPD（此命令可能较慢，增加等待超时）
        print("Reading SPD via 'sdram_spd 1'...")
        response = send_command(ser, "sdram_spd 1", timeout=20)
        print("Raw response:")
        print(response)

        # 解析SPD数据
        spd_data = parse_spd_data(response)
        print(f"Parsed {len(spd_data)} bytes of SPD data")

        # 保存到文件（同时保存原始文本以便对比）
        if spd_data:
            with open('spd_data_manual.bin', 'wb') as f:
                f.write(bytes(spd_data))
            with open('spd_data_manual.txt', 'w') as f:
                f.write(response)
            print("SPD data saved to spd_data_manual.bin and spd_data_manual.txt")
        else:
            print("No SPD data found in sdram_spd output")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        ser.close()

if __name__ == "__main__":
    main()