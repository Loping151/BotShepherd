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
            
    async def get_total_message_count(self) -> int:
        """获取数据库中消息总数"""
        async with self.session_factory() as session:
            try:
                stmt = select(func.count(Message.id))
                result = await session.execute(stmt)
                return result.scalar() or 0
            except Exception as e:
                print(f"获取消息总数失败: {e}")
                return 0

    def get_database_size(self) -> int:
        """获取数据库文件大小（单位：字节）"""
        try:
            if self.db_path and self.db_path.exists():
                return self.db_path.stat().st_size
            else:
                print("数据库文件不存在")
                return 0
        except Exception as e:
            print(f"获取数据库大小失败: {e}")
            return 0
    
    async def save_message(self, message_data: Dict[str, Any], direction: str, connection_id: str = None):
        """保存消息到数据库"""
        # 只处理MessageEvent和MessageSent类型
        post_type = message_data.get("post_type", "")
        if post_type not in ["message", "message_sent"]:
            return

        async with self.session_factory() as session:
            try:
                message_id = message_data.get("message_id")
                self_id = str(message_data.get("self_id", ""))
                user_id = str(message_data.get("user_id", "")) if message_data.get("user_id") else None
                if direction == "RECV":
                    # 提取消息信息
                    if user_id == self_id:
                        return # 不纪录自身上报的消息
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
                            elif msg_part.get("type") == "at":
                                text_parts.append(f"@{msg_part.get('data', {}).get('qq', '')}")
                                if str(msg_part.get("data", {}).get("qq")) == self_id:
                                    text_parts.append(f"[at BS Bot]")
                        message_content = "".join(text_parts)
                    else:
                        message_content = str(message_data["message"])

                # 发送者信息
                sender_info = json.dumps(message_data.get("sender", {}), ensure_ascii=False)

                # 时间戳
                timestamp = int(message_data.get("time", datetime.now().timestamp()))

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
            
    def _build_message_conditions(self,
                                self_id: Optional[str] = None,
                                user_id: Optional[str] = None,
                                group_id: Optional[str] = None,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None,
                                keywords: Optional[List[str]] = None,
                                keyword_type: str = "and",
                                prefix: Optional[str] = None,
                                direction: Optional[str] = "SEND") -> List[Any]:
        """构建通用的查询条件"""
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
        if direction:
            conditions.append(Message.direction == direction)
        
        if keywords:
            keyword_conditions = [
                or_(
                    Message.raw_message.contains(kw),
                    Message.message_content.contains(kw)
                ) for kw in keywords
            ]
            if keyword_type == "or":
                conditions.append(or_(*keyword_conditions))
            else:
                conditions.append(and_(*keyword_conditions))

        if prefix:
            prefix_condition = or_(
                Message.raw_message.startswith(prefix),
                Message.message_content.startswith(prefix)
            )
            conditions.append(prefix_condition)

        return conditions


    async def query_messages_combined(self,
                                    self_id: str = None,
                                    user_id: str = None,
                                    group_id: str = None,
                                    start_time: int = None,
                                    end_time: int = None,
                                    keywords: List[str] = None,
                                    keyword_type: str = "and",
                                    prefix: str = None,
                                    direction: str = "SEND",
                                    limit: int = 20,
                                    offset: int = 0) -> List[MessageRecord]:
        """组合查询消息"""
        async with self.session_factory() as session:
            try:
                conditions = self._build_message_conditions(
                    self_id, user_id, group_id, start_time, end_time,
                    keywords, keyword_type, prefix, direction
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
                            start_time: int = None,
                            end_time: int = None,
                            keywords: List[str] = None,
                            keyword_type: str = "and",
                            prefix: str = None,
                            direction: str = "SEND") -> int:
        """统计消息数量"""
        async with self.session_factory() as session:
            try:
                conditions = self._build_message_conditions(
                    self_id, user_id, group_id, start_time, end_time,
                    keywords, keyword_type, prefix, direction
                )

                stmt = select(func.count(Message.id))
                if conditions:
                    stmt = stmt.where(and_(*conditions))

                result = await session.execute(stmt)
                return result.scalar() or 0
            except Exception as e:
                print(f"统计消息数量失败: {e}")
                return 0

    async def count_messages_group_by_group_id(self,
                                            self_id: str = None,
                                            user_id: str = None,
                                            start_time: int = None,
                                            end_time: int = None,
                                            keywords: List[str] = None,
                                            keyword_type: str = "and",
                                            prefix: str = None,
                                            direction: str = "SEND") -> Dict[str, int]:
        """按 group_id 分组统计消息数量"""
        async with self.session_factory() as session:
            try:
                conditions = self._build_message_conditions(
                    self_id, user_id, None, start_time, end_time,
                    keywords, keyword_type, prefix, direction
                )

                stmt = select(Message.group_id, func.count(Message.id)).group_by(Message.group_id)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

                result = await session.execute(stmt)
                rows = result.all()

                return {group_id: count for group_id, count in rows if group_id}
            except Exception as e:
                print(f"按群号统计消息数量失败: {e}")
                return {}


    async def count_messages_group_by_self_id(self,
                                            user_id: str = None,
                                            group_id: str = None,
                                            start_time: int = None,
                                            end_time: int = None,
                                            keywords: List[str] = None,
                                            keyword_type: str = "and",
                                            prefix: str = None,
                                            direction: str = "SEND") -> Dict[str, int]:
        """按 self_id 分组统计消息数量"""
        async with self.session_factory() as session:
            try:
                conditions = self._build_message_conditions(
                    None, user_id, group_id, start_time, end_time,
                    keywords, keyword_type, prefix, direction
                )

                stmt = select(Message.self_id, func.count(Message.id)).group_by(Message.self_id)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

                result = await session.execute(stmt)
                rows = result.all()

                return {self_id: count for self_id, count in rows if self_id}
            except Exception as e:
                print(f"按 self_id 统计消息数量失败: {e}")
                return {}
            
    async def count_messages_group_by_user_id(self,
                                            self_id: str = None,
                                            group_id: str = None,
                                            start_time: int = None,
                                            end_time: int = None,
                                            keywords: List[str] = None,
                                            keyword_type: str = "and",
                                            prefix: str = None,
                                            direction: str = "SEND") -> Dict[str, int]:
        """按 user_id 分组统计消息数量"""
        async with self.session_factory() as session:
            try:
                conditions = self._build_message_conditions(
                    self_id, None, group_id, start_time, end_time,
                    keywords, keyword_type, prefix, direction
                )

                stmt = select(Message.user_id, func.count(Message.id)).group_by(Message.user_id)
                if conditions:
                    stmt = stmt.where(and_(*conditions))

                result = await session.execute(stmt)
                rows = result.all()

                return {user_id: count for user_id, count in rows if user_id}
            except Exception as e:
                print(f"按 user_id 统计消息数量失败: {e}")
                return {}

    async def count_messages_by_time_intervals(self,
                                             self_id: str = None,
                                             start_time: int = None,
                                             end_time: int = None,
                                             interval_hours: int = 3,
                                             direction: str = "SEND") -> List[Dict[str, Any]]:
        """按时间间隔统计消息数量"""
        async with self.session_factory() as session:
            try:
                if not start_time or not end_time:
                    return []

                # 计算时间间隔（秒）
                interval_seconds = interval_hours * 3600

                # 构建基础条件
                conditions = []
                if self_id:
                    conditions.append(Message.self_id == self_id)
                if direction:
                    conditions.append(Message.direction == direction)
                if start_time:
                    conditions.append(Message.timestamp >= start_time)
                if end_time:
                    conditions.append(Message.timestamp <= end_time)

                # 使用SQL计算时间间隔分组
                # 将时间戳按间隔分组
                time_group_expr = func.floor((Message.timestamp - start_time) / interval_seconds) * interval_seconds + start_time

                stmt = select(
                    time_group_expr.label('time_group'),
                    func.count(Message.id).label('message_count')
                ).group_by(time_group_expr).order_by(time_group_expr)

                if conditions:
                    stmt = stmt.where(and_(*conditions))

                result = await session.execute(stmt)
                rows = result.fetchall()

                # 格式化结果
                time_stats = []
                for row in rows:
                    time_group = int(row.time_group)
                    message_count = row.message_count

                    # 转换为可读的时间格式
                    from datetime import datetime
                    dt = datetime.fromtimestamp(time_group)
                    time_label = dt.strftime('%H:%M')

                    time_stats.append({
                        'timestamp': time_group,
                        'time_label': time_label,
                        'message_count': message_count
                    })

                return time_stats

            except Exception as e:
                print(f"按时间间隔统计消息数量失败: {e}")
                return []

    async def count_messages_by_type(self,
                                   self_id: str = None,
                                   start_time: int = None,
                                   end_time: int = None,
                                   direction: str = "SEND") -> Dict[str, int]:
        """按消息类型统计消息数量"""
        async with self.session_factory() as session:
            try:
                conditions = []
                if self_id:
                    conditions.append(Message.self_id == self_id)
                if direction:
                    conditions.append(Message.direction == direction)
                if start_time:
                    conditions.append(Message.timestamp >= start_time)
                if end_time:
                    conditions.append(Message.timestamp <= end_time)

                # 按消息类型分组统计
                stmt = select(
                    Message.message_type,
                    func.count(Message.id).label('count')
                ).group_by(Message.message_type)

                if conditions:
                    stmt = stmt.where(and_(*conditions))

                result = await session.execute(stmt)
                rows = result.fetchall()

                # 格式化结果，将消息类型转换为中文
                type_mapping = {
                    'group': '群聊',
                    'private': '私聊',
                    'notice': '通知',
                    'request': '请求',
                    'meta_event': '元事件'
                }

                type_stats = {}
                for row in rows:
                    message_type = row.message_type
                    count = row.count

                    # 转换为中文名称
                    chinese_type = type_mapping.get(message_type, message_type)
                    type_stats[chinese_type] = count

                return type_stats

            except Exception as e:
                print(f"按消息类型统计消息数量失败: {e}")
                return {}


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
        if int(expire_days) <= 1:
            return
        cutoff_date = int((datetime.now() - timedelta(days=expire_days)).timestamp())

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
