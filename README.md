# 🐑 BotShepherd - Bot牧羊人

**BotShepherd（Bot牧羊人）** 是一个强大的OneBot v11协议WebSocket代理和管理系统。就像牧羊人管理羊群一样，BotShepherd帮助您统一管理和协调多个Bot实例，实现一对多的连接管理、消息过滤、统计分析和权限控制。

## 🌟 核心特性

### 🔗 连接管理
- **一对多代理**：一个客户端连接对应多个目标框架连接
- **实时监控**：WebSocket连接状态实时监控和管理
- **自动重连**：连接断开时自动重连机制
- **负载均衡**：支持多目标端点的负载分配

### 📨 消息处理
- **OneBot v11标准**：完整兼容OneBot v11协议规范
- **消息解析**：支持文本、图片、@、回复、转发等所有消息类型
- **消息标准化**：可选的消息格式标准化（如NapCat兼容）
- **别名系统**：全局指令别名替换功能

### 🛡️ 权限与过滤
- **三级权限**：superuser > 群管/群主 > 普通用户
- **智能过滤**：全局+群组双层过滤系统
- **黑白名单**：支持用户和群组黑名单管理
- **前缀保护**：防止诱导触发的前缀保护机制

### 📊 统计分析
- **实时统计**：消息数量、指令使用、关键词监控
- **趋势分析**：7天/24小时消息量趋势图表
- **数据查询**：支持按日期、关键词、群组等维度查询
- **自动清理**：可配置的数据过期自动清理

### 🎛️ Web管理界面
- **现代化UI**：基于Bootstrap 5的响应式界面
- **实时监控**：连接状态、消息统计实时更新
- **配置管理**：所有配置项的可视化管理
- **图表展示**：Chart.js驱动的数据可视化

## 🚀 快速开始

### 环境要求
- Python 3.8+
- SQLite/MySQL/PostgreSQL（可选）

### 安装步骤

#### 方法一：自动安装（推荐）

1. **克隆项目**
```bash
git clone https://github.com/Loping151/BotShepherd.git
cd BotShepherd
```

2. **运行安装脚本**
```bash
python install.py
```

3. **启动系统**
```bash
python main.py
```

#### 方法二：手动安装

1. **克隆项目**
```bash
git clone https://github.com/Loping151/BotShepherd.git
cd BotShepherd
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **初始化配置**
```bash
python main.py --setup
```

4. **启动系统**
```bash
python main.py
```

#### 方法三：使用Makefile（Linux/Mac）

```bash
# 安装依赖并初始化
make quick-start

# 启动系统
make run
```

### 依赖检查

如果遇到依赖问题，可以运行依赖检查工具：

```bash
python check_requirements.py
```

### 系统测试

在启动前，建议运行系统测试确保一切正常：

```bash
python main.py --test
```

### 访问Web界面

启动后，打开浏览器访问 `http://localhost:8080`
- 默认用户名：`admin`
- 默认密码：`admin`

### 基础配置

#### 1. 连接配置
在 `config/connections.json` 中配置连接信息：

```json
{
  "connections": {
    "default": {
      "name": "默认连接",
      "description": "NapCat到Yunzai的代理连接",
      "client_endpoint": "ws://localhost:2537/OneBotv11",
      "target_endpoints": [
        "ws://localhost:2536/OneBotv11"
      ],
      "enabled": true
    }
  }
}
```

#### 2. 全局配置
在 `config/global_config.json` 中配置系统参数：

```json
{
  "superusers": ["123456789"],
  "command_prefix": "bs",
  "global_aliases": {
    "ww": ["ww", "xw"]
  },
  "allow_private": true,
  "private_friend_only": true
}
```

## 📖 使用指南

### 指令系统

BotShepherd内置了丰富的指令系统，默认前缀为 `bs`：

- `bs帮助` - 显示帮助信息
- `bs统计 -d today` - 查看今日统计
- `bs统计 -k 关键词` - 搜索关键词
- `bs黑名单 add 123456` - 添加黑名单
- `bs群管理 expire 群号 30` - 设置群组30天后到期
- `bs触发 QQ号 指令` - 模拟用户发送指令

### 权限系统

1. **Superuser（超级用户）**
   - 配置在 `global_config.json` 中
   - 拥有所有权限，消息不受过滤限制

2. **群管理员**
   - 通过OneBot消息中的 `role` 字段识别
   - 可管理群组设置和过滤词

