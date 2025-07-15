"""
数据库模块 - 消息统计和存储
支持自动过期删除
"""

import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.sql import func, and_, or_
import json

Base = declarative_base()


class MessageRecord(Base):
    """消息记录表"""
    __tablename__ = 'message_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    self_id = Column(Integer, nullable=False, index=True)  # Bot QQ号
    message_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False, index=True)
    group_id = Column(Integer, nullable=True, index=True)  # 私聊时为None
    message_type = Column(String(20), nullable=False)  # private, group
    raw_message = Column(Text, nullable=False)
    message_data = Column(Text, nullable=False)  # JSON格式的消息段数据
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    date_str = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD格式，便于按日期查询
    
    # 索引
    __table_args__ = (
        Index('idx_self_date', 'self_id', 'date_str'),
        Index('idx_self_group_date', 'self_id', 'group_id', 'date_str'),
        Index('idx_self_user_date', 'self_id', 'user_id', 'date_str'),
    )


class KeywordRecord(Base):
    """关键词统计表"""
    __tablename__ = 'keyword_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    self_id = Column(Integer, nullable=False, index=True)
    keyword = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    group_id = Column(Integer, nullable=True, index=True)
    message_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    date_str = Column(String(10), nullable=False, index=True)
    
    # 索引
    __table_args__ = (
        Index('idx_self_keyword_date', 'self_id', 'keyword', 'date_str'),
        Index('idx_self_keyword_group_date', 'self_id', 'keyword', 'group_id', 'date_str'),
    )


