# BotShepherd 数据库 API 文档

## 概述

BotShepherd 的数据库管理器已经重构为使用 Python 接口而不是直接使用 SQL execute。新的实现专注于消息记录和查询功能，支持 MessageEvent 和 MessageSent 类型的消息。

## 主要特性

- **Python 接口**: 使用 SQLAlchemy ORM 而不是原始 SQL
- **消息记录类**: 返回 `MessageRecord` 对象，方便在 Python 中使用
- **专注消息**: 只记录和查询消息，不记录群组和用户信息
- **多种查询方式**: 支持按 self_id、时间段、用户ID、群聊ID、关键字、开头词查询
- **组合查询**: 支持多条件组合查询
- **数据清理**: 自动清理过期消息

## MessageRecord 类

```python
@dataclass
class MessageRecord:
    id: int                          # 数据库主键
    message_id: Optional[str]        # OneBot 消息ID
    self_id: str                     # 机器人ID
    user_id: Optional[str]           # 用户ID
    group_id: Optional[str]          # 群聊ID
    message_type: str                # 消息类型 (private/group)
    sub_type: Optional[str]          # 子类型
    post_type: str                   # 事件类型 (message/message_sent)
    raw_message: str                 # 原始消息内容
    message_content: str             # 提取的文本内容
    sender_info: Dict[str, Any]      # 发送者信息 (JSON)
    timestamp: datetime              # 消息时间戳
    direction: str                   # 方向 (RECV/SEND)
    connection_id: Optional[str]     # 连接ID
    processed: bool                  # 是否已处理
    created_at: datetime             # 创建时间
```

## API 方法

### 消息保存

```python
async def save_message(self, message_data: Dict[str, Any], direction: str, connection_id: str = None)
```

保存消息到数据库。只处理 `post_type` 为 `message` 或 `message_sent` 的消息。

### 查询方法

#### 1. 按 self_id 查询

```python
async def query_messages_by_self_id(self, self_id: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]
```

查询指定机器人的消息。

#### 2. 按时间段查询

```python
async def query_messages_by_time_range(self, start_time: datetime, end_time: datetime, 
                                     limit: int = 100, offset: int = 0) -> List[MessageRecord]
```

查询指定时间段内的消息。

#### 3. 按用户ID查询

```python
async def query_messages_by_user_id(self, user_id: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]
```

查询指定用户的消息。

#### 4. 按群聊ID查询

```python
async def query_messages_by_group_id(self, group_id: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]
```

查询指定群聊的消息。

#### 5. 关键字搜索

```python
async def query_messages_by_keyword(self, keyword: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]
```

搜索包含指定关键字的消息。会在 `raw_message` 和 `message_content` 中搜索。

#### 6. 开头词搜索

```python
async def query_messages_by_startswith(self, prefix: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]
```

搜索以指定词开头的消息。会在 `raw_message` 和 `message_content` 中搜索。

#### 7. 组合查询

```python
async def query_messages_combined(self, 
                                self_id: str = None,
                                user_id: str = None,
                                group_id: str = None,
                                start_time: datetime = None,
                                end_time: datetime = None,
                                keyword: str = None,
                                prefix: str = None,
                                limit: int = 100,
                                offset: int = 0) -> List[MessageRecord]
```

支持多条件组合查询。

#### 8. 消息计数

```python
async def count_messages(self, 
                       self_id: str = None,
                       user_id: str = None,
                       group_id: str = None,
                       start_time: datetime = None,
                       end_time: datetime = None,
                       keyword: str = None,
                       prefix: str = None) -> int
```

统计符合条件的消息数量。

## 使用示例

```python
import asyncio
from datetime import datetime, timedelta
from app.database.database_manager import DatabaseManager
from app.config.config_manager import ConfigManager

async def example():
    # 初始化
    config_manager = ConfigManager()
    await config_manager.initialize()
    
    db_manager = DatabaseManager(config_manager)
    await db_manager.initialize()
    
    # 查询最近24小时的消息
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    messages = await db_manager.query_messages_by_time_range(start_time, end_time, limit=10)
    
    # 搜索包含关键字的消息
    keyword_messages = await db_manager.query_messages_by_keyword("测试", limit=5)
    
    # 组合查询：特定用户在特定群聊中的消息
    combined_messages = await db_manager.query_messages_combined(
        user_id="123456",
        group_id="789012",
        keyword="hello",
        limit=10
    )
    
    # 统计消息数量
    total_count = await db_manager.count_messages()
    keyword_count = await db_manager.count_messages(keyword="测试")
    
    # 关闭连接
    await db_manager.close()

# 运行示例
asyncio.run(example())
```

## 数据清理

数据库管理器会自动启动清理任务，根据配置中的 `auto_expire_days` 设置（默认30天）清理过期消息。

## 注意事项

1. 所有查询方法都返回 `MessageRecord` 对象列表
2. 查询结果按时间戳降序排列（最新的在前）
3. 支持分页查询（limit 和 offset 参数）
4. 关键字和开头词搜索会同时在原始消息和提取的文本内容中搜索
5. 只记录 MessageEvent 和 MessageSent 类型的消息
6. 数据库使用 SQLite，支持并发读取

## 迁移说明

如果你之前使用旧的数据库接口，需要注意：

1. 不再有 `get_message_statistics`、`get_user_statistics` 等统计方法
2. 不再记录用户和群组信息
3. 查询方法返回 `MessageRecord` 对象而不是字典
4. 使用 SQLAlchemy ORM 而不是原始 SQL

详细的使用示例请参考 `example_database_usage.py` 文件。
