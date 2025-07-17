# BotShepherd 配置文件说明

## 目录结构

```
config/
├── README.md                           # 本文件
├── global_config.json.template         # 全局配置模板
├── global_config.json                  # 全局配置文件（需要创建）
├── connections/                         # 连接配置目录
│   ├── example.json.template           # 连接配置模板
│   └── *.json                          # 实际连接配置文件
├── account/                            # 账号配置目录
│   └── *.json                          # 账号配置文件（自动生成）
└── group/                              # 群组配置目录
    └── *.json                          # 群组配置文件（自动生成）
```

## 配置文件说明

### 1. 全局配置 (global_config.json)

全局配置文件包含系统的基本设置：

```bash
# 从模板创建配置文件
cp global_config.json.template global_config.json
```

**主要配置项：**

- `superusers`: 超级用户QQ号列表
- `command_prefix`: 指令前缀（默认"bs"）
- `global_aliases`: 全局指令别名
- `blacklist`: 黑名单配置
- `global_filters`: 全局过滤词
- `database`: 数据库配置
- `web_auth`: Web界面认证信息

### 2. 连接配置 (connections/*.json)

每个连接配置文件定义一个WebSocket代理连接：

```bash
# 从模板创建连接配置
cp connections/example.json.template connections/my_connection.json
```

**配置项说明：**

- `name`: 连接名称
- `description`: 连接描述
- `client_endpoint`: 客户端连接的WebSocket地址
- `target_endpoints`: 目标服务器WebSocket地址列表
- `enabled`: 是否启用此连接

### 3. 账号配置 (account/*.json)

账号配置文件会在检测到新账号时自动创建，包含：

- `account_id`: 账号ID（QQ号）
- `name`: 账号名称
- `description`: 账号描述
- `enabled`: 是否启用
- `last_receive_time`: 最后接收消息时间
- `last_send_time`: 最后发送消息时间

### 4. 群组配置 (group/*.json)

群组配置文件会在检测到新群组时自动创建，包含：

- `group_id`: 群组ID
- `description`: 群组描述
- `enabled`: 是否启用
- `expire_time`: 到期时间
- `last_message_time`: 最后消息时间
- `filters`: 群组过滤词设置

## 初始化配置

### 方法1：使用安装脚本

```bash
python install.py
```

### 方法2：使用命令行

```bash
python main.py --setup
```

### 方法3：手动创建

```bash
# 创建全局配置
cp config/global_config.json.template config/global_config.json

# 创建连接配置
cp config/connections/example.json.template config/connections/default.json

# 编辑配置文件
vim config/global_config.json
vim config/connections/default.json
```

## 配置示例

### NapCat框架配置示例

```json
{
  "name": "NapCat连接",
  "description": "连接到NapCat框架",
  "client_endpoint": "ws://localhost:3001/onebot/v11/ws",
  "target_endpoints": [
    "ws://localhost:3000/onebot/v11/ws"
  ],
  "enabled": true
}
```

### 云崽框架配置示例

```json
{
  "name": "云崽连接",
  "description": "连接到云崽框架", 
  "client_endpoint": "ws://localhost:2536/OneBotv11",
  "target_endpoints": [
    "ws://localhost:2537/OneBotv11"
  ],
  "enabled": true
}
```

### 一对多连接示例

```json
{
  "name": "多目标连接",
  "description": "一个客户端连接多个目标服务器",
  "client_endpoint": "ws://localhost:8080/onebot",
  "target_endpoints": [
    "ws://server1:3000/onebot/v11/ws",
    "ws://server2:3001/onebot/v11/ws", 
    "ws://server3:3002/onebot/v11/ws"
  ],
  "enabled": true
}
```

## 安全注意事项

⚠️ **重要提醒：**

1. **不要将配置文件提交到版本控制系统**
   - 配置文件包含QQ号、密码等敏感信息
   - `.gitignore`已配置忽略所有配置文件

2. **定期备份配置文件**
   ```bash
   # 使用Makefile备份
   make backup-config
   
   # 或手动备份
   tar -czf config_backup.tar.gz config/
   ```

3. **修改默认密码**
   - Web界面默认用户名/密码为 admin/admin
   - 请在`global_config.json`中修改`web_auth`配置

4. **设置合适的超级用户**
   - 在`superusers`中设置你的QQ号
   - 移除示例QQ号

## 配置验证

启动前可以运行配置验证：

```bash
# 运行系统测试
python main.py --test

# 检查依赖
python check_requirements.py
```

## 故障排除

### 配置文件格式错误

```bash
# 验证JSON格式
python -m json.tool config/global_config.json
```

### 权限问题

```bash
# 检查文件权限
ls -la config/
chmod 600 config/*.json  # 设置适当权限
```

### 端口冲突

- 检查WebSocket端点是否被占用
- 修改配置文件中的端口号
- 确保防火墙允许相应端口

## 更多帮助

- 查看主README.md文件
- 运行 `python main.py --help`
- 访问Web管理界面：http://localhost:8080
