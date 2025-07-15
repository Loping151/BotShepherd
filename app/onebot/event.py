"""
OneBot v11 事件类型解析
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime
import json

from .message import Message, MessageParser


@dataclass
class Sender:
    """发送者信息"""
    user_id: int
    nickname: str
    card: str = ""
    role: str = "member"  # member, admin, owner
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Sender':
        return cls(
            user_id=data.get("user_id", 0),
            nickname=data.get("nickname", ""),
            card=data.get("card", ""),
            role=data.get("role", "member")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "card": self.card,
            "role": self.role
        }


@dataclass
class BaseEvent(ABC):
    """事件基类"""
    time: int
    self_id: int
    post_type: str
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEvent':
        """从字典创建事件对象"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        pass
    
    def get_datetime(self) -> datetime:
        """获取事件时间的datetime对象"""
        return datetime.fromtimestamp(self.time)


@dataclass
class MessageEvent(BaseEvent):
    """消息事件"""
    message_type: str  # private, group
    sub_type: str
    message_id: int
    user_id: int
    message: Message
    raw_message: str
    font: int
    sender: Sender
    group_id: Optional[int] = None
    message_seq: Optional[int] = None
    real_id: Optional[int] = None
    real_seq: Optional[str] = None
    message_format: str = "array"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEvent':
        # 解析消息内容
        message_data = data.get("message", [])
        if isinstance(message_data, list):
            message = MessageParser.parse_message_array(message_data)
        else:
            message = MessageParser.parse_raw_message(str(message_data))
        
        # 解析发送者信息
        sender_data = data.get("sender", {})
        sender = Sender.from_dict(sender_data)
        
        return cls(
            time=data.get("time", 0),
            self_id=data.get("self_id", 0),
            post_type=data.get("post_type", "message"),
            message_type=data.get("message_type", ""),
            sub_type=data.get("sub_type", ""),
            message_id=data.get("message_id", 0),
            user_id=data.get("user_id", 0),
            message=message,
            raw_message=data.get("raw_message", ""),
            font=data.get("font", 14),
            sender=sender,
            group_id=data.get("group_id"),
            message_seq=data.get("message_seq"),
            real_id=data.get("real_id"),
            real_seq=data.get("real_seq"),
            message_format=data.get("message_format", "array")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "time": self.time,
            "self_id": self.self_id,
            "post_type": self.post_type,
            "message_type": self.message_type,
            "sub_type": self.sub_type,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "message": self.message.to_list(),
            "raw_message": self.raw_message,
            "font": self.font,
            "sender": self.sender.to_dict(),
            "message_format": self.message_format
        }
        
        if self.group_id is not None:
            result["group_id"] = self.group_id
        if self.message_seq is not None:
            result["message_seq"] = self.message_seq
        if self.real_id is not None:
            result["real_id"] = self.real_id
        if self.real_seq is not None:
            result["real_seq"] = self.real_seq
            
        return result
    
    def is_group_message(self) -> bool:
        """是否为群消息"""
        return self.message_type == "group"
    
    def is_private_message(self) -> bool:
        """是否为私聊消息"""
        return self.message_type == "private"
    
    def get_plain_text(self) -> str:
        """获取纯文本内容"""
        return self.message.extract_plain_text()
    
    def get_user_display_name(self) -> str:
        """获取用户显示名称（群名片优先，否则昵称）"""
        return self.sender.card or self.sender.nickname


