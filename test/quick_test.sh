#!/bin/bash
# BotShepherd 快速测试脚本

echo "🤖 BotShepherd 快速测试工具"
echo "================================"

# 检查Python是否安装
if ! command -v python &> /dev/null; then
    echo "❌ Python未安装，请先安装Python"
    exit 1
fi

# 检查websockets模块
if ! python -c "import websockets" &> /dev/null; then
    echo "⚠️ websockets模块未安装，正在安装..."
    pip install websockets
fi

echo ""
echo "请选择测试类型："
echo "1) 功能测试 - 发送预定义的测试消息"
echo "2) 压力测试 - 低速率测试 (1消息/秒, 30秒)"
echo "3) 压力测试 - 中速率测试 (5消息/秒, 60秒)"
echo "4) 压力测试 - 高速率测试 (10消息/秒, 30秒)"
echo "5) 自定义压力测试"
echo ""

read -p "请输入选择 (1-5): " choice

case $choice in
    1)
        echo "🧪 开始功能测试..."
        python test/test_script.py
        ;;
    2)
        echo "🚀 开始低速率压力测试..."
        python test/pressure_test_server.py --rate 1.0 --duration 30
        ;;
    3)
        echo "🚀 开始中速率压力测试..."
        python test/pressure_test_server.py --rate 5.0 --duration 60
        ;;
    4)
        echo "🚀 开始高速率压力测试..."
        python test/pressure_test_server.py --rate 10.0 --duration 30
        ;;
    5)
        echo "🔧 自定义压力测试配置"
        read -p "发送速率 (消息/秒): " rate
        read -p "持续时间 (秒): " duration
        read -p "服务器地址 [ws://localhost:5666]: " url
        url=${url:-ws://localhost:5666}
        
        echo "🚀 开始自定义压力测试..."
        python test/pressure_test_server.py --rate $rate --duration $duration --url $url
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✅ 测试完成！"
