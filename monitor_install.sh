#!/bin/bash

# rowhammer-tester 安装进度监控脚本

echo "=== Rowhammer Tester 安装进度监控 ==="
echo "开始时间: $(date)"
echo ""

# 激活虚拟环境
source venv/bin/activate

# 记录开始时的包数量
INITIAL_COUNT=$(pip list 2>/dev/null | wc -l)
echo "初始已安装包数: $INITIAL_COUNT"
echo ""

# 监控循环
while true; do
    # 检查pip安装进程是否还在运行
    PIP_PROCESS=$(ps aux | grep "pip install" | grep requirements | grep -v grep)
    
    if [ -z "$PIP_PROCESS" ]; then
        echo -e "\n✅ 安装进程已完成！"
        break
    fi
    
    # 获取当前包数量
    CURRENT_COUNT=$(pip list 2>/dev/null | wc -l)
    PROGRESS=$((CURRENT_COUNT - INITIAL_COUNT))
    
    # 检查最近安装的包
    RECENT_PACKAGES=$(pip list 2>/dev/null | tail -5 | head -4)
    
    # 清屏并显示状态
    clear
    echo "=== Rowhammer Tester 安装进度监控 ==="
    echo "时间: $(date)"
    echo ""
    echo "📦 安装状态:"
    echo "   初始包数: $INITIAL_COUNT"
    echo "   当前包数: $CURRENT_COUNT"
    echo "   新增包数: $PROGRESS"
    echo ""
    echo "🔄 安装进程信息:"
    echo "   PID: $(echo $PIP_PROCESS | awk '{print $2}')"
    echo "   状态: 正在安装..."
    echo ""
    echo "📋 最近安装的包:"
    echo "$RECENT_PACKAGES"
    echo ""
    echo "💡 提示: 按 Ctrl+C 退出监控（不会停止安装）"
    
    # 等待3秒后刷新
    sleep 3
done

# 安装完成后的最终检查
echo ""
echo "=== 最终安装检查 ==="
./check_environment.sh

echo ""
echo "🎉 监控完成！安装进程已结束。"
