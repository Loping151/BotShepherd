"""
OneBot v11 API调用相关类
参考nonebot2的实现
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
import json
import uuid
import asyncio
import websockets
from datetime import datetime

from .message import Message, MessageSegment


@dataclass
class ApiResponse:
    """API响应"""
    status: str  # ok, failed
    retcode: int
    data: Any = None
    echo: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApiResponse':
        return cls(
            status=data.get("status", "failed"),
            retcode=data.get("retcode", -1),
            data=data.get("data"),
            echo=data.get("echo")
        )
    
    def is_success(self) -> bool:
        """是否成功"""
        return self.status == "ok" and self.retcode == 0


@dataclass
class ApiRequest:
    """API请求"""
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    echo: Optional[str] = None
    
    def __post_init__(self):
        if self.echo is None:
            self.echo = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "action": self.action,
            "params": self.params
        }
        if self.echo:
            result["echo"] = self.echo
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class BotAPI:
    """Bot API调用类"""
    
    def __init__(self, websocket_connections: Dict[str, Any]):
        """
        初始化API调用器
        websocket_connections: 目标端点的websocket连接字典
        """
        self.connections = websocket_connections
        self.pending_requests: Dict[str, asyncio.Future] = {}
    
    async def call_api(self, action: str, params: Dict[str, Any] = None, 
                      target_endpoint: str = None, timeout: float = 30.0) -> ApiResponse:
        """
        调用API
        
        Args:
            action: API动作名
            params: 参数
            target_endpoint: 目标端点，如果为None则发送到所有连接
            timeout: 超时时间
        """
        if params is None:
            params = {}
        
        request = ApiRequest(action=action, params=params)
        
        # 创建Future等待响应
        future = asyncio.Future()
        self.pending_requests[request.echo] = future
        
        try:
            # 发送请求
            if target_endpoint and target_endpoint in self.connections:
                # 发送到指定端点
                await self.connections[target_endpoint].send(request.to_json())
            else:
                # 发送到所有连接（取第一个响应）
                for connection in self.connections.values():
                    await connection.send(request.to_json())
            
            # 等待响应
            response_data = await asyncio.wait_for(future, timeout=timeout)
            return ApiResponse.from_dict(response_data)
            
        except asyncio.TimeoutError:
            return ApiResponse(status="failed", retcode=-1, data="Request timeout")
        except Exception as e:
            return ApiResponse(status="failed", retcode=-1, data=str(e))
        finally:
            # 清理pending request
            if request.echo in self.pending_requests:
                del self.pending_requests[request.echo]
    
    def handle_api_response(self, response_data: Dict[str, Any]):
        """处理API响应"""
        echo = response_data.get("echo")
        if echo and echo in self.pending_requests:
            future = self.pending_requests[echo]
            if not future.done():
                future.set_result(response_data)
    
    # 消息发送相关API
    async def send_private_msg(self, user_id: int, message: Union[str, Message, List[MessageSegment]], 
                              auto_escape: bool = False, target_endpoint: str = None) -> ApiResponse:
        """发送私聊消息"""
        if isinstance(message, str):
            message_data = message
        elif isinstance(message, Message):
            message_data = message.to_list()
        elif isinstance(message, list):
            message_data = [seg.to_dict() if isinstance(seg, MessageSegment) else seg for seg in message]
        else:
            message_data = str(message)
        
        params = {
            "user_id": user_id,
            "message": message_data,
            "auto_escape": auto_escape
        }
        
        return await self.call_api("send_private_msg", params, target_endpoint)
    
    async def send_group_msg(self, group_id: int, message: Union[str, Message, List[MessageSegment]], 
                            auto_escape: bool = False, target_endpoint: str = None) -> ApiResponse:
        """发送群消息"""
        if isinstance(message, str):
            message_data = message
        elif isinstance(message, Message):
            message_data = message.to_list()
        elif isinstance(message, list):
            message_data = [seg.to_dict() if isinstance(seg, MessageSegment) else seg for seg in message]
        else:
            message_data = str(message)
        
        params = {
            "group_id": group_id,
            "message": message_data,
            "auto_escape": auto_escape
        }
        
        return await self.call_api("send_group_msg", params, target_endpoint)
    
    async def send_msg(self, message_type: str, user_id: Optional[int] = None, 
                      group_id: Optional[int] = None, message: Union[str, Message, List[MessageSegment]] = None,
                      auto_escape: bool = False, target_endpoint: str = None) -> ApiResponse:
        """发送消息（通用）"""
        if isinstance(message, str):
            message_data = message
        elif isinstance(message, Message):
            message_data = message.to_list()
        elif isinstance(message, list):
            message_data = [seg.to_dict() if isinstance(seg, MessageSegment) else seg for seg in message]
        else:
            message_data = str(message)
        
        params = {
            "message_type": message_type,
            "message": message_data,
            "auto_escape": auto_escape
        }
        
        if user_id is not None:
            params["user_id"] = user_id
        if group_id is not None:
            params["group_id"] = group_id
        
        return await self.call_api("send_msg", params, target_endpoint)
    
    async def delete_msg(self, message_id: int, target_endpoint: str = None) -> ApiResponse:
        """撤回消息"""
        params = {"message_id": message_id}
        return await self.call_api("delete_msg", params, target_endpoint)

    # 转发消息相关API
    async def send_forward_msg(self, message_type: str, messages: List[Dict[str, Any]],
                              user_id: Optional[int] = None, group_id: Optional[int] = None,
                              target_endpoint: str = None) -> ApiResponse:
        """发送转发消息"""
        params = {
            "message_type": message_type,
            "messages": messages
        }

        if user_id is not None:
            params["user_id"] = user_id
        if group_id is not None:
            params["group_id"] = group_id

        return await self.call_api("send_forward_msg", params, target_endpoint)

    async def send_group_forward_msg(self, group_id: int, messages: List[Dict[str, Any]],
                                    target_endpoint: str = None) -> ApiResponse:
        """发送群转发消息"""
        return await self.send_forward_msg("group", messages, group_id=group_id, target_endpoint=target_endpoint)

    async def send_private_forward_msg(self, user_id: int, messages: List[Dict[str, Any]],
                                      target_endpoint: str = None) -> ApiResponse:
        """发送私聊转发消息"""
        return await self.send_forward_msg("private", messages, user_id=user_id, target_endpoint=target_endpoint)

    # 群管理相关API
    async def set_group_kick(self, group_id: int, user_id: int, reject_add_request: bool = False,
                            target_endpoint: str = None) -> ApiResponse:
        """群组踢人"""
        params = {
            "group_id": group_id,
            "user_id": user_id,
            "reject_add_request": reject_add_request
        }
        return await self.call_api("set_group_kick", params, target_endpoint)

    async def set_group_ban(self, group_id: int, user_id: int, duration: int = 30 * 60,
                           target_endpoint: str = None) -> ApiResponse:
        """群组单人禁言"""
        params = {
            "group_id": group_id,
            "user_id": user_id,
            "duration": duration
        }
        return await self.call_api("set_group_ban", params, target_endpoint)

    async def set_group_whole_ban(self, group_id: int, enable: bool = True,
                                 target_endpoint: str = None) -> ApiResponse:
        """群组全员禁言"""
        params = {
            "group_id": group_id,
            "enable": enable
        }
        return await self.call_api("set_group_whole_ban", params, target_endpoint)

    # 信息获取相关API
    async def get_login_info(self, target_endpoint: str = None) -> ApiResponse:
        """获取登录号信息"""
        return await self.call_api("get_login_info", {}, target_endpoint)

    async def get_stranger_info(self, user_id: int, no_cache: bool = False,
                               target_endpoint: str = None) -> ApiResponse:
        """获取陌生人信息"""
        params = {
            "user_id": user_id,
            "no_cache": no_cache
        }
        return await self.call_api("get_stranger_info", params, target_endpoint)

    async def get_friend_list(self, target_endpoint: str = None) -> ApiResponse:
        """获取好友列表"""
        return await self.call_api("get_friend_list", {}, target_endpoint)

    async def get_group_info(self, group_id: int, no_cache: bool = False,
                            target_endpoint: str = None) -> ApiResponse:
        """获取群信息"""
        params = {
            "group_id": group_id,
            "no_cache": no_cache
        }
        return await self.call_api("get_group_info", params, target_endpoint)

    async def get_group_list(self, target_endpoint: str = None) -> ApiResponse:
        """获取群列表"""
        return await self.call_api("get_group_list", {}, target_endpoint)

    async def get_group_member_info(self, group_id: int, user_id: int, no_cache: bool = False,
                                   target_endpoint: str = None) -> ApiResponse:
        """获取群成员信息"""
        params = {
            "group_id": group_id,
            "user_id": user_id,
            "no_cache": no_cache
        }
        return await self.call_api("get_group_member_info", params, target_endpoint)

    async def get_group_member_list(self, group_id: int, target_endpoint: str = None) -> ApiResponse:
        """获取群成员列表"""
        params = {"group_id": group_id}
        return await self.call_api("get_group_member_list", params, target_endpoint)

    async def get_msg(self, message_id: int, target_endpoint: str = None) -> ApiResponse:
        """获取消息"""
        params = {"message_id": message_id}
        return await self.call_api("get_msg", params, target_endpoint)


class ForwardMessageBuilder:
    """转发消息构造器"""

    @staticmethod
    def create_forward_node(user_id: int, nickname: str, content: Union[str, Message, List[MessageSegment]]) -> Dict[str, Any]:
        """创建转发消息节点"""
        if isinstance(content, str):
            message_data = content
        elif isinstance(content, Message):
            message_data = content.to_list()
        elif isinstance(content, list):
            message_data = [seg.to_dict() if isinstance(seg, MessageSegment) else seg for seg in content]
        else:
            message_data = str(content)

        return {
            "type": "node",
            "data": {
                "user_id": user_id,
                "nickname": nickname,
                "content": message_data
            }
        }

    @staticmethod
    def create_forward_message(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """创建转发消息"""
        return nodes


# 预留消息处理函数区域
class MessageProcessor:
    """消息处理器 - 预留给后续JSON操作处理函数"""

    def __init__(self):
        # TODO: 在这里添加消息处理相关的初始化
        pass

    async def process_incoming_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理传入的消息
        预留给后续实现的消息处理逻辑
        """
        # TODO: 实现消息过滤、统计、转换等逻辑
        return message_data

    async def process_outgoing_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理发出的消息
        预留给后续实现的消息处理逻辑
        """
        # TODO: 实现消息过滤、转换等逻辑
        return message_data

    def apply_forbidden_word_filter(self, message: str, forbidden_words: List[str]) -> str:
        """
        应用违禁词过滤
        预留给后续实现
        """
        # TODO: 实现违禁词过滤逻辑
        return message

    def apply_command_alias(self, message: str, alias_dict: Dict[str, List[str]]) -> str:
        """
        应用指令别名替换
        预留给后续实现
        """
        # TODO: 实现指令别名替换逻辑
        return message

    def add_anti_trigger_prefix(self, message: str, trigger_words: List[str]) -> str:
        """
        添加防误触前缀
        预留给后续实现
        """
        # TODO: 实现防误触前缀添加逻辑
        return message
