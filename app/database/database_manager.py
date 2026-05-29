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
from sqlalchemy import case, select, and_, or_, func, desc, delete, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from .models import Base, Message, MessageRecord
from sqlalchemy.exc import OperationalError


class DatabaseManager:
    """数据库管理器"""
    MAX_RETRY = 3
    RETRY_DELAY = 0.1
    WRITE_QUEUE_MAX = 20000   # 写队列上限,满则丢弃告警
    WRITE_BATCH_MAX = 200     # 单事务最多批量写入条数
    CLEANUP_BATCH = 5000      # 过期清理每批删除行数

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.db_config = None
        self.engine = None
        self.session_factory = None
        self.db_path = None
        self._write_queue = None   # asyncio.Queue,save_message 入队,后台 writer 落库
        self._writer_task = None
        self._cleanup_task = None

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

        # busy_timeout/synchronous 是连接级,需逐连接设;在建连接前注册
        @event.listens_for(self.engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, conn_record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA busy_timeout=10000")   # 写锁最多等10s,不立即报 database is locked
            cur.execute("PRAGMA synchronous=NORMAL")    # WAL 下安全且少 fsync 卡顿
            cur.close()

        async with self.engine.begin() as conn:
            row = (await conn.execute(text("PRAGMA journal_mode=WAL"))).fetchone()
            if not row or str(row[0]).lower() != "wal":
                print(f"[DB] 警告: journal_mode 未切到 WAL,当前={row}")

        # 创建会话工厂
        self.session_factory = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # 创建数据表
        await self._create_tables()

        # 启动时回收 WAL:无流量能拿独占锁截断(execv 自重启不 close DB,靠此清理)
        try:
            async with self.engine.begin() as conn:
                row = (await conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))).fetchone()
                if row and row[0] != 0:
                    print(f"[DB] 启动时 WAL 未完全截断(busy): {tuple(row)}")
        except Exception as e:
            print(f"[DB] 启动时 checkpoint 失败: {e}")

        # 启动后台写入任务(save_message 入队,DB 慢不再卡转发热路径)
        self._write_queue = asyncio.Queue(maxsize=self.WRITE_QUEUE_MAX)
        self._writer_task = asyncio.create_task(self._writer_loop())

        # 启动数据清理任务
        self._cleanup_task = asyncio.create_task(self._start_cleanup_task())
    
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
                        if isinstance(msg_part.get("data", {}).get("text", ""), list):
                            text_parts.append("\n".join(msg_part.get("data", {}).get("text", "")))
                        else:
                            text_parts.append(msg_part.get("data", {}).get("text", ""))
                    elif msg_part.get("type") == "at":
                        text_parts.append(f"@{msg_part.get('data', {}).get('qq', '')}")
                        if str(msg_part.get("data", {}).get("qq")) == self_id:
                            text_parts.append(f"[at BS Bot]")
                    elif msg_part.get("type") == "face":
                        text_parts.append(f"[动画表情]")
                    elif msg_part.get("type") == "image":
                        text_parts.append(f"[图片]")
                    else: # 其他类型
                        text_parts.append(f"[{msg_part.get('type', '未知消息类型')}]")
                message_content = "".join(text_parts)
            elif isinstance(message_data["message"], dict):
                if message_data["message"].get("type") == "image":
                    message_content = "[图片]"
                else:
                    message_content = f"[{message_data['message'].get('type', '未知消息类型')}]: {str(message_data['message'])[:1000]}"
            else:
                message_content = str(message_data["message"])[:1000]  # 限制长度为1000字符

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

        # 入队即返回,DB 慢/被锁不再卡转发热路径;后台 _writer_loop 批量落库
        if self._write_queue is None:
            return
        try:
            self._write_queue.put_nowait(message_record)
        except asyncio.QueueFull:
            print(f"[DB] 写队列已满({self.WRITE_QUEUE_MAX})，丢弃消息记录 direction={direction}")

    async def _writer_loop(self):
        """后台批量落库,降低事务数与 fsync 次数"""
        while True:
            try:
                record = await self._write_queue.get()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[DB] writer 取队列异常: {e}")
                continue

            batch = [record]
            for _ in range(self.WRITE_BATCH_MAX - 1):
                try:
                    batch.append(self._write_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            try:
                await self._persist_batch(batch)
            except Exception as e:
                # CancelledError 是 BaseException,不会被这里捕获,会穿过 finally 正常传播
                print(f"[DB] 批量落库异常(丢弃{len(batch)}条): {e}")
            finally:
                for _ in batch:
                    self._write_queue.task_done()

    async def _persist_batch(self, records: List[Any]):
        """批量提交;锁冲突整批重试,其它错误回退逐条写,避免单条坏记录拖垮整批"""
        for attempt in range(self.MAX_RETRY):
            async with self.session_factory() as session:
                try:
                    session.add_all(records)
                    await session.commit()
                    return
                except OperationalError as e:
                    await session.rollback()
                    if "database is locked" in str(e) and attempt < self.MAX_RETRY - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    print(f"[错误] 批量写入失败(OperationalError),回退逐条: {e}")
                    break
                except Exception as e:
                    await session.rollback()
                    print(f"[错误] 批量保存消息失败,回退逐条: {e}")
                    break
        # 整批失败:逐条写,隔离单条坏记录,尽量不丢好记录
        for record in records:
            await self._persist_one(record)

    async def _persist_one(self, record: Any):
        """单条写入(带 database is locked 重试),失败则丢弃该条并告警"""
        for attempt in range(self.MAX_RETRY):
            async with self.session_factory() as session:
                try:
                    session.add(record)
                    await session.commit()
                    return
                except OperationalError as e:
                    await session.rollback()
                    if "database is locked" in str(e) and attempt < self.MAX_RETRY - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    print(f"[错误] 单条写入失败,丢弃: {e}")
                    return
                except Exception as e:
                    await session.rollback()
                    print(f"[错误] 单条保存消息失败,丢弃: {e}")
                    return

    def _build_message_conditions(self,
                                self_id: Optional[str] = None,
                                user_id: Optional[str] = None,
                                group_id: Optional[str] = None,
                                start_time: Optional[int] = None,
                                end_time: Optional[int] = None,
                                keywords: Optional[List[str]] = None,
                                keyword_type: str = "and",
                                prefix: Optional[str] = None,
                                direction: Optional[str] = "SEND",
                                private_only: bool = False) -> List[Any]:
        """构建通用的查询条件"""
        conditions = []

        if self_id:
            conditions.append(Message.self_id == self_id)
        if user_id:
            conditions.append(Message.user_id == user_id)
        if group_id:
            conditions.append(Message.group_id == group_id)
        elif private_only:
            # 只查询私聊消息（group_id为None或空）
            conditions.append(Message.group_id.is_(None))
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
                                    offset: int = 0,
                                    private_only: bool = False) -> List[MessageRecord]:
        """组合查询消息"""
        async with self.session_factory() as session:
            try:
                conditions = self._build_message_conditions(
                    self_id, user_id, group_id, start_time, end_time,
                    keywords, keyword_type, prefix, direction, private_only
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
                            direction: str = "SEND",
                            private_only: bool = False) -> int:
        """统计消息数量"""
        async with self.session_factory() as session:
            try:
                conditions = self._build_message_conditions(
                    self_id, user_id, group_id, start_time, end_time,
                    keywords, keyword_type, prefix, direction, private_only
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
        """分批删除过期消息(小事务+批间让锁),避免一次性巨型事务长时间独占写锁导致全局假死"""
        expire_days = self.db_config.get("auto_expire_days", 30)
        if int(expire_days) <= 1:
            return
        cutoff_date = int((datetime.now() - timedelta(days=expire_days)).timestamp())

        total_deleted = 0
        while True:
            async with self.session_factory() as session:
                try:
                    subq = select(Message.id).where(Message.timestamp < cutoff_date).limit(self.CLEANUP_BATCH)
                    result = await session.execute(delete(Message).where(Message.id.in_(subq)))
                    await session.commit()
                    n = result.rowcount or 0
                except Exception as e:
                    await session.rollback()
                    print(f"数据清理失败: {e}")
                    return
            total_deleted += n
            if n < self.CLEANUP_BATCH:
                break
            await asyncio.sleep(0.5)

        if total_deleted > 0:
            print(f"清理了 {total_deleted} 条过期消息记录")
            try:
                async with self.engine.begin() as conn:
                    row = (await conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))).fetchone()
                    if row and row[0] != 0:
                        print(f"[DB] 清理后 WAL 未完全截断(busy): {tuple(row)}")
            except Exception as e:
                print(f"清理后 checkpoint 失败: {e}")


    async def close(self):
        """关闭数据库连接(先停清理、再尽量把写队列清空)"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except (asyncio.CancelledError, Exception):
                pass
        if self._write_queue is not None:
            try:
                await asyncio.wait_for(self._write_queue.join(), timeout=10)
            except asyncio.TimeoutError:
                print("[DB] 关闭时写队列未在10s内清空")
        if self._writer_task:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except (asyncio.CancelledError, Exception):
                pass
        if self.engine:
            await self.engine.dispose()
