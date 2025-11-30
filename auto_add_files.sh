#!/bin/bash
# 自动添加和提交新的测试数据和分析文件

echo "正在检查新的测试数据和分析文件..."

# 添加新的Python脚本
find rowhammer_tester/scripts/result/ -name "*.py" -type f | while read file; do
    if ! git ls-files --error-unmatch "$file" &>/dev/null; then
        echo "添加新脚本: $file"
        git add "$file"
    fi
done

# 添加新的测试数据
find rowhammer_tester/scripts/result/ -name "*.json" -o -name "*.csv" | while read file; do
    if ! git ls-files --error-unmatch "$file" &>/dev/null; then
        echo "添加测试数据: $file"
        git add "$file"
    fi
done

# 添加新的热力图
find rowhammer_tester/scripts/result/ -name "*.png" -o -name "*.pdf" | while read file; do
    if ! git ls-files --error-unmatch "$file" &>/dev/null; then
        echo "添加热力图: $file"
        git add "$file"
    fi
done

# 添加根目录的分析脚本
find . -maxdepth 1 -name "*.py" | while read file; do
    if ! git ls-files --error-unmatch "$file" &>/dev/null; then
        echo "添加根目录脚本: $file"
        git add "$file"
    fi
done

# 检查是否有新文件被添加
if git diff --cached --quiet; then
    echo "没有新的文件需要提交"
else
    echo "发现新文件，准备提交..."
    git status --porcelain --cached
    
    # 询问是否提交
    read -p "是否要提交这些新文件? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        timestamp=$(date "+%Y-%m-%d %H:%M:%S")
        git commit -m "自动添加新的测试数据和分析文件 - $timestamp"
        echo "文件已提交!"
    else
        echo "取消提交，文件仍在暂存区"
    fi
fi
