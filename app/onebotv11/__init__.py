"""
OneBot v11协议解析模块
完整实现OneBot v11标准的消息解析、事件处理和API调用
"""

from .models import (
    # 基础模型
    PostType, MessageType, NoticeType, RequestType, Role, Sex,
    MessageSegmentType, BaseEvent, Sender, MessageSegment,

    # 消息事件
    MessageEvent, PrivateMessageEvent, GroupMessageEvent,
    MessageSentEvent, PrivateMessageSentEvent, GroupMessageSentEvent,

    # 通知事件
    NoticeEvent, GroupUploadNotice, GroupAdminNotice,
    GroupDecreaseNotice, GroupIncreaseNotice, GroupBanNotice,
    FriendAddNotice, GroupRecallNotice, FriendRecallNotice,
    PokeNotifyEvent,

    # 请求事件
    RequestEvent, FriendRequestEvent, GroupRequestEvent,

    # 元事件
    MetaEvent, LifecycleMetaEvent, HeartbeatMetaEvent,

    # API相关
    ApiRequest, ApiResponse,

    # 联合类型
    Event
)

from .event_parser import EventParser, MessageNormalizer, EventValidator
from .message_segment import MessageSegmentBuilder, MessageSegmentParser
from .api_handler import ApiHandler

__all__ = [
    # 基础类型
    "PostType", "MessageType", "NoticeType", "RequestType", "Role", "Sex",
    "MessageSegmentType", "BaseEvent", "Sender", "MessageSegment",

    # 事件类型
    "Event", "MessageEvent", "PrivateMessageEvent", "GroupMessageEvent",
    "MessageSentEvent", "PrivateMessageSentEvent", "GroupMessageSentEvent",
    "NoticeEvent", "GroupUploadNotice", "GroupAdminNotice",
    "GroupDecreaseNotice", "GroupIncreaseNotice", "GroupBanNotice",
    "FriendAddNotice", "GroupRecallNotice", "FriendRecallNotice",
    "PokeNotifyEvent", "RequestEvent", "FriendRequestEvent", "GroupRequestEvent",
    "MetaEvent", "LifecycleMetaEvent", "HeartbeatMetaEvent",

    # API相关
    "ApiRequest", "ApiResponse",

    # 工具类
    "EventParser", "MessageNormalizer", "EventValidator",
    "MessageSegmentBuilder", "MessageSegmentParser", "ApiHandler"
]
