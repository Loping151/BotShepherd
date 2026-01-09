# BotShepherd API 文档

## 概述

BotShepherd Web API 提供了完整的系统管理功能，包括连接管理、账号管理、群组管理、统计分析、消息查询等功能。所有API都需要通过Web界面登录认证后才能访问。

**基础URL**: `http://localhost:5100`，如果修改端口，请自行修改。

**认证方式**: Session认证（需要先通过Web界面登录）

---

## 认证相关

### 登录
- **URL**: `/login`
- **方法**: POST
- **描述**: 用户登录认证
- **请求体**:
  ```json
  {
    "username": "admin",
    "password": "admin"
  }
  ```
- **响应**: 重定向到主页或返回错误信息

### 登出
- **URL**: `/logout`
- **方法**: GET
- **描述**: 用户登出
- **响应**: 重定向到登录页面

---

## 系统信息API

### 获取版本信息
- **URL**: `/api/version`
- **方法**: GET
- **描述**: 获取系统版本信息
- **响应**:
  ```json
  {
    "version": "1.0.0",
    "author": "作者名",
    "description": "系统描述"
  }
  ```

### 获取GitHub版本信息
- **URL**: `/api/github-version`
- **方法**: GET
- **描述**: 从GitHub获取最新版本信息
- **响应**:
  ```json
  {
    "version": "1.0.1",
    "author": "作者名",
    "description": "系统描述"
  }
  ```

### 获取系统状态
- **URL**: `/api/status`
- **方法**: GET
- **描述**: 获取系统运行状态
- **响应**:
  ```json
  {
    "status": "running",
    "active_connections": 5,
    "timestamp": 1672531200.0
  }
  ```

### 获取系统资源信息
- **URL**: `/api/system-resources`
- **方法**: GET
- **描述**: 获取详细的系统资源使用情况
- **响应**:
  ```json
  {
    "app_cpu": 15.2,
    "total_cpu": 45.8,
    "app_memory": 128.5,
    "total_memory_gb": 16.0,
    "used_memory_gb": 8.5,
    "available_memory_gb": 7.5,
    "memory_percent": 53.1,
    "disk_total_gb": 500.0,
    "disk_used_gb": 250.0,
    "disk_free_gb": 250.0,
    "disk_percent": 50.0,
    "cpu_cores": 8,
    "cpu_freq_current": 2400,
    "cpu_freq_max": 3200,
    "system_info": "Linux 5.4.0",
    "python_version": "3.9.7",
    "system_uptime_days": 5,
    "system_uptime_hours": 12,
    "app_uptime_hours": 2,
    "app_uptime_minutes": 30
  }
  ```

### 获取数据库状态
- **URL**: `/api/database-status`
- **方法**: GET
- **描述**: 获取数据库状态信息
- **响应**:
  ```json
  {
    "db_size_mb": 125.8,
    "message_count": 50000,
    "retention_days": 30,
    "storage_path": "./data"
  }
  ```

### 获取仪表盘内容
- **URL**: `/api/dashboard-content`
- **方法**: GET
- **描述**: 获取仪表盘Markdown内容
- **响应**:
  ```json
  {
    "content": "# 欢迎使用 BotShepherd\n\n仪表盘内容..."
  }
  ```

---

## 连接管理API

### 获取连接配置列表
- **URL**: `/api/connections`
- **方法**: GET
- **描述**: 获取所有连接配置及其状态
- **响应**:
  ```json
  {
    "connection_1": {
      "name": "连接1",
      "description": "连接描述信息",
      "enabled": true,
      "client_endpoint": "ws://localhost:6100/OneBotv11",
      "target_endpoints": ["ws://localhost:2536/OneBotv11"],
      "status": {
        "enabled": true,
        "client_status": "listening",
        "client_endpoint": "ws://localhost:6100/OneBotv11",
        "target_statuses": {},
        "error": null,
        "client_address": "127.0.0.1:52341",
        "self_id": 1234567890
      }
    }
  }
  ```
