"""
数据库管理器
负责数据库连接、表创建和数据操作
"""

import asyncio
import aiosqlite
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.db_config = None
        self.engine = None
        self.session_factory = None
        self.db_path = None
        
    async def initialize(self):
        """初始化数据库"""
        # 获取数据库配置
        global_config = await self.config_manager.get_global_config()
        self.db_config = global_config.get("database", {})
        
        # 创建数据目录
        data_path = Path(self.db_config.get("data_path", "./data"))
        data_path.mkdir(exist_ok=True)
        
        # 设置数据库路径
        self.db_path = data_path / "botshepherd.db"
        
        # 创建异步数据库引擎
        db_url = f"sqlite+aiosqlite:///{self.db_path}"
        self.engine = create_async_engine(db_url, echo=False)
        
        # 创建会话工厂
        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # 创建数据表
        await self._create_tables()
        
        # 启动数据清理任务
        asyncio.create_task(self._start_cleanup_task())
    
    async def _create_tables(self):
        """创建数据表"""
        async with self.engine.begin() as conn:
            # 消息表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT,
                    self_id TEXT NOT NULL,
                    user_id TEXT,
                    group_id TEXT,
                    message_type TEXT NOT NULL,
                    sub_type TEXT,
                    post_type TEXT,
                    raw_message TEXT,
                    message_content TEXT,
                    sender_info TEXT,
                    timestamp DATETIME NOT NULL,
                    direction TEXT NOT NULL,
                    connection_id TEXT,
                    processed BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 用户表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    nickname TEXT,
                    card TEXT,
                    role TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """))
            
            # 群组表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id TEXT PRIMARY KEY,
                    group_name TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_message_time DATETIME,
                    message_count INTEGER DEFAULT 0,
                    member_count INTEGER DEFAULT 0
                )
            """))
            
            # 统计表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    self_id TEXT NOT NULL,
                    group_id TEXT,
                    message_count INTEGER DEFAULT 0,
                    command_count INTEGER DEFAULT 0,
                    user_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, self_id, group_id)
                )
            """))
            
            # API调用记录表
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS api_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    self_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    params TEXT,
                    result TEXT,
                    success BOOLEAN,
                    timestamp DATETIME NOT NULL,
                    response_time REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # 创建索引
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_self_id ON messages(self_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_group_id ON messages(group_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_statistics_date ON statistics(date)"))
    
    async def save_message(self, message_data: Dict[str, Any], direction: str, connection_id: str = None):
        """保存消息到数据库"""
        async with self.session_factory() as session:
            try:
                # 提取消息信息
                message_id = message_data.get("message_id")
                self_id = str(message_data.get("self_id", ""))
                user_id = str(message_data.get("user_id", "")) if message_data.get("user_id") else None
                group_id = str(message_data.get("group_id", "")) if message_data.get("group_id") else None
                message_type = message_data.get("message_type", "unknown")
                sub_type = message_data.get("sub_type")
                post_type = message_data.get("post_type", "message")
                raw_message = message_data.get("raw_message", "")
                
                # 处理消息内容
                message_content = ""
                if "message" in message_data:
                    if isinstance(message_data["message"], list):
                        # 提取文本内容
                        text_parts = []
                        for msg_part in message_data["message"]:
                            if msg_part.get("type") == "text":
                                text_parts.append(msg_part.get("data", {}).get("text", ""))
                        message_content = "".join(text_parts)
                    else:
                        message_content = str(message_data["message"])
                
                # 发送者信息
                sender_info = json.dumps(message_data.get("sender", {}), ensure_ascii=False)
                
                # 时间戳
                timestamp = datetime.fromtimestamp(message_data.get("time", datetime.now().timestamp()))
                
                # 插入消息记录
                await session.execute(text("""
                    INSERT INTO messages (
                        message_id, self_id, user_id, group_id, message_type, sub_type,
                        post_type, raw_message, message_content, sender_info, timestamp,
                        direction, connection_id
                    ) VALUES (
                        :message_id, :self_id, :user_id, :group_id, :message_type, :sub_type,
                        :post_type, :raw_message, :message_content, :sender_info, :timestamp,
                        :direction, :connection_id
                    )
                """), {
                    "message_id": message_id,
                    "self_id": self_id,
                    "user_id": user_id,
                    "group_id": group_id,
                    "message_type": message_type,
                    "sub_type": sub_type,
                    "post_type": post_type,
                    "raw_message": raw_message,
                    "message_content": message_content,
                    "sender_info": sender_info,
                    "timestamp": timestamp,
                    "direction": direction,
                    "connection_id": connection_id
                })
                
                # 更新用户信息
                if user_id and "sender" in message_data:
                    sender = message_data["sender"]
                    await session.execute(text("""
                        INSERT OR REPLACE INTO users (
                            user_id, nickname, card, role, last_seen, message_count
                        ) VALUES (
                            :user_id, :nickname, :card, :role, :last_seen,
                            COALESCE((SELECT message_count FROM users WHERE user_id = :user_id), 0) + 1
                        )
                    """), {
                        "user_id": user_id,
                        "nickname": sender.get("nickname", ""),
                        "card": sender.get("card", ""),
                        "role": sender.get("role", "member"),
                        "last_seen": timestamp
                    })
                
                # 更新群组信息
                if group_id:
                    await session.execute(text("""
                        INSERT OR REPLACE INTO groups (
                            group_id, last_message_time, message_count
                        ) VALUES (
                            :group_id, :last_message_time,
                            COALESCE((SELECT message_count FROM groups WHERE group_id = :group_id), 0) + 1
                        )
                    """), {
                        "group_id": group_id,
                        "last_message_time": timestamp
                    })
                
                # 更新统计信息
                date_str = timestamp.strftime("%Y-%m-%d")
                await session.execute(text("""
                    INSERT OR REPLACE INTO statistics (
                        date, self_id, group_id, message_count, user_count
                    ) VALUES (
                        :date, :self_id, :group_id,
                        COALESCE((SELECT message_count FROM statistics WHERE date = :date AND self_id = :self_id AND group_id IS :group_id), 0) + 1,
                        COALESCE((SELECT user_count FROM statistics WHERE date = :date AND self_id = :self_id AND group_id IS :group_id), 0)
                    )
                """), {
                    "date": date_str,
                    "self_id": self_id,
                    "group_id": group_id
                })
                
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                print(f"保存消息失败: {e}")
                raise
    
    async def get_message_statistics(self, 
                                   date: str = None, 
                                   self_id: str = None, 
                                   group_id: str = None,
                                   keyword: str = None,
                                   command_prefix: str = None) -> Dict[str, Any]:
        """获取消息统计"""
        async with self.session_factory() as session:
            try:
                # 构建查询条件
                conditions = []
                params = {}
                
                if date:
                    if date == "today":
                        date = datetime.now().strftime("%Y-%m-%d")
                    conditions.append("DATE(timestamp) = :date")
                    params["date"] = date
                
                if self_id:
                    conditions.append("self_id = :self_id")
                    params["self_id"] = self_id
                
                if group_id:
                    conditions.append("group_id = :group_id")
                    params["group_id"] = group_id
                
                if keyword:
                    conditions.append("message_content LIKE :keyword")
                    params["keyword"] = f"%{keyword}%"
                
                if command_prefix:
                    conditions.append("message_content LIKE :command_prefix")
                    params["command_prefix"] = f"{command_prefix}%"
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                
                # 查询消息统计
                result = await session.execute(text(f"""
                    SELECT 
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT group_id) as unique_groups,
                        COUNT(DISTINCT self_id) as unique_bots
                    FROM messages 
                    WHERE {where_clause}
                """), params)
                
                stats = result.fetchone()
                
                return {
                    "total_messages": stats[0] if stats else 0,
                    "unique_users": stats[1] if stats else 0,
                    "unique_groups": stats[2] if stats else 0,
                    "unique_bots": stats[3] if stats else 0,
                    "query_params": {
                        "date": date,
                        "self_id": self_id,
                        "group_id": group_id,
                        "keyword": keyword,
                        "command_prefix": command_prefix
                    }
                }
                
            except Exception as e:
                print(f"查询统计失败: {e}")
                return {
                    "total_messages": 0,
                    "unique_users": 0,
                    "unique_groups": 0,
                    "unique_bots": 0,
                    "error": str(e)
                }

    async def get_message_history(self,
                                self_id: str = None,
                                user_id: str = None,
                                group_id: str = None,
                                limit: int = 100,
                                offset: int = 0,
                                start_time: datetime = None,
                                end_time: datetime = None) -> List[Dict[str, Any]]:
        """获取消息历史"""
        async with self.session_factory() as session:
            try:
                conditions = []
                params = {}

                if self_id:
                    conditions.append("self_id = :self_id")
                    params["self_id"] = self_id

                if user_id:
                    conditions.append("user_id = :user_id")
                    params["user_id"] = user_id

                if group_id:
                    conditions.append("group_id = :group_id")
                    params["group_id"] = group_id

                if start_time:
                    conditions.append("timestamp >= :start_time")
                    params["start_time"] = start_time

                if end_time:
                    conditions.append("timestamp <= :end_time")
                    params["end_time"] = end_time

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                result = await session.execute(text(f"""
                    SELECT
                        id, message_id, self_id, user_id, group_id,
                        message_type, sub_type, post_type, raw_message,
                        message_content, sender_info, timestamp, direction
                    FROM messages
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT :limit OFFSET :offset
                """), {**params, "limit": limit, "offset": offset})

                messages = []
                for row in result.fetchall():
                    message = {
                        "id": row[0],
                        "message_id": row[1],
                        "self_id": row[2],
                        "user_id": row[3],
                        "group_id": row[4],
                        "message_type": row[5],
                        "sub_type": row[6],
                        "post_type": row[7],
                        "raw_message": row[8],
                        "message_content": row[9],
                        "sender_info": json.loads(row[10]) if row[10] else {},
                        "timestamp": row[11],
                        "direction": row[12]
                    }
                    messages.append(message)

                return messages

            except Exception as e:
                print(f"查询消息历史失败: {e}")
                return []

    async def get_user_statistics(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """获取用户统计信息"""
        async with self.session_factory() as session:
            try:
                start_date = datetime.now() - timedelta(days=days)

                # 消息统计
                result = await session.execute(text("""
                    SELECT
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT group_id) as active_groups,
                        COUNT(DISTINCT DATE(timestamp)) as active_days
                    FROM messages
                    WHERE user_id = :user_id AND timestamp >= :start_date
                """), {"user_id": user_id, "start_date": start_date})

                stats = result.fetchone()

                # 每日消息统计
                daily_result = await session.execute(text("""
                    SELECT
                        DATE(timestamp) as date,
                        COUNT(*) as message_count
                    FROM messages
                    WHERE user_id = :user_id AND timestamp >= :start_date
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """), {"user_id": user_id, "start_date": start_date})

                daily_stats = []
                for row in daily_result.fetchall():
                    daily_stats.append({
                        "date": row[0],
                        "message_count": row[1]
                    })

                return {
                    "user_id": user_id,
                    "total_messages": stats[0] if stats else 0,
                    "active_groups": stats[1] if stats else 0,
                    "active_days": stats[2] if stats else 0,
                    "daily_stats": daily_stats
                }

            except Exception as e:
                print(f"查询用户统计失败: {e}")
                return {
                    "user_id": user_id,
                    "total_messages": 0,
                    "active_groups": 0,
                    "active_days": 0,
                    "daily_stats": []
                }

    async def get_group_statistics(self, group_id: str, days: int = 7) -> Dict[str, Any]:
        """获取群组统计信息"""
        async with self.session_factory() as session:
            try:
                start_date = datetime.now() - timedelta(days=days)

                # 群组基本统计
                result = await session.execute(text("""
                    SELECT
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT user_id) as active_users,
                        COUNT(DISTINCT DATE(timestamp)) as active_days
                    FROM messages
                    WHERE group_id = :group_id AND timestamp >= :start_date
                """), {"group_id": group_id, "start_date": start_date})

                stats = result.fetchone()

                # 用户活跃度统计
                user_result = await session.execute(text("""
                    SELECT
                        user_id,
                        COUNT(*) as message_count,
                        MAX(timestamp) as last_message_time
                    FROM messages
                    WHERE group_id = :group_id AND timestamp >= :start_date
                    GROUP BY user_id
                    ORDER BY message_count DESC
                    LIMIT 10
                """), {"group_id": group_id, "start_date": start_date})

                user_stats = []
                for row in user_result.fetchall():
                    user_stats.append({
                        "user_id": row[0],
                        "message_count": row[1],
                        "last_message_time": row[2]
                    })

                return {
                    "group_id": group_id,
                    "total_messages": stats[0] if stats else 0,
                    "active_users": stats[1] if stats else 0,
                    "active_days": stats[2] if stats else 0,
                    "top_users": user_stats
                }

            except Exception as e:
                print(f"查询群组统计失败: {e}")
                return {
                    "group_id": group_id,
                    "total_messages": 0,
                    "active_users": 0,
                    "active_days": 0,
                    "top_users": []
                }

    async def search_messages(self,
                            keyword: str,
                            self_id: str = None,
                            user_id: str = None,
                            group_id: str = None,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """搜索消息"""
        async with self.session_factory() as session:
            try:
                conditions = ["message_content LIKE :keyword"]
                params = {"keyword": f"%{keyword}%"}

                if self_id:
                    conditions.append("self_id = :self_id")
                    params["self_id"] = self_id

                if user_id:
                    conditions.append("user_id = :user_id")
                    params["user_id"] = user_id

                if group_id:
                    conditions.append("group_id = :group_id")
                    params["group_id"] = group_id

                where_clause = " AND ".join(conditions)

                result = await session.execute(text(f"""
                    SELECT
                        id, message_id, self_id, user_id, group_id,
                        message_type, raw_message, message_content,
                        timestamp, direction
                    FROM messages
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """), {**params, "limit": limit})

                messages = []
                for row in result.fetchall():
                    message = {
                        "id": row[0],
                        "message_id": row[1],
                        "self_id": row[2],
                        "user_id": row[3],
                        "group_id": row[4],
                        "message_type": row[5],
                        "raw_message": row[6],
                        "message_content": row[7],
                        "timestamp": row[8],
                        "direction": row[9]
                    }
                    messages.append(message)

                return messages

            except Exception as e:
                print(f"搜索消息失败: {e}")
                return []

    async def _start_cleanup_task(self):
        """启动数据清理任务"""
        while True:
            try:
                await self._cleanup_expired_data()
                # 每天清理一次
                await asyncio.sleep(24 * 60 * 60)
            except Exception as e:
                print(f"数据清理任务错误: {e}")
                await asyncio.sleep(60 * 60)  # 出错后1小时重试
    
    async def _cleanup_expired_data(self):
        """清理过期数据"""
        expire_days = self.db_config.get("auto_expire_days", 30)
        cutoff_date = datetime.now() - timedelta(days=expire_days)
        
        async with self.session_factory() as session:
            try:
                # 删除过期消息
                result = await session.execute(text("""
                    DELETE FROM messages WHERE timestamp < :cutoff_date
                """), {"cutoff_date": cutoff_date})
                
                deleted_count = result.rowcount
                
                # 删除过期API调用记录
                await session.execute(text("""
                    DELETE FROM api_calls WHERE timestamp < :cutoff_date
                """), {"cutoff_date": cutoff_date})
                
                await session.commit()
                
                if deleted_count > 0:
                    print(f"清理了 {deleted_count} 条过期消息记录")
                
            except Exception as e:
                await session.rollback()
                print(f"数据清理失败: {e}")

    async def save_api_call(self, self_id: str, action: str, params: Dict[str, Any],
                          result: Dict[str, Any] = None, success: bool = True,
                          response_time: float = None):
        """保存API调用记录"""
        async with self.session_factory() as session:
            try:
                await session.execute(text("""
                    INSERT INTO api_calls (
                        self_id, action, params, result, success,
                        timestamp, response_time
                    ) VALUES (
                        :self_id, :action, :params, :result, :success,
                        :timestamp, :response_time
                    )
                """), {
                    "self_id": self_id,
                    "action": action,
                    "params": json.dumps(params, ensure_ascii=False),
                    "result": json.dumps(result, ensure_ascii=False) if result else None,
                    "success": success,
                    "timestamp": datetime.now(),
                    "response_time": response_time
                })

                await session.commit()

            except Exception as e:
                await session.rollback()
                print(f"保存API调用记录失败: {e}")

    async def get_api_statistics(self, self_id: str = None, days: int = 7) -> Dict[str, Any]:
        """获取API调用统计"""
        async with self.session_factory() as session:
            try:
                start_date = datetime.now() - timedelta(days=days)
                conditions = ["timestamp >= :start_date"]
                params = {"start_date": start_date}

                if self_id:
                    conditions.append("self_id = :self_id")
                    params["self_id"] = self_id

                where_clause = " AND ".join(conditions)

                # 基本统计
                result = await session.execute(text(f"""
                    SELECT
                        COUNT(*) as total_calls,
                        COUNT(CASE WHEN success = 1 THEN 1 END) as success_calls,
                        AVG(response_time) as avg_response_time
                    FROM api_calls
                    WHERE {where_clause}
                """), params)

                stats = result.fetchone()

                # 按动作统计
                action_result = await session.execute(text(f"""
                    SELECT
                        action,
                        COUNT(*) as call_count,
                        COUNT(CASE WHEN success = 1 THEN 1 END) as success_count,
                        AVG(response_time) as avg_response_time
                    FROM api_calls
                    WHERE {where_clause}
                    GROUP BY action
                    ORDER BY call_count DESC
                """), params)

                action_stats = []
                for row in action_result.fetchall():
                    action_stats.append({
                        "action": row[0],
                        "call_count": row[1],
                        "success_count": row[2],
                        "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                        "avg_response_time": row[3]
                    })

                return {
                    "total_calls": stats[0] if stats else 0,
                    "success_calls": stats[1] if stats else 0,
                    "success_rate": stats[1] / stats[0] if stats and stats[0] > 0 else 0,
                    "avg_response_time": stats[2] if stats else 0,
                    "action_stats": action_stats
                }

            except Exception as e:
                print(f"查询API统计失败: {e}")
                return {
                    "total_calls": 0,
                    "success_calls": 0,
                    "success_rate": 0,
                    "avg_response_time": 0,
                    "action_stats": []
                }

    async def get_hourly_message_stats(self, date: str = None, self_id: str = None) -> List[Dict[str, Any]]:
        """获取小时级消息统计"""
        async with self.session_factory() as session:
            try:
                if date is None:
                    date = datetime.now().strftime("%Y-%m-%d")

                conditions = ["DATE(timestamp) = :date"]
                params = {"date": date}

                if self_id:
                    conditions.append("self_id = :self_id")
                    params["self_id"] = self_id

                where_clause = " AND ".join(conditions)

                result = await session.execute(text(f"""
                    SELECT
                        strftime('%H', timestamp) as hour,
                        COUNT(*) as message_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT group_id) as unique_groups
                    FROM messages
                    WHERE {where_clause}
                    GROUP BY strftime('%H', timestamp)
                    ORDER BY hour
                """), params)

                hourly_stats = []
                for row in result.fetchall():
                    hourly_stats.append({
                        "hour": int(row[0]) if row[0] else 0,
                        "message_count": row[1],
                        "unique_users": row[2],
                        "unique_groups": row[3]
                    })

                # 填充缺失的小时数据
                hour_dict = {stat["hour"]: stat for stat in hourly_stats}
                complete_stats = []
                for hour in range(24):
                    if hour in hour_dict:
                        complete_stats.append(hour_dict[hour])
                    else:
                        complete_stats.append({
                            "hour": hour,
                            "message_count": 0,
                            "unique_users": 0,
                            "unique_groups": 0
                        })

                return complete_stats

            except Exception as e:
                print(f"查询小时统计失败: {e}")
                return []

    async def get_command_statistics(self, command_prefix: str, days: int = 7,
                                   self_id: str = None) -> List[Dict[str, Any]]:
        """获取指令使用统计"""
        async with self.session_factory() as session:
            try:
                start_date = datetime.now() - timedelta(days=days)
                conditions = [
                    "timestamp >= :start_date",
                    "message_content LIKE :command_pattern"
                ]
                params = {
                    "start_date": start_date,
                    "command_pattern": f"{command_prefix}%"
                }

                if self_id:
                    conditions.append("self_id = :self_id")
                    params["self_id"] = self_id

                where_clause = " AND ".join(conditions)

                result = await session.execute(text(f"""
                    SELECT
                        CASE
                            WHEN instr(message_content, ' ') > 0
                            THEN substr(message_content, 1, instr(message_content, ' ') - 1)
                            ELSE message_content
                        END as command,
                        COUNT(*) as usage_count,
                        COUNT(DISTINCT user_id) as unique_users,
                        COUNT(DISTINCT group_id) as unique_groups
                    FROM messages
                    WHERE {where_clause}
                    GROUP BY command
                    ORDER BY usage_count DESC
                    LIMIT 20
                """), params)

                command_stats = []
                for row in result.fetchall():
                    command_stats.append({
                        "command": row[0],
                        "usage_count": row[1],
                        "unique_users": row[2],
                        "unique_groups": row[3]
                    })

                return command_stats

            except Exception as e:
                print(f"查询指令统计失败: {e}")
                return []

    async def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        async with self.session_factory() as session:
            try:
                # 表大小统计
                tables_info = []
                table_names = ["messages", "users", "groups", "statistics", "api_calls"]

                for table_name in table_names:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.fetchone()[0]
                    tables_info.append({
                        "table_name": table_name,
                        "row_count": count
                    })

                # 数据库文件大小
                db_size = 0
                if self.db_path and self.db_path.exists():
                    db_size = self.db_path.stat().st_size

                # 最早和最新消息时间
                result = await session.execute(text("""
                    SELECT MIN(timestamp), MAX(timestamp) FROM messages
                """))
                time_range = result.fetchone()

                return {
                    "database_path": str(self.db_path),
                    "database_size": db_size,
                    "tables": tables_info,
                    "earliest_message": time_range[0] if time_range[0] else None,
                    "latest_message": time_range[1] if time_range[1] else None,
                    "auto_expire_days": self.db_config.get("auto_expire_days", 30)
                }

            except Exception as e:
                print(f"获取数据库信息失败: {e}")
                return {
                    "database_path": str(self.db_path) if self.db_path else None,
                    "database_size": 0,
                    "tables": [],
                    "earliest_message": None,
                    "latest_message": None,
                    "auto_expire_days": 30
                }

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
