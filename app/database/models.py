"""
数据库模型定义
使用SQLAlchemy定义数据库表结构
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

Base = declarative_base()

class Message(Base):
    """消息表"""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(50), index=True)
    self_id = Column(String(20), nullable=False, index=True)
    user_id = Column(String(20), index=True)
    group_id = Column(String(20), index=True)
    message_type = Column(String(20), nullable=False)
    sub_type = Column(String(20))
    post_type = Column(String(20))
    raw_message = Column(Text)
    message_content = Column(Text)
    sender_info = Column(Text)  # JSON格式的发送者信息
    timestamp = Column(BigInteger, nullable=False, index=True)  # 使用BigInteger存储时间戳
    direction = Column(String(10), nullable=False)  # RECV/SEND
    connection_id = Column(String(50))
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    # 创建复合索引
    __table_args__ = (
        Index('idx_messages_self_id_timestamp', 'self_id', 'timestamp'),
        Index('idx_messages_group_id_timestamp', 'group_id', 'timestamp'),
        Index('idx_messages_user_id_timestamp', 'user_id', 'timestamp'),
        Index('idx_messages_content_search', 'message_content'),
    )



@dataclass
class MessageRecord:
    """消息记录类"""
    id: int
    message_id: Optional[str]
    self_id: str
    user_id: Optional[str]
    group_id: Optional[str]
    message_type: str
    sub_type: Optional[str]
    post_type: str
    raw_message: str
    message_content: str
    sender_info: Dict[str, Any]
    timestamp: datetime
    direction: str
    connection_id: Optional[str]
    processed: bool
    created_at: datetime

    @classmethod
    def from_db_row(cls, row: Message) -> 'MessageRecord':
        """从数据库行创建消息记录"""
        sender_info = {}
        if row.sender_info:
            try:
                sender_info = json.loads(row.sender_info)
            except (json.JSONDecodeError, TypeError):
                sender_info = {}

        return cls(
            id=row.id,
            message_id=row.message_id,
            self_id=row.self_id,
            user_id=row.user_id,
            group_id=row.group_id,
            message_type=row.message_type,
            sub_type=row.sub_type,
            post_type=row.post_type,
            raw_message=row.raw_message or "",
            message_content=row.message_content or "",
            sender_info=sender_info,
            timestamp=row.timestamp,
            direction=row.direction,
            connection_id=row.connection_id,
            processed=row.processed or False,
            created_at=row.created_at
        )
