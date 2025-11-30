#!/usr/bin/env python3
"""
批量生成所有时间点的位翻转热力图
"""

import json
import subprocess
import sys
from pathlib import Path

def generate_all_heatmaps(json_file):
    """为JSON文件中的所有时间点生成热力图"""
    
    print(f"Loading {json_file} to get time points...")
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # 获取所有时间点
    time_points = data['metadata']['time_points']
    
    print(f"Found {len(time_points)} time points: {time_points}")
    
    # 为每个时间点生成热力图
    for time_point in time_points:
        print(f"\nGenerating heatmap for time point: {time_point:.2f}s")
        
        # 调用quick_heatmap.py脚本
        cmd = [
            "/home/hc/rowhammer-tester/.venv/bin/python", 
            "quick_heatmap.py", 
            json_file, 
            "--time", str(time_point), 
            "--save"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Successfully generated heatmap for {time_point:.2f}s")
            else:
                print(f"✗ Error generating heatmap for {time_point:.2f}s")
                print(f"Error: {result.stderr}")
        except Exception as e:
            print(f"✗ Exception occurred: {e}")
    
    print(f"\nAll heatmaps generated! Check the result/result/retention/ directory.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_all_heatmaps.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not Path(json_file).exists():
        print(f"Error: File {json_file} not found")
        sys.exit(1)
    
    generate_all_heatmaps(json_file)
