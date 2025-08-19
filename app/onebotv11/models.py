"""
OneBot v11 数据模型
定义所有OneBot v11协议相关的数据结构
"""

from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# 基础枚举类型
class PostType(str, Enum):
    """事件类型"""
    MESSAGE = "message"
    MESSAGE_SENT = "message_sent" # napcat
    NOTICE = "notice"
    REQUEST = "request"
    META_EVENT = "meta_event"

class MessageType(str, Enum):
    """消息类型"""
    PRIVATE = "private"
    GROUP = "group"

class NoticeType(str, Enum):
    """通知类型"""
    GROUP_UPLOAD = "group_upload"
    GROUP_ADMIN = "group_admin"
    GROUP_DECREASE = "group_decrease"
    GROUP_INCREASE = "group_increase"
    GROUP_BAN = "group_ban"
    FRIEND_ADD = "friend_add"
    GROUP_RECALL = "group_recall"
    FRIEND_RECALL = "friend_recall"
    NOTIFY = "notify"

class RequestType(str, Enum):
    """请求类型"""
    FRIEND = "friend"
    GROUP = "group"

class Role(str, Enum):
    """用户角色"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class Sex(str, Enum):
    """性别"""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"

# 消息段类型
class MessageSegmentType(str, Enum):
    """消息段类型"""
    TEXT = "text"
    FACE = "face"
    IMAGE = "image"
    RECORD = "record"
    VIDEO = "video"
    AT = "at"
    RPS = "rps"
    DICE = "dice"
    SHAKE = "shake"
    POKE = "poke"
    ANONYMOUS = "anonymous"
    SHARE = "share"
    CONTACT = "contact"
    LOCATION = "location"
    MUSIC = "music"
    REPLY = "reply"
    FORWARD = "forward"
    NODE = "node"
    XML = "xml"
    JSON = "json"
    FILE = "file"
    MARKDOWN = "markdown"

# 基础模型
class BaseEvent(BaseModel):
    """事件基类"""
    time: int = Field(..., description="事件发生的时间戳")
    self_id: int = Field(..., description="收到事件的机器人QQ号")
    post_type: PostType = Field(..., description="事件类型")

class Sender(BaseModel):
    """发送者信息"""
    user_id: int = Field(..., description="发送者QQ号")
    nickname: str = Field("", description="昵称")
    card: str = Field("", description="群名片/备注")
    sex: Optional[Sex] = Field(None, description="性别")
    age: Optional[int] = Field(None, description="年龄")
    area: Optional[str] = Field(None, description="地区")
    level: Optional[str] = Field(None, description="成员等级")
    role: Optional[Role] = Field(None, description="角色")
    title: Optional[str] = Field(None, description="专属头衔")

class MessageSegment(BaseModel):
    """消息段"""
    type: MessageSegmentType = Field(..., description="消息段类型")
    data: Dict[str, Any] = Field(default_factory=dict, description="消息段数据")

# 消息事件
class MessageEvent(BaseEvent):
    """消息事件基类"""
    post_type: Literal[PostType.MESSAGE] = PostType.MESSAGE
    message_type: MessageType = Field(..., description="消息类型")
    sub_type: str = Field(..., description="消息子类型")
    message_id: int = Field(..., description="消息ID")
    user_id: int = Field(..., description="发送者QQ号")
    message: List[MessageSegment] = Field(..., description="消息内容")
    raw_message: str = Field(..., description="原始消息内容")
    font: int = Field(0, description="字体")
    sender: Sender = Field(..., description="发送者信息")

class PrivateMessageEvent(MessageEvent):
    """私聊消息事件"""
    message_type: Literal[MessageType.PRIVATE] = MessageType.PRIVATE
    sub_type: Literal["friend", "group", "other"] = Field(..., description="私聊类型")
    temp_source: Optional[int] = Field(None, description="临时会话来源")

class GroupMessageEvent(MessageEvent):
    """群消息事件"""
    message_type: Literal[MessageType.GROUP] = MessageType.GROUP
    sub_type: Literal["normal", "anonymous", "notice"] = Field(..., description="群消息类型")
    group_id: int = Field(..., description="群号")
    anonymous: Optional[Dict[str, Any]] = Field(None, description="匿名信息")
    
# 发送事件
class MessageSentEvent(MessageEvent):
    """消息发送事件基类"""
    post_type: Literal[PostType.MESSAGE_SENT] = PostType.MESSAGE_SENT
    message_type: MessageType = Field(..., description="消息类型")
    sub_type: str = Field(..., description="消息子类型")
    message_id: int = Field(..., description="消息ID")
    user_id: int = Field(..., description="发送者QQ号")
    message: List[MessageSegment] = Field(..., description="消息内容")
    raw_message: str = Field(..., description="原始消息内容")
    font: int = Field(0, description="字体")
    sender: Sender = Field(..., description="发送者信息")

class PrivateMessageSentEvent(MessageSentEvent, PrivateMessageEvent):
    """私聊消息发送事件"""
    message_type: Literal[MessageType.PRIVATE] = MessageType.PRIVATE
    sub_type: Literal["friend", "group", "other"] = Field(..., description="私聊类型")
    temp_source: Optional[int] = Field(None, description="临时会话来源")
    message_sent_type: Literal["self", "other"] = Field(..., description="消息发送类型")

class GroupMessageSentEvent(MessageSentEvent, GroupMessageEvent):
    """群消息发送事件"""
    message_type: Literal[MessageType.GROUP] = MessageType.GROUP
    sub_type: Literal["normal", "anonymous", "notice"] = Field(..., description="群消息类型")
    group_id: int = Field(..., description="群号")
    anonymous: Optional[Dict[str, Any]] = Field(None, description="匿名信息")
    message_sent_type: Literal["self", "other"] = Field(..., description="消息发送类型")

# 通知事件
class NoticeEvent(BaseEvent):
    """通知事件基类"""
    post_type: Literal[PostType.NOTICE] = PostType.NOTICE
    notice_type: NoticeType = Field(..., description="通知类型")

class GroupUploadNotice(NoticeEvent):
    """群文件上传通知"""
    notice_type: Literal[NoticeType.GROUP_UPLOAD] = NoticeType.GROUP_UPLOAD
    group_id: int = Field(..., description="群号")
    user_id: int = Field(..., description="发送者QQ号")
    file: Dict[str, Any] = Field(..., description="文件信息")

class GroupAdminNotice(NoticeEvent):
    """群管理员变动通知"""
    notice_type: Literal[NoticeType.GROUP_ADMIN] = NoticeType.GROUP_ADMIN
    sub_type: Literal["set", "unset"] = Field(..., description="事件子类型")
    group_id: int = Field(..., description="群号")
    user_id: int = Field(..., description="管理员QQ号")

class GroupDecreaseNotice(NoticeEvent):
    """群成员减少通知"""
    notice_type: Literal[NoticeType.GROUP_DECREASE] = NoticeType.GROUP_DECREASE
    sub_type: Literal["leave", "kick", "kick_me"] = Field(..., description="事件子类型")
    group_id: int = Field(..., description="群号")
    operator_id: int = Field(..., description="操作者QQ号")
    user_id: int = Field(..., description="离开者QQ号")

class GroupIncreaseNotice(NoticeEvent):
    """群成员增加通知"""
    notice_type: Literal[NoticeType.GROUP_INCREASE] = NoticeType.GROUP_INCREASE
    sub_type: Literal["approve", "invite"] = Field(..., description="事件子类型")
    group_id: int = Field(..., description="群号")
    operator_id: int = Field(..., description="操作者QQ号")
    user_id: int = Field(..., description="加入者QQ号")

class GroupBanNotice(NoticeEvent):
    """群禁言通知"""
    notice_type: Literal[NoticeType.GROUP_BAN] = NoticeType.GROUP_BAN
    sub_type: Literal["ban", "lift_ban"] = Field(..., description="事件子类型")
    group_id: int = Field(..., description="群号")
    operator_id: int = Field(..., description="操作者QQ号")
    user_id: int = Field(..., description="被禁言QQ号")
    duration: int = Field(..., description="禁言时长")

class FriendAddNotice(NoticeEvent):
    """好友添加通知"""
    notice_type: Literal[NoticeType.FRIEND_ADD] = NoticeType.FRIEND_ADD
    user_id: int = Field(..., description="新添加好友QQ号")

class GroupRecallNotice(NoticeEvent):
    """群消息撤回通知"""
    notice_type: Literal[NoticeType.GROUP_RECALL] = NoticeType.GROUP_RECALL
    group_id: int = Field(..., description="群号")
    user_id: int = Field(..., description="消息发送者QQ号")
    operator_id: int = Field(..., description="操作者QQ号")
    message_id: int = Field(..., description="被撤回的消息ID")

class FriendRecallNotice(NoticeEvent):
    """好友消息撤回通知"""
    notice_type: Literal[NoticeType.FRIEND_RECALL] = NoticeType.FRIEND_RECALL
    user_id: int = Field(..., description="好友QQ号")
    message_id: int = Field(..., description="被撤回的消息ID")

class PokeNotifyEvent(NoticeEvent):
    """戳一戳通知"""
    notice_type: Literal[NoticeType.NOTIFY] = NoticeType.NOTIFY
    sub_type: Literal["poke"] = "poke"
    group_id: Optional[int] = Field(None, description="群号")
    user_id: int = Field(..., description="发送者QQ号")
    target_id: int = Field(..., description="被戳者QQ号")

# 请求事件
class RequestEvent(BaseEvent):
    """请求事件基类"""
    post_type: Literal[PostType.REQUEST] = PostType.REQUEST
    request_type: RequestType = Field(..., description="请求类型")

class FriendRequestEvent(RequestEvent):
    """加好友请求"""
    request_type: Literal[RequestType.FRIEND] = RequestType.FRIEND
    user_id: int = Field(..., description="发送请求的QQ号")
    comment: str = Field(..., description="验证信息")
    flag: str = Field(..., description="请求flag")

class GroupRequestEvent(RequestEvent):
    """加群请求/群邀请"""
    request_type: Literal[RequestType.GROUP] = RequestType.GROUP
    sub_type: Literal["add", "invite"] = Field(..., description="请求子类型")
    group_id: int = Field(..., description="群号")
    user_id: int = Field(..., description="发送请求的QQ号")
    comment: str = Field(..., description="验证信息")
    flag: str = Field(..., description="请求flag")

# 元事件
class MetaEvent(BaseEvent):
    """元事件基类"""
    post_type: Literal[PostType.META_EVENT] = PostType.META_EVENT
    meta_event_type: str = Field(..., description="元事件类型")

class LifecycleMetaEvent(MetaEvent):
    """生命周期元事件"""
    meta_event_type: Literal["lifecycle"] = "lifecycle"
    sub_type: Literal["enable", "disable", "connect"] = Field(..., description="事件子类型")

class HeartbeatMetaEvent(MetaEvent):
    """心跳元事件"""
    meta_event_type: Literal["heartbeat"] = "heartbeat"
    status: Dict[str, Any] = Field(..., description="状态信息")
    interval: int = Field(..., description="心跳间隔")

# API相关模型
class ApiRequest(BaseModel):
    """API请求"""
    action: str = Field(..., description="API动作")
    params: Dict[str, Any] = Field(default_factory=dict, description="参数")
    echo: Optional[str|dict] = Field(None, description="回声")

class ApiResponse(BaseModel):
    """API响应"""
    status: Literal["ok", "async", "failed"] = Field(..., description="状态")
    retcode: int = Field(..., description="返回码")
    data: Optional[Dict[str, Any]|List[Dict[str, Any]]] = Field(None, description="数据")
    message: Optional[str] = Field(None, description="信息")
    wording: Optional[str] = Field(None, description="暂时不知道是什么")
    echo: Optional[str|dict|int] = Field(None, description="回声")

# 联合类型
Event = Union[
    PrivateMessageEvent,
    PrivateMessageSentEvent,
    GroupMessageEvent,
    GroupMessageSentEvent,
    GroupUploadNotice,
    GroupAdminNotice,
    GroupDecreaseNotice,
    GroupIncreaseNotice,
    GroupBanNotice,
    FriendAddNotice,
    GroupRecallNotice,
    FriendRecallNotice,
    PokeNotifyEvent,
    FriendRequestEvent,
    GroupRequestEvent,
    LifecycleMetaEvent,
    HeartbeatMetaEvent
]
