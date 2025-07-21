# BotShepherd 测试工具

这个目录包含了用于测试BotShepherd的工具和脚本。

## 快速开始

使用快速测试脚本：
```bash
./test/quick_test.sh
```

或者直接运行：
```bash
# 功能测试
python test/test_script.py

# 压力测试
python test/pressure_test_server.py --rate 2.0 --duration 60
```

## 文件说明

### 1. quick_test.sh
交互式快速测试脚本，提供菜单选择不同的测试模式。

**使用方法：**
```bash
./test/quick_test.sh
```

### 2. pressure_test_server.py
压力测试服务器，可以以指定的速率向BotShepherd发送消息进行压力测试。

**功能特点：**
- 模拟napcat客户端连接
- 发送OneBot v11标准的lifecycle消息
- 支持可配置的发送速率和持续时间
- 包含多种类型的测试消息（群聊、私聊、@消息、拍一拍等）
- 包含nonebot指令测试（今日运势、ww帮助等）

**使用方法：**
```bash
# 基本使用（默认1消息/秒，持续60秒）
python test/pressure_test_server.py

# 自定义参数
python test/pressure_test_server.py --rate 5.0 --duration 120 --url ws://localhost:5511

# 查看所有参数
python test/pressure_test_server.py --help
```

**参数说明：**
- `--url`: BotShepherd服务器地址（默认: ws://localhost:5511）
- `--bot-qq`: 机器人QQ号（默认: 3145443954）
- `--group`: 测试群号（默认: 1053786482）
- `--user`: 测试用户QQ号（默认: 2408736708）
- `--rate`: 发送速率，消息/秒（默认: 1.0）
- `--duration`: 测试持续时间，秒（默认: 60）

### 3. test_script.py
简单的测试脚本，发送一系列预定义的测试消息。

**功能特点：**
- 固定的QQ号配置
- 发送6种不同类型的测试消息
- 包含nonebot指令和BotShepherd内置指令测试
- 自动等待响应

**使用方法：**
```bash
python test/test_script.py
```

**测试消息类型：**
1. 今日运势指令（群聊）
2. ww帮助指令（群聊）
3. bs帮助指令（群聊，BotShepherd内置）
4. 私聊消息
5. @机器人消息
6. 拍一拍通知

## 配置说明

### QQ号配置
测试脚本中使用的QQ号：
- **机器人QQ**: 3145443954
- **测试用户QQ**: 2408736708
- **测试群号**: 1053786482

这些QQ号可以在脚本中修改，或通过命令行参数指定（pressure_test_server.py）。

### 连接配置
测试工具会连接到BotShepherd的WebSocket端点，默认为 `ws://localhost:5511`。

确保BotShepherd的连接配置文件中包含对应的client_endpoint配置。

### 消息格式
所有消息都严格按照OneBot v11标准格式构造，包括：
- 正确的消息头信息
- 标准的消息体结构
- 适当的时间戳和ID
- 符合napcat格式的sender信息

## 使用前准备

1. **启动BotShepherd主程序**：
   ```bash
   python main.py
   ```

2. **确保连接配置正确**：
   检查 `config/connections/` 目录下的配置文件，确保有对应的client_endpoint配置。

3. **安装依赖**：
   ```bash
   pip install websockets
   ```

## 测试流程

### 压力测试流程
1. 连接到BotShepherd WebSocket端点
2. 发送lifecycle消息初始化连接
3. 按指定速率循环发送测试消息
4. 实时显示发送统计信息
5. 测试完成后显示总结报告

### 功能测试流程
1. 连接到BotShepherd WebSocket端点
2. 发送lifecycle消息初始化连接
3. 依次发送6种不同类型的测试消息
4. 等待响应并保持连接
5. 自动关闭连接

## 注意事项

1. **连接头信息**：测试工具会发送标准的napcat连接头信息，包括User-Agent、X-Self-Id等。

2. **消息ID**：每条消息都会生成随机的message_id和相关ID，避免重复。

3. **时间戳**：使用当前时间戳，确保消息时间的准确性。

4. **错误处理**：包含完整的错误处理和重连机制。

5. **资源清理**：测试结束后会自动关闭WebSocket连接。

## 故障排除

### 连接失败
- 检查BotShepherd是否正在运行
- 确认WebSocket端点地址是否正确
- 检查防火墙设置

### 消息发送失败
- 检查消息格式是否正确
- 确认QQ号配置是否有效
- 查看BotShepherd日志获取详细错误信息

### 性能问题
- 降低发送速率（--rate参数）
- 检查系统资源使用情况
- 监控网络连接状态

## 扩展开发

可以基于这些测试工具进行扩展：
- 添加更多类型的测试消息
- 实现自动化测试套件
- 添加性能监控和报告功能
- 支持多客户端并发测试
