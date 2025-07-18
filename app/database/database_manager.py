"""
数据库管理器
负责数据库连接、表创建和数据操作
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import Base, Message, MessageRecord

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
        global_config = self.config_manager.get_global_config()
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
        # 使用SQLAlchemy模型创建表
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def save_message(self, message_data: Dict[str, Any], direction: str, connection_id: str = None):
        """保存消息到数据库"""
        # 只处理MessageEvent和MessageSent类型
        post_type = message_data.get("post_type", "")
        if post_type not in ["message", "message_sent"]:
            return

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

                # 创建消息记录
                message_record = Message(
                    message_id=str(message_id) if message_id else None,
                    self_id=self_id,
                    user_id=user_id,
                    group_id=group_id,
                    message_type=message_type,
                    sub_type=sub_type,
                    post_type=post_type,
                    raw_message=raw_message,
                    message_content=message_content,
                    sender_info=sender_info,
                    timestamp=timestamp,
                    direction=direction,
                    connection_id=connection_id,
                    processed=False
                )

                session.add(message_record)
                await session.commit()

            except Exception as e:
                await session.rollback()
                print(f"保存消息失败: {e}")
                raise
    
    async def query_messages_by_self_id(self, self_id: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]:
        """按self_id查询消息"""
        async with self.session_factory() as session:
            try:
                stmt = select(Message).where(Message.self_id == self_id).order_by(desc(Message.timestamp)).limit(limit).offset(offset)
                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [MessageRecord.from_db_row(msg) for msg in messages]
            except Exception as e:
                print(f"按self_id查询消息失败: {e}")
                return []

    async def query_messages_by_time_range(self, start_time: datetime, end_time: datetime,
                                         limit: int = 100, offset: int = 0) -> List[MessageRecord]:
        """按时间段查询消息"""
        async with self.session_factory() as session:
            try:
                stmt = select(Message).where(
                    and_(Message.timestamp >= start_time, Message.timestamp <= end_time)
                ).order_by(desc(Message.timestamp)).limit(limit).offset(offset)
                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [MessageRecord.from_db_row(msg) for msg in messages]
            except Exception as e:
                print(f"按时间段查询消息失败: {e}")
                return []

    async def query_messages_by_user_id(self, user_id: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]:
        """按用户ID查询消息"""
        async with self.session_factory() as session:
            try:
                stmt = select(Message).where(Message.user_id == user_id).order_by(desc(Message.timestamp)).limit(limit).offset(offset)
                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [MessageRecord.from_db_row(msg) for msg in messages]
            except Exception as e:
                print(f"按用户ID查询消息失败: {e}")
                return []

    async def query_messages_by_group_id(self, group_id: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]:
        """按群聊ID查询消息"""
        async with self.session_factory() as session:
            try:
                stmt = select(Message).where(Message.group_id == group_id).order_by(desc(Message.timestamp)).limit(limit).offset(offset)
                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [MessageRecord.from_db_row(msg) for msg in messages]
            except Exception as e:
                print(f"按群聊ID查询消息失败: {e}")
                return []

    async def query_messages_by_keyword(self, keyword: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]:
        """查询包含关键字的消息（从raw_message中搜索）"""
        async with self.session_factory() as session:
            try:
                stmt = select(Message).where(
                    or_(
                        Message.raw_message.contains(keyword),
                        Message.message_content.contains(keyword)
                    )
                ).order_by(desc(Message.timestamp)).limit(limit).offset(offset)
                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [MessageRecord.from_db_row(msg) for msg in messages]
            except Exception as e:
                print(f"按关键字查询消息失败: {e}")
                return []

    async def query_messages_by_startswith(self, prefix: str, limit: int = 100, offset: int = 0) -> List[MessageRecord]:
        """查询以指定词开头的消息"""
        async with self.session_factory() as session:
            try:
                stmt = select(Message).where(
                    or_(
                        Message.raw_message.startswith(prefix),
                        Message.message_content.startswith(prefix)
                    )
                ).order_by(desc(Message.timestamp)).limit(limit).offset(offset)
                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [MessageRecord.from_db_row(msg) for msg in messages]
            except Exception as e:
                print(f"按开头词查询消息失败: {e}")
                return []

    async def query_messages_combined(self,
                                    self_id: str = None,
                                    user_id: str = None,
                                    group_id: str = None,
                                    start_time: datetime = None,
                                    end_time: datetime = None,
                                    keyword: str = None,
                                    prefix: str = None,
                                    limit: int = 100,
                                    offset: int = 0) -> List[MessageRecord]:
        """组合查询消息"""
        async with self.session_factory() as session:
            try:
                conditions = []

                if self_id:
                    conditions.append(Message.self_id == self_id)
                if user_id:
                    conditions.append(Message.user_id == user_id)
                if group_id:
                    conditions.append(Message.group_id == group_id)
                if start_time:
                    conditions.append(Message.timestamp >= start_time)
                if end_time:
                    conditions.append(Message.timestamp <= end_time)
                if keyword:
                    conditions.append(
                        or_(
                            Message.raw_message.contains(keyword),
                            Message.message_content.contains(keyword)
                        )
                    )
                if prefix:
                    conditions.append(
                        or_(
                            Message.raw_message.startswith(prefix),
                            Message.message_content.startswith(prefix)
                        )
                    )

                stmt = select(Message)
                if conditions:
                    stmt = stmt.where(and_(*conditions))
                stmt = stmt.order_by(desc(Message.timestamp)).limit(limit).offset(offset)

                result = await session.execute(stmt)
                messages = result.scalars().all()
                return [MessageRecord.from_db_row(msg) for msg in messages]
            except Exception as e:
                print(f"组合查询消息失败: {e}")
                return []

    async def count_messages(self,
                           self_id: str = None,
                           user_id: str = None,
                           group_id: str = None,
                           start_time: datetime = None,
                           end_time: datetime = None,
                           keyword: str = None,
                           prefix: str = None) -> int:
        """统计消息数量"""
        async with self.session_factory() as session:
            try:
                conditions = []

                if self_id:
                    conditions.append(Message.self_id == self_id)
                if user_id:
                    conditions.append(Message.user_id == user_id)
                if group_id:
                    conditions.append(Message.group_id == group_id)
                if start_time:
                    conditions.append(Message.timestamp >= start_time)
                if end_time:
                    conditions.append(Message.timestamp <= end_time)
                if keyword:
                    conditions.append(
                        or_(
                            Message.raw_message.contains(keyword),
                            Message.message_content.contains(keyword)
                        )
                    )
                if prefix:
                    conditions.append(
                        or_(
                            Message.raw_message.startswith(prefix),
                            Message.message_content.startswith(prefix)
                        )
                    )

                stmt = select(func.count(Message.id))
                if conditions:
                    stmt = stmt.where(and_(*conditions))

                result = await session.execute(stmt)
                return result.scalar() or 0
            except Exception as e:
                print(f"统计消息数量失败: {e}")
                return 0


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
                # 查询要删除的消息数量
                count_stmt = select(func.count(Message.id)).where(Message.timestamp < cutoff_date)
                result = await session.execute(count_stmt)
                deleted_count = result.scalar() or 0

                # 删除过期消息
                if deleted_count > 0:
                    delete_stmt = select(Message).where(Message.timestamp < cutoff_date)
                    result = await session.execute(delete_stmt)
                    messages_to_delete = result.scalars().all()

                    for message in messages_to_delete:
                        session.delete(message)

                await session.commit()

                if deleted_count > 0:
                    print(f"清理了 {deleted_count} 条过期消息记录")

            except Exception as e:
                await session.rollback()
                print(f"数据清理失败: {e}")


    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
