"""
OneBot v11 消息格式解析类
参考文档: https://283375.github.io/onebot_v11_vitepress/api/public.html
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
import html


@dataclass
class MessageSegment:
    """消息段基类"""
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """转换为CQ码格式"""
        if self.type == "text":
            return self.data.get("text", "")
        
        params = []
        for key, value in self.data.items():
            if value is not None:
                # 转义特殊字符
                escaped_value = str(value).replace("&", "&amp;").replace("[", "&#91;").replace("]", "&#93;").replace(",", "&#44;")
                params.append(f"{key}={escaped_value}")
        
        if params:
            return f"[CQ:{self.type},{','.join(params)}]"
        else:
            return f"[CQ:{self.type}]"
    
    def __repr__(self) -> str:
        return f"MessageSegment(type='{self.type}', data={self.data})"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageSegment':
        """从字典创建消息段"""
        return cls(
            type=data.get("type", ""),
            data=data.get("data", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type,
            "data": self.data
        }


class Message:
    """消息类，包含多个消息段"""
    
    def __init__(self, segments: Optional[List[Union[MessageSegment, Dict[str, Any]]]] = None):
        self.segments: List[MessageSegment] = []
        if segments:
            for segment in segments:
                if isinstance(segment, dict):
                    self.segments.append(MessageSegment.from_dict(segment))
                elif isinstance(segment, MessageSegment):
                    self.segments.append(segment)
    
    def __str__(self) -> str:
        """转换为字符串（CQ码格式）"""
        return "".join(str(segment) for segment in self.segments)
    
    def __repr__(self) -> str:
        return f"Message({self.segments})"
    
    def __len__(self) -> int:
        return len(self.segments)
    
    def __getitem__(self, index) -> MessageSegment:
        return self.segments[index]
    
    def __iter__(self):
        return iter(self.segments)
    
    def append(self, segment: Union[MessageSegment, Dict[str, Any]]) -> 'Message':
        """添加消息段"""
        if isinstance(segment, dict):
            self.segments.append(MessageSegment.from_dict(segment))
        elif isinstance(segment, MessageSegment):
            self.segments.append(segment)
        return self
    
    def extend(self, segments: List[Union[MessageSegment, Dict[str, Any]]]) -> 'Message':
        """添加多个消息段"""
        for segment in segments:
            self.append(segment)
        return self
    
    def extract_plain_text(self) -> str:
        """提取纯文本内容"""
        text_parts = []
        for segment in self.segments:
            if segment.type == "text":
                text_parts.append(segment.data.get("text", ""))
        return "".join(text_parts)
    
    def get_segments_by_type(self, segment_type: str) -> List[MessageSegment]:
        """获取指定类型的消息段"""
        return [segment for segment in self.segments if segment.type == segment_type]
    
    def has_type(self, segment_type: str) -> bool:
        """检查是否包含指定类型的消息段"""
        return any(segment.type == segment_type for segment in self.segments)
    
    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> 'Message':
        """从消息段列表创建消息"""
        return cls(data)
    
    def to_list(self) -> List[Dict[str, Any]]:
        """转换为消息段列表"""
        return [segment.to_dict() for segment in self.segments]


# 常用消息段构造函数
class MessageBuilder:
    """消息构造器"""
    
    @staticmethod
    def text(text: str) -> MessageSegment:
        """文本消息段"""
        return MessageSegment("text", {"text": text})
    
    @staticmethod
    def at(qq: Union[str, int]) -> MessageSegment:
        """@某人消息段"""
        return MessageSegment("at", {"qq": str(qq)})
    
    @staticmethod
    def at_all() -> MessageSegment:
        """@全体成员消息段"""
        return MessageSegment("at", {"qq": "all"})
    
    @staticmethod
    def image(file: str, url: Optional[str] = None, file_size: Optional[str] = None, 
              sub_type: Optional[int] = None, summary: Optional[str] = None) -> MessageSegment:
        """图片消息段"""
        data = {"file": file}
        if url:
            data["url"] = url
        if file_size:
            data["file_size"] = file_size
        if sub_type is not None:
            data["sub_type"] = sub_type
        if summary:
            data["summary"] = summary
        return MessageSegment("image", data)
    
    @staticmethod
    def face(id: Union[str, int]) -> MessageSegment:
        """表情消息段"""
        return MessageSegment("face", {"id": str(id)})
    
    @staticmethod
    def record(file: str, url: Optional[str] = None) -> MessageSegment:
        """语音消息段"""
        data = {"file": file}
        if url:
            data["url"] = url
        return MessageSegment("record", data)
    
    @staticmethod
    def video(file: str, url: Optional[str] = None) -> MessageSegment:
        """视频消息段"""
        data = {"file": file}
        if url:
            data["url"] = url
        return MessageSegment("video", data)
    
    @staticmethod
    def reply(id: Union[str, int]) -> MessageSegment:
        """回复消息段"""
        return MessageSegment("reply", {"id": str(id)})
    
    @staticmethod
    def forward(id: str) -> MessageSegment:
        """转发消息段"""
        return MessageSegment("forward", {"id": id})
    
    @staticmethod
    def json_msg(data: Union[str, Dict[str, Any]]) -> MessageSegment:
        """JSON消息段"""
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        return MessageSegment("json", {"data": data})
    
    @staticmethod
    def xml(data: str) -> MessageSegment:
        """XML消息段"""
        return MessageSegment("xml", {"data": data})
    
    @staticmethod
    def poke(qq: Union[str, int]) -> MessageSegment:
        """戳一戳消息段"""
        return MessageSegment("poke", {"qq": str(qq)})


# 消息解析工具
class MessageParser:
    """消息解析工具"""
    
    @staticmethod
    def parse_raw_message(raw_message: str) -> Message:
        """解析原始消息字符串（CQ码格式）为Message对象"""
        # 这里可以实现CQ码解析逻辑
        # 简化实现，直接返回文本消息
        return Message([MessageBuilder.text(raw_message)])
    
    @staticmethod
    def parse_message_array(message_array: List[Dict[str, Any]]) -> Message:
        """解析消息数组为Message对象"""
        return Message.from_list(message_array)
    
    @staticmethod
    def extract_keywords(message: Message, prefixes: List[str]) -> List[str]:
        """提取消息中的关键词（以指定前缀开头）"""
        text = message.extract_plain_text()
        keywords = []
        for prefix in prefixes:
            if text.startswith(prefix):
                keywords.append(prefix)
        return keywords
    
    @staticmethod
    def contains_forbidden_words(message: Message, forbidden_words: List[str]) -> bool:
        """检查消息是否包含违禁词"""
        text = message.extract_plain_text().lower()
        return any(word.lower() in text for word in forbidden_words)
    
    @staticmethod
    def replace_command_alias(message: Message, alias_dict: Dict[str, List[str]]) -> Message:
        """替换指令别名"""
        text = message.extract_plain_text()
        
        for command, aliases in alias_dict.items():
            for alias in aliases:
                if text.startswith(alias):
                    # 替换别名为原指令
                    new_text = command + text[len(alias):]
                    return Message([MessageBuilder.text(new_text)])
        
        return message