@dataclass
class NoticeEvent(BaseEvent):
    """通知事件"""
    notice_type: str
    sub_type: str
    user_id: int
    group_id: Optional[int] = None
    target_id: Optional[int] = None
    sender_id: Optional[int] = None
    raw_info: Optional[List[Dict[str, Any]]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NoticeEvent':
        return cls(
            time=data.get("time", 0),
            self_id=data.get("self_id", 0),
            post_type=data.get("post_type", "notice"),
            notice_type=data.get("notice_type", ""),
            sub_type=data.get("sub_type", ""),
            user_id=data.get("user_id", 0),
            group_id=data.get("group_id"),
            target_id=data.get("target_id"),
            sender_id=data.get("sender_id"),
            raw_info=data.get("raw_info")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "time": self.time,
            "self_id": self.self_id,
            "post_type": self.post_type,
            "notice_type": self.notice_type,
            "sub_type": self.sub_type,
            "user_id": self.user_id
        }
        
        if self.group_id is not None:
            result["group_id"] = self.group_id
        if self.target_id is not None:
            result["target_id"] = self.target_id
        if self.sender_id is not None:
            result["sender_id"] = self.sender_id
        if self.raw_info is not None:
            result["raw_info"] = self.raw_info
            
        return result
    
    def is_poke(self) -> bool:
        """是否为戳一戳事件"""
        return self.notice_type == "notify" and self.sub_type == "poke"
    
    def is_group_event(self) -> bool:
        """是否为群事件"""
        return self.group_id is not None


@dataclass
class RequestEvent(BaseEvent):
    """请求事件"""
    request_type: str
    sub_type: str
    user_id: int
    comment: str
    flag: str
    group_id: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RequestEvent':
        return cls(
            time=data.get("time", 0),
            self_id=data.get("self_id", 0),
            post_type=data.get("post_type", "request"),
            request_type=data.get("request_type", ""),
            sub_type=data.get("sub_type", ""),
            user_id=data.get("user_id", 0),
            comment=data.get("comment", ""),
            flag=data.get("flag", ""),
            group_id=data.get("group_id")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "time": self.time,
            "self_id": self.self_id,
            "post_type": self.post_type,
            "request_type": self.request_type,
            "sub_type": self.sub_type,
            "user_id": self.user_id,
            "comment": self.comment,
            "flag": self.flag
        }
        
        if self.group_id is not None:
            result["group_id"] = self.group_id
            
        return result


@dataclass
class MetaEvent(BaseEvent):
    """元事件"""
    meta_event_type: str
    sub_type: str
    status: Optional[Dict[str, Any]] = None
    interval: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetaEvent':
        return cls(
            time=data.get("time", 0),
            self_id=data.get("self_id", 0),
            post_type=data.get("post_type", "meta_event"),
            meta_event_type=data.get("meta_event_type", ""),
            sub_type=data.get("sub_type", ""),
            status=data.get("status"),
            interval=data.get("interval")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "time": self.time,
            "self_id": self.self_id,
            "post_type": self.post_type,
            "meta_event_type": self.meta_event_type,
            "sub_type": self.sub_type
        }
        
        if self.status is not None:
            result["status"] = self.status
        if self.interval is not None:
            result["interval"] = self.interval
            
        return result


class EventParser:
    """事件解析器"""
    
    @staticmethod
    def parse_event(data: Dict[str, Any]) -> BaseEvent:
        """解析事件数据"""
        post_type = data.get("post_type", "")
        
        if post_type == "message":
            return MessageEvent.from_dict(data)
        elif post_type == "notice":
            return NoticeEvent.from_dict(data)
        elif post_type == "request":
            return RequestEvent.from_dict(data)
        elif post_type == "meta_event":
            return MetaEvent.from_dict(data)
        else:
            # 默认返回消息事件
            return MessageEvent.from_dict(data)
    
    @staticmethod
    def parse_json_event(json_str: str) -> BaseEvent:
        """解析JSON字符串事件"""
        try:
            data = json.loads(json_str)
            return EventParser.parse_event(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    @staticmethod
    def is_command(event: MessageEvent, prefixes: List[str]) -> bool:
        """检查是否为指令消息"""
        if not isinstance(event, MessageEvent):
            return False
        
        text = event.get_plain_text().strip()
        return any(text.startswith(prefix) for prefix in prefixes)
    
    @staticmethod
    def extract_command(event: MessageEvent, prefixes: List[str]) -> Optional[str]:
        """提取指令内容"""
        if not EventParser.is_command(event, prefixes):
            return None
        
        text = event.get_plain_text().strip()
        for prefix in prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        
        return None
