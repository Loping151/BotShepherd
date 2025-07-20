"""
OneBot v11 事件解析器
解析各种类型的OneBot事件
"""

import json
from typing import Dict, Any, Optional, Union, List
from pydantic import ValidationError

from .models import (
    Event, PostType, MessageType, NoticeType, RequestType,
    PrivateMessageEvent, GroupMessageEvent, PrivateMessageSentEvent, GroupMessageSentEvent,
    GroupUploadNotice, GroupAdminNotice, GroupDecreaseNotice, GroupIncreaseNotice,
    GroupBanNotice, FriendAddNotice, GroupRecallNotice, FriendRecallNotice,
    PokeNotifyEvent, FriendRequestEvent, GroupRequestEvent,
    LifecycleMetaEvent, HeartbeatMetaEvent,
    MessageSegment, Sender, ApiRequest, ApiResponse
)

class EventParser:
    """事件解析器"""
    
    @staticmethod
    def parse_raw_data(raw_data: Union[str, Dict[str, Any]]) -> Optional[Event]:
        """解析原始数据为事件对象"""
        try:
            if isinstance(raw_data, str):
                data = json.loads(raw_data)
            else:
                data = raw_data
            
            return EventParser.parse_event_data(data)
        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            print(f"解析事件数据失败: {e}")
            return None
    
    @staticmethod
    def parse_event_data(data: Dict[str, Any]) -> Optional[Event]:
        """解析事件数据"""
        post_type = data.get("post_type")
        
        if post_type == PostType.MESSAGE:
            return EventParser._parse_message_event(data)
        elif post_type == PostType.MESSAGE_SENT:
            return EventParser._parse_message_sent_event(data)
        elif post_type == PostType.NOTICE:
            return EventParser._parse_notice_event(data)
        elif post_type == PostType.REQUEST:
            return EventParser._parse_request_event(data)
        elif post_type == PostType.META_EVENT:
            return EventParser._parse_meta_event(data)
        elif EventParser.is_api_request(data): 
            return EventParser.parse_api_request(data)
        elif EventParser.is_api_response(data):
            return EventParser.parse_api_response(data)
        else:
            return None
    
    @staticmethod
    def _parse_message_event(data: Dict[str, Any]) -> Optional[Union[PrivateMessageEvent, GroupMessageEvent]]:
        """解析消息事件"""
        data = data.copy()

        message_type = data.get("message_type")
        
        # 解析消息段
        message_segments = EventParser._parse_message_segments(data.get("message", []))
        data["message"] = message_segments
        
        # 解析发送者信息
        sender_data = data.get("sender", {})
        sender = Sender(**sender_data)
        data["sender"] = sender
        
        if message_type == MessageType.PRIVATE:
            return PrivateMessageEvent(**data)
        elif message_type == MessageType.GROUP:
            return GroupMessageEvent(**data)
        else:
            print(f"未知的消息类型: {message_type}")
            return None
        
    @staticmethod
    def _parse_message_sent_event(data: Dict[str, Any]) -> Optional[Union[PrivateMessageSentEvent, GroupMessageSentEvent]]:
        """解析已发送消息事件"""
        data = data.copy()
        
        message_type = data.get("message_type")
        
        # 解析消息段
        message_segments = EventParser._parse_message_segments(data.get("message", []))
        data["message"] = message_segments
        
        # 解析发送者信息
        sender_data = data.get("sender", {})
        sender = Sender(**sender_data)
        data["sender"] = sender
        
        if message_type == MessageType.PRIVATE:
            return PrivateMessageSentEvent(**data)
        elif message_type == MessageType.GROUP:
            return GroupMessageSentEvent(**data)
        else:
            print(f"未知的消息类型: {message_type}")
            return None
    
    @staticmethod
    def _parse_notice_event(data: Dict[str, Any]) -> Optional[Event]:
        """解析通知事件"""
        notice_type = data.get("notice_type")
        
        if notice_type == NoticeType.GROUP_UPLOAD:
            return GroupUploadNotice(**data)
        elif notice_type == NoticeType.GROUP_ADMIN:
            return GroupAdminNotice(**data)
        elif notice_type == NoticeType.GROUP_DECREASE:
            return GroupDecreaseNotice(**data)
        elif notice_type == NoticeType.GROUP_INCREASE:
            return GroupIncreaseNotice(**data)
        elif notice_type == NoticeType.GROUP_BAN:
            return GroupBanNotice(**data)
        elif notice_type == NoticeType.FRIEND_ADD:
            return FriendAddNotice(**data)
        elif notice_type == NoticeType.GROUP_RECALL:
            return GroupRecallNotice(**data)
        elif notice_type == NoticeType.FRIEND_RECALL:
            return FriendRecallNotice(**data)
        elif notice_type == NoticeType.NOTIFY:
            sub_type = data.get("sub_type")
            if sub_type == "poke":
                return PokeNotifyEvent(**data)
        
        # print(f"未知的通知类型: {notice_type}")
        return None
    
    @staticmethod
    def _parse_request_event(data: Dict[str, Any]) -> Optional[Union[FriendRequestEvent, GroupRequestEvent]]:
        """解析请求事件"""
        request_type = data.get("request_type")
        
        if request_type == RequestType.FRIEND:
            return FriendRequestEvent(**data)
        elif request_type == RequestType.GROUP:
            return GroupRequestEvent(**data)
        else:
            print(f"未知的请求类型: {request_type}")
            return None
    
    @staticmethod
    def _parse_meta_event(data: Dict[str, Any]) -> Optional[Union[LifecycleMetaEvent, HeartbeatMetaEvent]]:
        """解析元事件"""
        meta_event_type = data.get("meta_event_type")
        
        if meta_event_type == "lifecycle":
            return LifecycleMetaEvent(**data)
        elif meta_event_type == "heartbeat":
            return HeartbeatMetaEvent(**data)
        else:
            print(f"未知的元事件类型: {meta_event_type}")
            return None
    
    @staticmethod
    def _parse_message_segments(message_data: Union[str, List[Dict[str, Any]]]) -> List[MessageSegment]:
        """解析消息段"""
        if isinstance(message_data, str):
            # 字符串格式消息，转换为文本消息段
            return [MessageSegment(type="text", data={"text": message_data})]
        elif isinstance(message_data, list):
            # 数组格式消息
            segments = []
            for segment_data in message_data:
                try:
                    segment = MessageSegment(**segment_data)
                    segments.append(segment)
                except ValidationError as e:
                    print(f"解析消息段失败: {e}")
                    # 创建一个文本消息段作为fallback
                    segments.append(MessageSegment(
                        type="text", 
                        data={"text": str(segment_data)}
                    ))
            return segments
        else:
            # 其他格式，转换为文本消息段
            return [MessageSegment(type="text", data={"text": str(message_data)})]
    
    @staticmethod
    def parse_api_request(data: Dict[str, Any]) -> Optional[ApiRequest]:
        """解析API请求"""
        try:
            return ApiRequest(**data)
        except ValidationError as e:
            print(f"解析API请求失败: {e}")
            return None
    
    @staticmethod
    def parse_api_response(data: Dict[str, Any]) -> Optional[ApiResponse]:
        """解析API响应"""
        try:
            return ApiResponse(**data)
        except ValidationError as e:
            print(f"解析API响应失败: {e}")
            return None
    
    @staticmethod
    def is_api_request(data: Dict[str, Any]) -> bool:
        """判断是否为API请求"""
        return "action" in data
    
    @staticmethod
    def is_api_response(data: Dict[str, Any]) -> bool:
        """判断是否为API响应"""
        return "status" in data and "retcode" in data
    
    @staticmethod
    def normalize_napcat_message(data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化NapCat消息格式"""
        # 处理NapCat的message_sent事件
        if data.get("post_type") == "message_sent":
            data["post_type"] = "message"
            # 移除NapCat特有字段
            data.pop("message_sent_type", None)
        
        return data

class MessageNormalizer:
    """消息标准化器"""
    
    @staticmethod
    def normalize_message_event(event_data: Dict[str, Any], 
                               enable_napcat_normalization: bool = False) -> Dict[str, Any]:
        """标准化消息事件"""
        if enable_napcat_normalization:
            event_data = EventParser.normalize_napcat_message(event_data)
        
        return event_data
    
    @staticmethod
    def extract_command_info(event: Union[PrivateMessageEvent, GroupMessageEvent], 
                           command_prefix: str) -> Optional[Dict[str, Any]]:
        """提取指令信息"""
        from .message_segment import MessageSegmentParser
        
        if not MessageSegmentParser.is_command(event.message, command_prefix):
            return None
        
        command_result = MessageSegmentParser.parse_command(event.message, command_prefix)
        if not command_result:
            return None
        
        command_name, args = command_result
        
        return {
            "command": command_name,
            "args": args,
            "raw_command": MessageSegmentParser.extract_text(event.message).strip(),
            "at_list": MessageSegmentParser.extract_at_list(event.message),
            "has_at_all": MessageSegmentParser.has_at_all(event.message),
            "images": MessageSegmentParser.extract_images(event.message),
            "reply_id": MessageSegmentParser.extract_reply_id(event.message)
        }

class EventValidator:
    """事件验证器"""
    
    @staticmethod
    def validate_event(event: Event) -> bool:
        """验证事件是否有效"""
        try:
            # 基本字段验证
            if not hasattr(event, 'time') or not hasattr(event, 'self_id'):
                return False
            
            # 时间戳验证
            if event.time <= 0:
                return False
            
            # self_id验证
            if event.self_id <= 0:
                return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_message_event(event: Union[PrivateMessageEvent, GroupMessageEvent]) -> bool:
        """验证消息事件"""
        if not EventValidator.validate_event(event):
            return False
        
        try:
            # 消息ID验证
            if event.message_id <= 0:
                return False
            
            # 用户ID验证
            if event.user_id <= 0:
                return False
            
            # 消息内容验证
            if not event.message or len(event.message) == 0:
                return False
            
            # 群消息特殊验证
            if isinstance(event, GroupMessageEvent):
                if event.group_id <= 0:
                    return False
            
            return True
        except Exception:
            return False
