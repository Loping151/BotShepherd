"""
OneBot v11 API处理器
处理各种OneBot API调用
"""

from typing import Dict, Any, List, Optional, Union
import uuid
from .models import ApiRequest, ApiResponse, MessageSegment
from .message_segment import MessageSegmentBuilder

class ApiHandler:
    """API处理器"""
    
    @staticmethod
    def create_send_private_msg_request(user_id: Union[int, str], 
                                      message: Union[str, List[MessageSegment]],
                                      auto_escape: bool = False) -> ApiRequest:
        """创建发送私聊消息请求"""
        if isinstance(message, str):
            message_data = [{"type": "text", "data": {"text": message}}]
        else:
            message_data = [seg.model_dump() for seg in message]
        
        return ApiRequest(
            action="send_private_msg",
            params={
                "user_id": int(user_id),
                "message": message_data,
                "auto_escape": auto_escape
            },
            echo=uuid.uuid4().hex
        )
        
    @staticmethod
    def create_send_private_forward_msg_request(user_id: Union[int, str],
                                              messages: List[Union[str, List[MessageSegment]]]) -> ApiRequest:
        """创建发送私聊合并转发消息请求"""
        message_data = []
        for message in messages:
            if isinstance(message, str):
                message_data.append({"type": "text", "data": {"text": message}})
            else:
                message_data.append({"type": "node", "data": {"content": [seg.model_dump() for seg in message]}})
        
        return ApiRequest(
            action="send_private_forward_msg",
            params={
                "user_id": int(user_id),
                "messages": message_data
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_send_group_msg_request(group_id: Union[int, str],
                                    message: Union[str, List[MessageSegment]],
                                    auto_escape: bool = False) -> ApiRequest:
        """创建发送群消息请求"""
        if isinstance(message, str):
            message_data = [{"type": "text", "data": {"text": message}}]
        else:
            message_data = [seg.model_dump() for seg in message]
        
        return ApiRequest(
            action="send_group_msg",
            params={
                "group_id": int(group_id),
                "message": message_data,
                "auto_escape": auto_escape
            },
            echo=uuid.uuid4().hex
        )
        
    @staticmethod
    def create_send_group_forward_msg_request(group_id: Union[int, str],
                                            messages: List[Union[str, List[MessageSegment]]]) -> ApiRequest:
        """创建发送群合并转发消息请求"""
        message_data = []
        for message in messages:
            if isinstance(message, str):
                message_data.append({"type": "text", "data": {"text": message}})
            else:
                message_data.append({"type": "node", "data": {"content": [seg.model_dump() for seg in message]}})
        
        return ApiRequest(
            action="send_group_forward_msg",
            params={
                "group_id": int(group_id),
                "messages": message_data
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_send_msg_request(message_type: str,
                              user_id: Optional[Union[int, str]] = None,
                              group_id: Optional[Union[int, str]] = None,
                              message: Union[str, List[MessageSegment]] = "",
                              auto_escape: bool = False) -> ApiRequest:
        """创建发送消息请求（通用）"""
        if isinstance(message, str):
            message_data = [{"type": "text", "data": {"text": message}}]
        else:
            message_data = [seg.model_dump() for seg in message]
        
        params = {
            "message_type": message_type,
            "message": message_data,
            "auto_escape": auto_escape
        }
        
        if user_id is not None:
            params["user_id"] = int(user_id)
        if group_id is not None:
            params["group_id"] = int(group_id)
        
        return ApiRequest(
            action="send_msg",
            params=params,
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_delete_msg_request(message_id: Union[int, str]) -> ApiRequest:
        """创建撤回消息请求"""
        return ApiRequest(
            action="delete_msg",
            params={"message_id": int(message_id)},
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_msg_request(message_id: Union[int, str]) -> ApiRequest:
        """创建获取消息请求"""
        return ApiRequest(
            action="get_msg",
            params={"message_id": int(message_id)},
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_forward_msg_request(id: str) -> ApiRequest:
        """创建获取合并转发消息请求"""
        return ApiRequest(
            action="get_forward_msg",
            params={"id": id},
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_send_like_request(user_id: Union[int, str], times: int = 1) -> ApiRequest:
        """创建发送好友赞请求"""
        return ApiRequest(
            action="send_like",
            params={
                "user_id": int(user_id),
                "times": times
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_kick_request(group_id: Union[int, str],
                                    user_id: Union[int, str],
                                    reject_add_request: bool = False) -> ApiRequest:
        """创建群组踢人请求"""
        return ApiRequest(
            action="set_group_kick",
            params={
                "group_id": int(group_id),
                "user_id": int(user_id),
                "reject_add_request": reject_add_request
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_ban_request(group_id: Union[int, str],
                                   user_id: Union[int, str],
                                   duration: int = 30 * 60) -> ApiRequest:
        """创建群组单人禁言请求"""
        return ApiRequest(
            action="set_group_ban",
            params={
                "group_id": int(group_id),
                "user_id": int(user_id),
                "duration": duration
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_anonymous_ban_request(group_id: Union[int, str],
                                             anonymous: Dict[str, Any],
                                             duration: int = 30 * 60) -> ApiRequest:
        """创建群组匿名用户禁言请求"""
        return ApiRequest(
            action="set_group_anonymous_ban",
            params={
                "group_id": int(group_id),
                "anonymous": anonymous,
                "duration": duration
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_whole_ban_request(group_id: Union[int, str],
                                         enable: bool = True) -> ApiRequest:
        """创建群组全员禁言请求"""
        return ApiRequest(
            action="set_group_whole_ban",
            params={
                "group_id": int(group_id),
                "enable": enable
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_admin_request(group_id: Union[int, str],
                                     user_id: Union[int, str],
                                     enable: bool = True) -> ApiRequest:
        """创建群组设置管理员请求"""
        return ApiRequest(
            action="set_group_admin",
            params={
                "group_id": int(group_id),
                "user_id": int(user_id),
                "enable": enable
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_anonymous_request(group_id: Union[int, str],
                                         enable: bool = True) -> ApiRequest:
        """创建群组匿名请求"""
        return ApiRequest(
            action="set_group_anonymous",
            params={
                "group_id": int(group_id),
                "enable": enable
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_card_request(group_id: Union[int, str],
                                    user_id: Union[int, str],
                                    card: str = "") -> ApiRequest:
        """创建设置群名片请求"""
        return ApiRequest(
            action="set_group_card",
            params={
                "group_id": int(group_id),
                "user_id": int(user_id),
                "card": card
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_name_request(group_id: Union[int, str],
                                    group_name: str) -> ApiRequest:
        """创建设置群名请求"""
        return ApiRequest(
            action="set_group_name",
            params={
                "group_id": int(group_id),
                "group_name": group_name
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_leave_request(group_id: Union[int, str],
                                     is_dismiss: bool = False) -> ApiRequest:
        """创建退出群组请求"""
        return ApiRequest(
            action="set_group_leave",
            params={
                "group_id": int(group_id),
                "is_dismiss": is_dismiss
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_special_title_request(group_id: Union[int, str],
                                             user_id: Union[int, str],
                                             special_title: str = "",
                                             duration: int = -1) -> ApiRequest:
        """创建设置群组专属头衔请求"""
        return ApiRequest(
            action="set_group_special_title",
            params={
                "group_id": int(group_id),
                "user_id": int(user_id),
                "special_title": special_title,
                "duration": duration
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_friend_add_request(flag: str, approve: bool = True,
                                    remark: str = "") -> ApiRequest:
        """创建处理加好友请求"""
        return ApiRequest(
            action="set_friend_add_request",
            params={
                "flag": flag,
                "approve": approve,
                "remark": remark
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_set_group_add_request(flag: str, sub_type: str,
                                   approve: bool = True,
                                   reason: str = "") -> ApiRequest:
        """创建处理加群请求/邀请"""
        return ApiRequest(
            action="set_group_add_request",
            params={
                "flag": flag,
                "sub_type": sub_type,
                "approve": approve,
                "reason": reason
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_login_info_request() -> ApiRequest:
        """创建获取登录号信息请求"""
        return ApiRequest(action="get_login_info")
    
    @staticmethod
    def create_get_stranger_info_request(user_id: Union[int, str],
                                       no_cache: bool = False) -> ApiRequest:
        """创建获取陌生人信息请求"""
        return ApiRequest(
            action="get_stranger_info",
            params={
                "user_id": int(user_id),
                "no_cache": no_cache
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_friend_list_request() -> ApiRequest:
        """创建获取好友列表请求"""
        return ApiRequest(action="get_friend_list")
    
    @staticmethod
    def create_get_group_info_request(group_id: Union[int, str],
                                    no_cache: bool = False) -> ApiRequest:
        """创建获取群信息请求"""
        return ApiRequest(
            action="get_group_info",
            params={
                "group_id": int(group_id),
                "no_cache": no_cache
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_group_list_request() -> ApiRequest:
        """创建获取群列表请求"""
        return ApiRequest(action="get_group_list")
    
    @staticmethod
    def create_get_group_member_info_request(group_id: Union[int, str],
                                           user_id: Union[int, str],
                                           no_cache: bool = False) -> ApiRequest:
        """创建获取群成员信息请求"""
        return ApiRequest(
            action="get_group_member_info",
            params={
                "group_id": int(group_id),
                "user_id": int(user_id),
                "no_cache": no_cache
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_group_member_list_request(group_id: Union[int, str]) -> ApiRequest:
        """创建获取群成员列表请求"""
        return ApiRequest(
            action="get_group_member_list",
            params={"group_id": int(group_id)}
        )
    
    @staticmethod
    def create_get_group_honor_info_request(group_id: Union[int, str],
                                          type: str) -> ApiRequest:
        """创建获取群荣誉信息请求"""
        return ApiRequest(
            action="get_group_honor_info",
            params={
                "group_id": int(group_id),
                "type": type
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_cookies_request(domain: str = "") -> ApiRequest:
        """创建获取Cookies请求"""
        return ApiRequest(
            action="get_cookies",
            params={"domain": domain},
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_csrf_token_request() -> ApiRequest:
        """创建获取CSRF Token请求"""
        return ApiRequest(action="get_csrf_token", echo=uuid.uuid4().hex)
    
    @staticmethod
    def create_get_credentials_request(domain: str = "") -> ApiRequest:
        """创建获取QQ相关接口凭证请求"""
        return ApiRequest(
            action="get_credentials",
            params={"domain": domain},
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_record_request(file: str, out_format: str) -> ApiRequest:
        """创建获取语音请求"""
        return ApiRequest(
            action="get_record",
            params={
                "file": file,
                "out_format": out_format
            },
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_get_image_request(file: str) -> ApiRequest:
        """创建获取图片请求"""
        return ApiRequest(
            action="get_image",
            params={"file": file},
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_can_send_image_request() -> ApiRequest:
        """创建检查是否可以发送图片请求"""
        return ApiRequest(action="can_send_image", echo=uuid.uuid4().hex)
    
    @staticmethod
    def create_can_send_record_request() -> ApiRequest:
        """创建检查是否可以发送语音请求"""
        return ApiRequest(action="can_send_record", echo=uuid.uuid4().hex)
    
    @staticmethod
    def create_get_status_request() -> ApiRequest:
        """创建获取运行状态请求"""
        return ApiRequest(action="get_status", echo=uuid.uuid4().hex)
    
    @staticmethod
    def create_get_version_info_request() -> ApiRequest:
        """创建获取版本信息请求"""
        return ApiRequest(action="get_version_info", echo=uuid.uuid4().hex)
    
    @staticmethod
    def create_set_restart_request(delay: int = 0) -> ApiRequest:
        """创建重启OneBot实现请求"""
        return ApiRequest(
            action="set_restart",
            params={"delay": delay},
            echo=uuid.uuid4().hex
        )
    
    @staticmethod
    def create_clean_cache_request() -> ApiRequest:
        """创建清理缓存请求"""
        return ApiRequest(action="clean_cache", echo=uuid.uuid4().hex)