- **status字段说明**:
  - `enabled`: 是否启用
  - `client_status`: 客户端连接状态，可选值：
    - `disabled`: 已禁用
    - `starting`: 正在启动
    - `listening`: 监听中（等待客户端连接）
    - `connected`: 已连接（客户端已连接）
    - `error`: 错误状态
  - `client_endpoint`: 客户端端点配置
  - `target_statuses`: 目标端点状态（预留字段）
  - `error`: 错误信息（如果有）
  - `client_address`: 客户端连接地址（如果已连接）
  - `self_id`: Bot账号ID（从WebSocket消息中获取，如果未连接则为null）

### 更新连接配置
- **URL**: `/api/connections/{connection_id}`
- **方法**: PUT
- **描述**: 更新指定连接的配置
- **请求体**:
  ```json
  {
    "name": "更新的连接名",
    "description": "连接描述信息",
    "enabled": true,
    "client_endpoint": "ws://localhost:6100/OneBotv11",
    "target_endpoints": ["ws://localhost:2536/OneBotv11"]
  }
  ```
- **响应**:
  ```json
  {
    "success": true
  }
  ```
- **字段说明**:
  - `name`: 连接名称
  - `description`: 连接描述信息（可选）
  - `enabled`: 是否启用连接
  - `client_endpoint`: 客户端监听端点（WebSocket地址）
  - `target_endpoints`: 目标端点列表（WebSocket地址数组）

### 复制连接配置
- **URL**: `/api/connections/{connection_id}/copy`
- **方法**: POST
- **描述**: 复制现有连接配置
- **请求体**:
  ```json
  {
    "new_id": "new_connection_id",
    "new_name": "连接名称-1"
  }
  ```
  - `new_id`: 必填，新连接的ID
  - `new_name`: 可选，新连接的名称（如果未提供则使用"原名称 - 副本"格式）
- **响应**:
  ```json
  {
    "success": true,
    "message": "连接配置已复制"
  }
  ```

### 删除连接配置
- **URL**: `/api/connections/{connection_id}`
- **方法**: DELETE
- **描述**: 删除指定连接配置
- **响应**:
  ```json
  {
    "success": true
  }
  ```

---

## 账号管理API

### 获取账号配置列表
- **URL**: `/api/accounts`
- **方法**: GET
- **描述**: 获取所有账号配置
- **响应**:
  ```json
  {
    "123456": {
      "name": "机器人名称",
      "description": "账号描述信息",
      "enabled": true,
      "aliases": {
        "#": ["#", "yun"]
      },
      "last_receive_time": "2025-01-10T12:00:00",
      "last_send_time": "2025-01-10T12:05:00"
    }
  }
  ```
- **字段说明**:
  - `name`: 账号名称
  - `description`: 账号描述信息
  - `enabled`: 是否启用
  - `aliases`: 指令别名映射（目标指令 -> 别名列表）
  - `last_receive_time`: 最后接收消息时间
  - `last_send_time`: 最后发送消息时间

### 更新账号配置
- **URL**: `/api/accounts/{account_id}`
- **方法**: PUT
- **描述**: 更新指定账号的配置
- **请求体**:
  ```json
  {
    "name": "新账号名称",
    "description": "账号描述信息",
    "enabled": true,
    "aliases": {
      "#": ["#", "yun"],
      "yz": ["yunzai"]
    }
  }
  ```
- **响应**:
  ```json
  {
    "success": true
  }
  ```
- **字段说明**:
  - `name`: 账号名称
  - `description`: 账号描述信息（可选）
  - `enabled`: 是否启用
  - `aliases`: 指令别名配置，格式为 `{目标指令: [别名列表]}`
- **备注**: 更新后会立即将脏数据写入磁盘

### 删除账号配置
- **URL**: `/api/accounts/{account_id}`
- **方法**: DELETE
- **描述**: 删除指定账号配置
- **响应**:
  ```json
  {
    "success": true
  }
  ```