class DailyStatistics(Base):
    """每日统计表"""
    __tablename__ = 'daily_statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    self_id = Column(Integer, nullable=False, index=True)
    date_str = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    group_id = Column(Integer, nullable=True, index=True)  # None表示全部群组
    user_id = Column(Integer, nullable=True, index=True)   # None表示全部用户
    message_count = Column(Integer, nullable=False, default=0)
    keyword_stats = Column(Text, nullable=True)  # JSON格式的关键词统计
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        Index('idx_self_date_group', 'self_id', 'date_str', 'group_id'),
        Index('idx_self_date_user', 'self_id', 'date_str', 'user_id'),
    )


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_config):
        self.config = database_config
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self.setup_database()
    
    def setup_database(self):
        """设置数据库连接"""
        if self.config.type == "sqlite":
            # 确保数据目录存在
            data_path = self.config.data_path
            os.makedirs(data_path, exist_ok=True)
            
            # 同步引擎
            db_file = os.path.join(data_path, "botshepherd.db")
            database_url = f"sqlite:///{db_file}"
            self.engine = create_engine(database_url, echo=False)
            
            # 异步引擎
            async_database_url = f"sqlite+aiosqlite:///{db_file}"
            self.async_engine = create_async_engine(async_database_url, echo=False)
            
        else:
            # 其他数据库类型的支持可以在这里添加
            raise NotImplementedError(f"Database type {self.config.type} not implemented yet")
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine, class_=AsyncSession)
        
        # 创建表
        Base.metadata.create_all(bind=self.engine)
    
    async def create_tables_async(self):
        """异步创建表"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    def get_session(self) -> Session:
        """获取同步会话"""
        return self.SessionLocal()
    
    def get_async_session(self) -> AsyncSession:
        """获取异步会话"""
        return self.AsyncSessionLocal()
    
    async def add_message_record(self, self_id: int, message_event) -> bool:
        """添加消息记录"""
        try:
            async with self.get_async_session() as session:
                # 创建消息记录
                record = MessageRecord(
                    self_id=self_id,
                    message_id=message_event.message_id,
                    user_id=message_event.user_id,
                    group_id=message_event.group_id if hasattr(message_event, 'group_id') else None,
                    message_type=message_event.message_type,
                    raw_message=message_event.raw_message,
                    message_data=json.dumps(message_event.message.to_list(), ensure_ascii=False),
                    timestamp=message_event.get_datetime(),
                    date_str=message_event.get_datetime().strftime('%Y-%m-%d')
                )
                
                session.add(record)
                await session.commit()
                return True
                
        except Exception as e:
            print(f"Error adding message record: {e}")
            return False
    
    async def add_keyword_records(self, self_id: int, message_event, keywords: List[str]) -> bool:
        """添加关键词记录"""
        if not keywords:
            return True
        
        try:
            async with self.get_async_session() as session:
                records = []
                for keyword in keywords:
                    record = KeywordRecord(
                        self_id=self_id,
                        keyword=keyword,
                        user_id=message_event.user_id,
                        group_id=message_event.group_id if hasattr(message_event, 'group_id') else None,
                        message_id=message_event.message_id,
                        timestamp=message_event.get_datetime(),
                        date_str=message_event.get_datetime().strftime('%Y-%m-%d')
                    )
                    records.append(record)
                
                session.add_all(records)
                await session.commit()
                return True
                
        except Exception as e:
            print(f"Error adding keyword records: {e}")
            return False
    
    async def get_daily_message_count(self, self_id: int, date_str: str, 
                                     group_id: Optional[int] = None, 
                                     user_id: Optional[int] = None) -> int:
        """获取指定日期的消息数量"""
        try:
            async with self.get_async_session() as session:
                query = session.query(func.count(MessageRecord.id)).filter(
                    MessageRecord.self_id == self_id,
                    MessageRecord.date_str == date_str
                )
                
                if group_id is not None:
                    query = query.filter(MessageRecord.group_id == group_id)
                if user_id is not None:
                    query = query.filter(MessageRecord.user_id == user_id)
                
                result = await session.execute(query)
                return result.scalar() or 0
                
        except Exception as e:
            print(f"Error getting daily message count: {e}")
            return 0
    
    async def get_keyword_count(self, self_id: int, keyword: str, date_str: str,
                               group_id: Optional[int] = None) -> int:
        """获取指定关键词在指定日期的出现次数"""
        try:
            async with self.get_async_session() as session:
                query = session.query(func.count(KeywordRecord.id)).filter(
                    KeywordRecord.self_id == self_id,
                    KeywordRecord.keyword == keyword,
                    KeywordRecord.date_str == date_str
                )
                
                if group_id is not None:
                    query = query.filter(KeywordRecord.group_id == group_id)
                
                result = await session.execute(query)
                return result.scalar() or 0
                
        except Exception as e:
            print(f"Error getting keyword count: {e}")
            return 0
    
    async def search_keyword_records(self, self_id: int, keyword: str, 
                                    days: int = 7, group_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """搜索关键词记录"""
        try:
            async with self.get_async_session() as session:
                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                query = session.query(KeywordRecord).filter(
                    KeywordRecord.self_id == self_id,
                    KeywordRecord.keyword.like(f"%{keyword}%"),
                    KeywordRecord.timestamp >= start_date,
                    KeywordRecord.timestamp <= end_date
                )
                
                if group_id is not None:
                    query = query.filter(KeywordRecord.group_id == group_id)
                
                query = query.order_by(KeywordRecord.timestamp.desc()).limit(100)
                
                result = await session.execute(query)
                records = result.scalars().all()
                
                return [
                    {
                        "keyword": record.keyword,
                        "user_id": record.user_id,
                        "group_id": record.group_id,
                        "message_id": record.message_id,
                        "timestamp": record.timestamp.isoformat(),
                        "date_str": record.date_str
                    }
                    for record in records
                ]
                
        except Exception as e:
            print(f"Error searching keyword records: {e}")
            return []
    
    async def cleanup_expired_data(self, self_id: int, expire_days: int) -> bool:
        """清理过期数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=expire_days)
            cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')
            
            async with self.get_async_session() as session:
                # 删除过期的消息记录
                await session.execute(
                    MessageRecord.__table__.delete().where(
                        and_(
                            MessageRecord.self_id == self_id,
                            MessageRecord.date_str < cutoff_date_str
                        )
                    )
                )
                
                # 删除过期的关键词记录
                await session.execute(
                    KeywordRecord.__table__.delete().where(
                        and_(
                            KeywordRecord.self_id == self_id,
                            KeywordRecord.date_str < cutoff_date_str
                        )
                    )
                )
                
                # 删除过期的统计记录
                await session.execute(
                    DailyStatistics.__table__.delete().where(
                        and_(
                            DailyStatistics.self_id == self_id,
                            DailyStatistics.date_str < cutoff_date_str
                        )
                    )
                )
                
                await session.commit()
                return True
                
        except Exception as e:
            print(f"Error cleaning up expired data: {e}")
            return False
    
    async def get_statistics_summary(self, self_id: int, days: int = 7) -> Dict[str, Any]:
        """获取统计摘要"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            async with self.get_async_session() as session:
                # 消息总数
                message_count_query = session.query(func.count(MessageRecord.id)).filter(
                    MessageRecord.self_id == self_id,
                    MessageRecord.date_str >= start_date_str,
                    MessageRecord.date_str <= end_date_str
                )
                message_count_result = await session.execute(message_count_query)
                total_messages = message_count_result.scalar() or 0
                
                # 关键词总数
                keyword_count_query = session.query(func.count(KeywordRecord.id)).filter(
                    KeywordRecord.self_id == self_id,
                    KeywordRecord.date_str >= start_date_str,
                    KeywordRecord.date_str <= end_date_str
                )
                keyword_count_result = await session.execute(keyword_count_query)
                total_keywords = keyword_count_result.scalar() or 0
                
                # 活跃群组数
                active_groups_query = session.query(func.count(func.distinct(MessageRecord.group_id))).filter(
                    MessageRecord.self_id == self_id,
                    MessageRecord.date_str >= start_date_str,
                    MessageRecord.date_str <= end_date_str,
                    MessageRecord.group_id.isnot(None)
                )
                active_groups_result = await session.execute(active_groups_query)
                active_groups = active_groups_result.scalar() or 0
                
                return {
                    "total_messages": total_messages,
                    "total_keywords": total_keywords,
                    "active_groups": active_groups,
                    "days": days,
                    "start_date": start_date_str,
                    "end_date": end_date_str
                }
                
        except Exception as e:
            print(f"Error getting statistics summary: {e}")
            return {
                "total_messages": 0,
                "total_keywords": 0,
                "active_groups": 0,
                "days": days,
                "error": str(e)
            }
    
    async def close(self):
        """关闭数据库连接"""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