3. **普通用户**
   - 默认权限等级
   - 受所有过滤规则限制

### 过滤系统

#### 全局过滤
- **接收过滤**：阻止包含特定词汇的消息传递给框架
- **发送过滤**：阻止包含特定词汇的消息发送给客户端
- **前缀保护**：为特定前缀添加警告标识

#### 群组过滤
- **双层控制**：superuser设置 + 群管设置
- **优先级**：先执行superuser过滤，再执行群管过滤
- **灵活配置**：每个群组独立的过滤词列表

## 🔧 高级配置

### 数据库配置

支持多种数据库类型：

```json
{
  "database": {
    "type": "sqlite",
    "data_path": "./data",
    "auto_expire_days": 30
  }
}
```

### 消息标准化

启用NapCat消息标准化：

```json
{
  "message_normalization": {
    "enabled": true,
    "normalize_napcat_sent": true
  }
}
```

### 日志配置

```json
{
  "logging": {
    "level": "INFO",
    "file_rotation": true,
    "keep_days": 7
  }
}
```

## 📊 统计功能

### 支持的统计维度
- **时间维度**：今日、昨日、指定日期、时间段
- **账号维度**：单账号或全部账号统计
- **群组维度**：按群组分别统计
- **内容维度**：指令统计、关键词搜索

### 统计指令示例
```bash
bs统计 -d today                    # 今日统计
bs统计 -d 2025-07-01               # 指定日期
bs统计 -k 小维                     # 关键词搜索
bs统计 -c ww                       # 指令统计
bs统计 -a -g                       # 全部账号按群组统计
```

## 🌐 Web界面功能

### 仪表板
- 实时系统状态监控
- 消息量趋势图表
- 连接状态总览
- 过滤率统计

### 连接管理
- 连接配置的增删改查
- 代理服务的启动/停止/重启
- 连接状态实时监控

### 账号管理
- QQ账号的启用/禁用
- 账号活跃状态监控
- 账号配置管理

### 群组管理
- 群组的启用/禁用
- 到期时间设置
- 过滤词配置

### 统计分析
- 多维度数据查询
- 图表可视化展示
- 数据导出功能

## 🛠️ 开发指南

### 项目结构
```
BotShepherd/
├── app/                    # 核心应用代码
│   ├── onebot/            # OneBot协议解析
│   ├── config_manager.py  # 配置管理
│   ├── database.py        # 数据库操作
│   ├── websocket_proxy.py # WebSocket代理
│   └── web_api.py         # Web API接口
├── config/                # 配置文件目录
├── data/                  # 数据库文件目录
├── logs/                  # 日志文件目录
├── static/                # 静态资源
├── templates/             # HTML模板
└── main.py               # 主程序入口
```

### 添加自定义指令

1. 继承 `Command` 基类
2. 实现 `execute` 方法
3. 注册到 `CommandHandler`

```python
class MyCommand(Command):
    def __init__(self):
        super().__init__(
            name="我的指令",
            description="自定义指令示例",
            required_permission=PermissionLevel.MEMBER
        )
    
    async def execute(self, ctx: CommandContext):
        return ctx.reply("Hello World!")

# 注册指令
command_handler.register_command(MyCommand())
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置
```bash
# 克隆项目
git clone https://github.com/Loping151/BotShepherd.git
cd BotShepherd

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
python main.py --test

# 代码格式化
make format

# 代码检查
make lint

# 启动开发服务器
python main.py
```

### 常用命令

```bash
# 使用Makefile（推荐）
make help          # 查看所有可用命令
make install       # 安装依赖
make setup         # 初始化配置
make test          # 运行测试
make run           # 启动系统
make clean         # 清理临时文件

# 直接使用Python
python main.py --help     # 查看帮助
python main.py --setup    # 初始化配置
python main.py --test     # 运行测试
python main.py            # 启动系统
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [OneBot](https://onebot.dev/) - 聊天机器人应用接口标准
- [NapCat](https://github.com/NapNeko/NapCatQQ) - QQ机器人框架
- [Yunzai-Bot](https://github.com/yoimiya-kokomi/Yunzai-Bot) - 原神QQ群机器人
- [Flask](https://flask.palletsprojects.com/) - Web框架
- [Bootstrap](https://getbootstrap.com/) - 前端UI框架

---

**BotShepherd** - 让Bot管理变得简单而强大 🐑✨