### 获取最近活跃账号
- **URL**: `/api/recently-active-accounts`
- **方法**: GET
- **描述**: 获取24小时内活跃的账号列表
- **响应**:
  ```json
  [
    {
      "self_id": "123456",
      "nickname": "机器人1",
      "last_activity": 1672531200
    }
  ]
  ```

---

## 群组管理API

### 获取群组配置列表
- **URL**: `/api/groups`
- **方法**: GET
- **描述**: 获取所有群组配置
- **响应**:
  ```json
  {
    "789012": {
      "name": "测试群",
      "enabled": true,
      "auto_reply": false,
      "welcome_message": "欢迎新成员"
    }
  }
  ```

### 更新群组配置
- **URL**: `/api/groups/{group_id}`
- **方法**: PUT
- **描述**: 更新指定群组的配置
- **请求体**:
  ```json
  {
    "name": "新群名",
    "enabled": true,
    "auto_reply": true
  }
  ```
- **响应**:
  ```json
  {
    "success": true
  }
  ```
- **备注**: 更新后会立即将脏数据写入磁盘

### 删除群组配置
- **URL**: `/api/groups/{group_id}`
- **方法**: DELETE
- **描述**: 删除指定群组配置
- **响应**:
  ```json
  {
    "success": true
  }
  ```

### 获取最近活跃群组
- **URL**: `/api/recently-active-groups`
- **方法**: GET
- **描述**: 获取24小时内活跃的群组列表
- **响应**:
  ```json
  [
    {
      "group_id": "789012",
      "name": "测试群",
      "last_activity": 1672531200
    }
  ]
  ```

---

## 全局配置API

### 获取全局配置
- **URL**: `/api/global-config`
- **方法**: GET
- **描述**: 获取系统全局配置
- **响应**:
  ```json
  {
    "web_auth": {
      "username": "admin",
      "password": "admin"
    },
    "database": {
      "auto_expire_days": 30
    },
    "blacklist": {
      "users": ["blacklisted_user"],
      "groups": ["blacklisted_group"]
    }
  }
  ```

### 更新全局配置
- **URL**: `/api/global-config`
- **方法**: PUT
- **描述**: 更新系统全局配置
- **请求体**:
  ```json
  {
    "database": {
      "auto_expire_days": 60
    }
  }
  ```
- **响应**:
  ```json
  {
    "success": true
  }
  ```

---

## 配置写盘API

### 手动刷盘
- **URL**: `/api/config/flush`
- **方法**: POST
- **描述**: 立即将账号/群组的脏配置写入磁盘
- **响应**:
  ```json
  {
    "success": true
  }
  ```

---

## 黑名单管理API

### 获取黑名单
- **URL**: `/api/blacklist`
- **方法**: GET
- **描述**: 获取黑名单配置
- **响应**:
  ```json
  {
    "users": ["user1", "user2"],
    "groups": ["group1", "group2"]
  }
  ```

### 添加黑名单
- **URL**: `/api/blacklist`
- **方法**: POST
- **描述**: 添加用户或群组到黑名单
- **请求体**:
  ```json
  {
    "type": "users",
    "id": "user_id_to_block"
  }
  ```
- **响应**:
  ```json
  {
    "success": true
  }
  ```

### 移除黑名单
- **URL**: `/api/blacklist`
- **方法**: DELETE
- **描述**: 从黑名单移除用户或群组
- **请求体**:
  ```json
  {
    "type": "users",
    "id": "user_id_to_unblock"
  }
  ```
- **响应**:
  ```json
  {
    "success": true
  }
  ```

---

## 统计分析API

### 获取统计数据
- **URL**: `/api/statistics`
- **方法**: GET
- **描述**: 获取消息统计数据
- **查询参数**:
  - `range`: 时间范围 (today/yesterday/week/month/custom)
  - `start_date`: 自定义开始日期 (ISO格式)
  - `end_date`: 自定义结束日期 (ISO格式)
  - `self_id`: 账号ID过滤
  - `direction`: 消息方向 (SEND/RECV)

