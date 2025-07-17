"""
数据库模型定义
使用SQLAlchemy定义数据库表结构
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

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
    timestamp = Column(DateTime, nullable=False, index=True)
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

class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    user_id = Column(String(20), primary_key=True)
    nickname = Column(String(100))
    card = Column(String(100))
    role = Column(String(20))
    first_seen = Column(DateTime, default=func.now())
    last_seen = Column(DateTime, default=func.now())
    message_count = Column(Integer, default=0)
    
    # 索引
    __table_args__ = (
        Index('idx_users_last_seen', 'last_seen'),
        Index('idx_users_message_count', 'message_count'),
    )

class Group(Base):
    """群组表"""
    __tablename__ = 'groups'
    
    group_id = Column(String(20), primary_key=True)
    group_name = Column(String(100))
    first_seen = Column(DateTime, default=func.now())
    last_message_time = Column(DateTime)
    message_count = Column(Integer, default=0)
    member_count = Column(Integer, default=0)
    
    # 索引
    __table_args__ = (
        Index('idx_groups_last_message_time', 'last_message_time'),
        Index('idx_groups_message_count', 'message_count'),
    )

class Statistics(Base):
    """统计表"""
    __tablename__ = 'statistics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD格式
    self_id = Column(String(20), nullable=False)
    group_id = Column(String(20))
    message_count = Column(Integer, default=0)
    command_count = Column(Integer, default=0)
    user_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    
    # 唯一约束和索引
    __table_args__ = (
        Index('idx_statistics_unique', 'date', 'self_id', 'group_id', unique=True),
        Index('idx_statistics_date', 'date'),
    )

class ApiCall(Base):
    """API调用记录表"""
    __tablename__ = 'api_calls'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    self_id = Column(String(20), nullable=False)
    action = Column(String(50), nullable=False)
    params = Column(Text)  # JSON格式的参数
    result = Column(Text)  # JSON格式的结果
    success = Column(Boolean)
    timestamp = Column(DateTime, nullable=False, index=True)
    response_time = Column(Float)  # 响应时间（秒）
    created_at = Column(DateTime, default=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_api_calls_self_id_timestamp', 'self_id', 'timestamp'),
        Index('idx_api_calls_action', 'action'),
        Index('idx_api_calls_success', 'success'),
    )

class ConnectionLog(Base):
    """连接日志表"""
    __tablename__ = 'connection_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(String(50), nullable=False)
    event_type = Column(String(20), nullable=False)  # connect/disconnect/error
    client_ip = Column(String(45))  # 支持IPv6
    target_endpoint = Column(String(200))
    message = Column(Text)
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_connection_logs_connection_id', 'connection_id'),
        Index('idx_connection_logs_event_type', 'event_type'),
        Index('idx_connection_logs_timestamp', 'timestamp'),
    )

class FilterLog(Base):
    """过滤日志表"""
    __tablename__ = 'filter_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    self_id = Column(String(20), nullable=False)
    user_id = Column(String(20))
    group_id = Column(String(20))
    filter_type = Column(String(20), nullable=False)  # blacklist/receive_filter/send_filter/prefix_protection
    filter_rule = Column(String(200))
    original_message = Column(Text)
    filtered_message = Column(Text)
    action = Column(String(20))  # block/modify/warn
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_filter_logs_self_id_timestamp', 'self_id', 'timestamp'),
        Index('idx_filter_logs_filter_type', 'filter_type'),
        Index('idx_filter_logs_action', 'action'),
    )

class SystemMetrics(Base):
    """系统指标表"""
    __tablename__ = 'system_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(50), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20))
    tags = Column(Text)  # JSON格式的标签
    timestamp = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    
    # 索引
    __table_args__ = (
        Index('idx_system_metrics_name_timestamp', 'metric_name', 'timestamp'),
    )

# 数据库工具函数
def create_all_tables(engine):
    """创建所有表"""
    Base.metadata.create_all(engine)

def drop_all_tables(engine):
    """删除所有表"""
    Base.metadata.drop_all(engine)

def get_table_names():
    """获取所有表名"""
    return [table.name for table in Base.metadata.tables.values()]

def get_table_info():
    """获取表信息"""
    tables_info = []
    for table_name, table in Base.metadata.tables.items():
        columns_info = []
        for column in table.columns:
            columns_info.append({
                "name": column.name,
                "type": str(column.type),
                "nullable": column.nullable,
                "primary_key": column.primary_key,
                "index": column.index if hasattr(column, 'index') else False
            })
        
        indexes_info = []
        for index in table.indexes:
            indexes_info.append({
                "name": index.name,
                "columns": [col.name for col in index.columns],
                "unique": index.unique
            })
        
        tables_info.append({
            "name": table_name,
            "columns": columns_info,
            "indexes": indexes_info
        })
    
    return tables_info
