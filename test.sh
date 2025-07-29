# API性能测试 - curl命令版本

# 设置变量
SERVER="http://192.168.2.113:5100"
USERNAME="admin"
PASSWORD="admin"

echo "🚀 开始API性能测试"
echo "服务器: $SERVER"
echo ""

# 1. 先登录获取session
echo "🔐 步骤1: 登录获取session"
curl -c cookies.txt \
     -d "username=$USERNAME&password=$PASSWORD" \
     -X POST \
     -w "登录耗时: %{time_total}s\n" \
     -s -o login_response.txt \
     "$SERVER/login"

echo "✅ 登录完成，session已保存到 cookies.txt"
echo ""

# 2. 测试 /api/groups API - 单次测试
echo "📊 步骤2: 测试 /api/groups (单次)"
curl -b cookies.txt \
     -w "总耗时: %{time_total}s | DNS解析: %{time_namelookup}s | 连接: %{time_connect}s | 传输: %{time_starttransfer}s | 响应大小: %{size_download} bytes\n" \
     -s -o groups_response.json \
     "$SERVER/api/groups"

echo "✅ API响应已保存到 groups_response.json"
echo ""

# 3. 多次测试取平均值
echo "🔄 步骤3: 进行5次测试取平均值"
echo "测试次数 | 总耗时(s) | 传输时间(s) | 响应大小(bytes)"
echo "-------|----------|-----------|-------------"

for i in {1..5}; do
    curl -b cookies.txt \
         -w "$i        | %{time_total}   | %{time_starttransfer}     | %{size_download}\n" \
         -s -o /dev/null \
         "$SERVER/api/groups"
    sleep 1
done

echo ""

# 4. 并发测试
echo "⚡ 步骤4: 并发测试 (3个同时请求)"
echo "启动3个并发请求..."

# 后台启动3个curl进程
(curl -b cookies.txt -w "并发请求1: %{time_total}s\n" -s -o /dev/null "$SERVER/api/groups") &
(curl -b cookies.txt -w "并发请求2: %{time_total}s\n" -s -o /dev/null "$SERVER/api/groups") &
(curl -b cookies.txt -w "并发请求3: %{time_total}s\n" -s -o /dev/null "$SERVER/api/groups") &

# 等待所有后台进程完成
wait

echo ""

# 5. 分析响应内容
echo "📋 步骤5: 分析响应内容"
if [ -f "groups_response.json" ]; then
    echo "响应文件大小: $(wc -c < groups_response.json) bytes"
    
    # 如果有jq工具，分析JSON内容
    if command -v jq &> /dev/null; then
        echo "群组数量: $(jq 'length' groups_response.json)"
        echo "示例群组ID: $(jq -r 'keys[0:3][]?' groups_response.json | head -3 | paste -sd ', ')"
    else
        echo "群组数量: $(grep -o '"[0-9]*"' groups_response.json | wc -l)"
        echo "文件内容预览 (前200字符):"
        head -c 200 groups_response.json
        echo "..."
    fi
fi

echo ""
echo "🎉 测试完成！"
echo ""
echo "文件说明:"
echo "- cookies.txt: 登录session"
echo "- login_response.txt: 登录响应"
echo "- groups_response.json: API响应数据"
echo ""
echo "清理临时文件: rm cookies.txt login_response.txt groups_response.json"