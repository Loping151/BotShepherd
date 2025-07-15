# BotShepherd - WebSocket代理管理系统

BotShepherd是一个功能强大的WebSocket代理管理系统，专为NapCat和Yunzai之间的连接管理而设计。它提供了直观的Web界面来管理多个WebSocket代理连接配置。

## 功能特性

- 🌐 **Web管理界面**: 直观的Web UI，支持连接配置的可视化管理
- 🔄 **多连接支持**: 支持管理多个WebSocket代理连接
- ⚙️ **灵活配置**: 支持动态添加、编辑、删除连接配置
- 📊 **实时状态**: 实时显示代理服务器和连接状态
- 🚀 **一键启停**: 支持单独启动/停止每个代理服务
- 📝 **日志记录**: 详细的消息转发日志记录
- 💾 **持久化存储**: 配置自动保存到JSON文件

## 项目结构

```
BotShepherd/
├── app/                    # 核心应用模块
│   ├── config_manager.py   # 配置管理
│   ├── websocket_proxy.py  # WebSocket代理核心
│   └── web_api.py          # Web API接口
├── static/                 # 静态资源
│   ├── css/style.css       # 样式文件
│   └── js/app.js           # 前端JavaScript
├── templates/              # HTML模板
│   └── index.html          # 主页面
├── config/                 # 配置文件
│   └── connections.json    # 连接配置
├── logs/                   # 日志文件
├── main.py                 # 主程序入口
└── requirements.txt        # 依赖项
```

## 安装和使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动系统

```bash
python main.py
```

### 3. 访问Web界面

打开浏览器访问: http://localhost:5000

## 连接配置格式

连接配置使用以下格式：

```json
{
  "connections": {
    "connection_id": {
      "name": "连接名称",
      "client_endpoint": "ws://localhost:2537/OneBotv11",
      "target_endpoint": "ws://localhost:2536/OneBotv11",
      "enabled": true,
      "description": "连接描述"
    }
  }
}
```

- **client_endpoint**: Yunzai连接的地址（代理服务器监听地址）
- **target_endpoint**: NapCat的实际地址（代理转发目标）

## Web界面功能

### 连接管理
- 添加新的连接配置
- 编辑现有连接配置
- 删除不需要的连接
- 启用/禁用连接

### 代理控制
- 启动指定连接的代理服务
- 停止运行中的代理服务
- 查看代理服务状态

### 状态监控
- 实时显示活跃服务器数量
- 显示当前连接数
- 查看连接详细信息

## 配置说明

### 系统设置

在`config/connections.json`中的`settings`部分可以配置：

- `log_to_file`: 是否记录日志到文件
- `log_file_name`: 日志文件路径
- `auto_start`: 是否自动启动启用的连接

### 端口配置

确保配置的端口没有被其他程序占用：
- 默认Web界面端口: 5000
- 代理服务端口: 根据连接配置而定

## 故障排除

### 端口占用问题
如果遇到端口占用错误，请：
1. 检查端口是否被其他程序使用
2. 修改连接配置中的端口号
3. 或停止占用端口的程序

### 连接失败
如果代理连接失败，请检查：
1. 目标端点地址是否正确
2. NapCat服务是否正常运行
3. 网络连接是否正常

## 开发说明

### 项目架构
- **ConfigManager**: 负责配置文件的读写和管理
- **WebSocketProxy**: 核心代理逻辑，处理WebSocket连接转发
- **WebAPI**: Flask Web服务，提供REST API接口
- **前端**: Bootstrap + JavaScript，提供用户界面

### 扩展开发
项目采用模块化设计，可以轻松扩展新功能：
- 添加新的API接口到`web_api.py`
- 扩展配置管理功能到`config_manager.py`
- 增强代理功能到`websocket_proxy.py`

## 许可证

本项目采用MIT许可证。