- **响应**:
  ```json
  {
    "total_messages": 1000,
    "active_users": 50,
    "active_groups": 10,
    "received_messages": 800,
    "messages_change": 100,
    "users_change": 5,
    "groups_change": 1,
    "received_change": 50,
    "hourly_trend": [
      {"time": "2023-01-01 00:00", "count": 10},
      {"time": "2023-01-01 03:00", "count": 15}
    ],
    "top_groups": [
      {
        "group_id": "789012",
        "message_count": 200,
        "active_users": 1
      }
    ]
  }
  ```

### 获取数据库统计
- **URL**: `/api/statistics/database`
- **方法**: GET
- **描述**: 获取数据库详细统计
- **查询参数**:
  - `self_id`: 账号ID过滤
  - `start_time`: 开始时间戳
  - `end_time`: 结束时间戳

- **响应**:
  ```json
  {
    "group_statistics": {
      "group1": 100,
      "group2": 80
    },
    "account_statistics": {
      "123456": 500,
      "789012": 300
    },
    "user_statistics": {
      "user1": 50,
      "user2": 30
    }
  }
  ```

---

## 消息查询API

### 查询消息
- **URL**: `/api/query_messages`
- **方法**: GET
- **描述**: 查询消息记录
- **查询参数**:
  - `self_id`: 账号ID
  - `user_id`: 用户ID
  - `group_id`: 群组ID（特殊值：`__private__` 表示只查询私聊消息，即group_id为None的消息）
  - `start_time`: 开始时间戳
  - `end_time`: 结束时间戳
  - `keywords`: 关键词列表
  - `keyword_type`: 关键词匹配类型 (and/or)
  - `prefix`: 前缀过滤
  - `direction`: 消息方向 (SEND/RECV)
  - `limit`: 返回数量限制 (默认20)
  - `offset`: 偏移量 (默认0)
  - `private_only`: 是否只查询私聊消息（布尔值，与group_id=__private__效果相同）

- **响应**:
  ```json
  {
    "messages": [
      {
        "id": 1,
        "message_id": "msg123",
        "self_id": "123456",
        "user_id": "user123",
        "group_id": "group456",
        "message_type": "text",
        "sub_type": "normal",
        "post_type": "message",
        "raw_message": "原始消息",
        "message_content": "处理后消息",
        "sender_info": {"nickname": "用户昵称"},
        "timestamp": 1672531200,
        "direction": "SEND",
        "connection_id": "conn1"
      }
    ],
    "total_count": 1000,
    "offset": 0,
    "limit": 20
  }
  ```

---

## 日志管理API

### 获取日志文件列表
- **URL**: `/api/logs`
- **方法**: GET
- **描述**: 获取系统日志文件列表
- **响应**:
  ```json
  {
    "files": [
      {
        "name": "main/app.log",
        "display_name": "app.log",
        "size": 1024000,
        "modified": 1672531200.0,
        "is_rotated": false,
        "log_type": "main"
      }
    ]
  }
  ```

### 获取日志文件内容
- **URL**: `/api/logs/{filename}`
- **方法**: GET
- **描述**: 获取指定日志文件的内容
- **查询参数**:
  - `lines`: 显示行数 (默认1000)

- **响应**:
  ```json
  {
    "content": "日志内容...",
    "total_lines": 1000,
    "file_size": 1024000
  }
  ```

---

## 系统控制API

### 重启系统
- **URL**: `/api/system/restart`
- **方法**: POST
- **描述**: 重启整个系统
- **响应**:
  ```json
  {
    "success": true,
    "message": "系统将在2秒后重启"
  }
  ```

---

## 错误响应

所有API在出错时都会返回标准的错误响应格式：

```json
{
  "error": "错误描述信息"
}
```

常见的HTTP状态码：
- `200`: 成功
- `400`: 请求参数错误
- `401`: 未授权（需要登录）
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 注意事项

1. **认证要求**: 所有API都需要先通过Web界面登录认证
2. **异步操作**: 大部分配置更新操作都是异步执行的
3. **配置重载**: 某些配置更改可能需要重启系统才能完全生效
4. **文件安全**: 日志文件访问有路径遍历保护
5. **数据格式**: 时间戳使用Unix时间戳格式
6. **编码**: 所有文本数据使用UTF-8编码
7. **连接状态**: 连接配置的WebSocket服务器启动失败（如端口被占用）不会影响系统启动，状态会通过API返回
8. **私聊查询**: 查询私聊消息时，可使用`group_id=__private__`或`private_only=true`参数

---

## 配置读写规则（内存 vs 文件）

### 读盘会覆盖内存
- `/api/accounts`：先写盘，再从文件重载账号配置，覆盖内存
- `/api/groups`：先写盘，再从文件重载群组配置，覆盖内存
- `/api/connections`：直接从文件重载连接配置，覆盖内存
- `/api/blacklist`：从文件重载全局配置（仅黑名单相关）

### 写盘与内存关系
- `/api/accounts/{account_id}`：先更新内存，再立即写盘
- `/api/groups/{group_id}`：先更新内存，再立即写盘
- `/api/config/flush`：仅写盘（账号/群组脏数据），不重载
- `/api/global-config`：更新内存并立即写盘
- `/api/connections/{connection_id}`：更新内存并立即写盘

### 说明
- 账号/群组配置使用"脏数据"机制，内存更新后可通过定时保存或 `/api/config/flush` 落盘
- 连接/全局配置不使用脏数据机制，修改即写盘

---

## 新功能说明

### 1. 连接状态监控

系统现在实时监控每个连接配置的WebSocket连接状态：

**状态类型**:
- `disabled`: 连接已禁用
- `starting`: 正在启动WebSocket服务器
- `listening`: WebSocket服务器正在监听，等待客户端连接
- `connected`: 客户端已连接到WebSocket服务器
- `error`: 启动或连接过程中发生错误

**错误处理**:
- 当连接配置的端口被占用时，系统不会崩溃，而是将该连接状态标记为`error`
- 错误信息会通过API的`status.error`字段返回
- 其他连接配置不受影响，继续正常运行

**使用场景**:
- 通过`/api/connections` API获取所有连接的实时状态
- 前端界面会以不同颜色徽章显示连接状态
- 详情页面显示完整的连接状态和错误信息

### 2. 私聊消息查询

系统支持查询私聊消息（group_id为None的消息）：

**方法一：使用特殊group_id值**
```
GET /api/query_messages?group_id=__private__
```

**方法二：使用private_only参数**
```
GET /api/query_messages?private_only=true
```

**前端使用**:
在消息查询页面的"群组ID"输入框中输入"私聊"二字，系统会自动将其转换为`__private__`参数。

**注意事项**:
- 私聊消息的`group_id`字段为None或空
- 该查询会返回所有非群组的消息（包括私聊和临时会话）
- 可以与其他查询条件组合使用（如用户ID、时间范围等）

### 3. 连接描述字段

连接配置新增`description`字段用于记录连接的用途和说明：

- 在创建/编辑连接时可以添加描述信息
- 描述字段为可选字段，支持任意文本
- 在连接列表和详情页面都会显示描述信息
- 描述信息会持久化保存到配置文件中

### 4. 前端搜索和排序增强

所有管理页面（账号、群组、连接）现在都支持：

**搜索功能**:
- 账号管理：支持按ID、名称、描述搜索
- 群组管理：支持按群号搜索
- 连接管理：支持按ID、名称、描述搜索

**排序功能**:
- 账号管理：支持按ID、状态、最后接收时间、最后发送时间排序
- 群组管理：支持按群号、最后发送时间、过期时间、过滤词数量、状态排序
- 连接管理：支持按连接ID、名称、启用状态排序

**使用方法**:
- 点击列表表头的排序按钮进行升序/降序切换
- 排序指示器显示当前排序的列（^升序，v降序）
- 在搜索框输入关键词实时过滤结果

---
