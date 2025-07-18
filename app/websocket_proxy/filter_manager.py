"""
过滤管理器
处理消息过滤和内容检查
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from ..onebotv11.models import Event, PrivateMessageEvent, GroupMessageEvent
from ..onebotv11.message_segment import MessageSegmentParser
from ..commands.permission_manager import PermissionManager, PermissionLevel

class FilterAction(Enum):
    """过滤动作"""
    BLOCK = "block"      # 阻止消息
    MODIFY = "modify"    # 修改消息
    WARN = "warn"        # 警告但通过
    PASS = "pass"        # 通过

class FilterType(Enum):
    """过滤类型"""
    BLACKLIST = "blacklist"
    RECEIVE_FILTER = "receive_filter"
    SEND_FILTER = "send_filter"
    PREFIX_PROTECTION = "prefix_protection"
    GROUP_FILTER = "group_filter"

class FilterManager:
    """过滤管理器"""
    
    def __init__(self, config_manager, permission_manager: PermissionManager, logger):
        self.config_manager = config_manager
        self.permission_manager = permission_manager
        self.logger = logger
    
    async def filter_receive_message(self, event: Event, 
                                   message_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """过滤接收消息"""
        try:
            # 超级用户消息绕过过滤
            if self.permission_manager.bypass_whitelist_check(event):
                return True, "超级用户绕过", message_data
            
            # 检查全局接收过滤词
            if isinstance(event, (PrivateMessageEvent, GroupMessageEvent)):
                filtered, reason, modified_data = await self._apply_global_receive_filters(event, message_data)
                if not filtered:
                    return False, reason, modified_data
                message_data = modified_data
                
                # 检查群组过滤词
                if isinstance(event, GroupMessageEvent):
                    filtered, reason, modified_data = await self._apply_group_filters(event, message_data)
                    if not filtered:
                        return False, reason, modified_data
                    message_data = modified_data
            
            return True, "通过过滤", message_data
            
        except Exception as e:
            self.logger.error(f"过滤接收消息失败: {e}")
            return True, "过滤器错误，默认通过", message_data
    
    async def filter_send_message(self, event: Event, 
                                message_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """过滤发送消息"""
        try:
            # 检查全局发送过滤词
            if isinstance(event, (PrivateMessageEvent, GroupMessageEvent)):
                filtered, reason, modified_data = await self._apply_global_send_filters(event, message_data)
                if not filtered:
                    return False, reason, modified_data
                message_data = modified_data
                
                # 检查前缀保护
                filtered, reason, modified_data = await self._apply_prefix_protection(event, message_data)
                message_data = modified_data
            
            return True, "通过过滤", message_data
            
        except Exception as e:
            self.logger.error(f"过滤发送消息失败: {e}")
            return True, "过滤器错误，默认通过", message_data
    
    async def _apply_global_receive_filters(self, event: Event, 
                                          message_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """应用全局接收过滤词"""
        global_config = self.config_manager.get_global_config()
        receive_filters = global_config.get("global_filters", {}).get("receive_filters", [])
        
        if not receive_filters:
            return True, "无过滤词", message_data
        
        # 提取消息文本
        message_text = self._extract_message_text(message_data)
        if not message_text:
            return True, "无文本内容", message_data
        
        # 检查过滤词
        for filter_word in receive_filters:
            if filter_word in message_text:
                await self._log_filter_action(
                    event, FilterType.RECEIVE_FILTER, 
                    f"包含全局接收过滤词: {filter_word}", FilterAction.BLOCK
                )
                return False, f"包含过滤词: {filter_word}", message_data
        
        return True, "通过全局接收过滤", message_data
    
    async def _apply_global_send_filters(self, event: Event, 
                                       message_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """应用全局发送过滤词"""
        global_config = self.config_manager.get_global_config()
        send_filters = global_config.get("global_filters", {}).get("send_filters", [])
        
        if not send_filters:
            return True, "无过滤词", message_data
        
        # 提取消息文本
        message_text = self._extract_message_text(message_data)
        if not message_text:
            return True, "无文本内容", message_data
        
        # 检查过滤词
        for filter_word in send_filters:
            if filter_word in message_text:
                await self._log_filter_action(
                    event, FilterType.SEND_FILTER, 
                    f"包含全局发送过滤词: {filter_word}", FilterAction.BLOCK
                )
                return False, f"包含发送过滤词: {filter_word}", message_data
        
        return True, "通过全局发送过滤", message_data
    
    async def _apply_prefix_protection(self, event: Event, 
                                     message_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """应用前缀保护"""
        global_config = self.config_manager.get_global_config()
        prefix_protections = global_config.get("global_filters", {}).get("prefix_protections", [])
        
        if not prefix_protections:
            return True, "无前缀保护", message_data
        
        # 提取消息文本
        message_text = self._extract_message_text(message_data)
        if not message_text:
            return True, "无文本内容", message_data
        
        # 检查保护前缀
        for prefix in prefix_protections:
            if message_text.startswith(prefix):
                # 在消息前添加保护标识
                protected_text = f"[禁止诱导触发]{message_text}"
                modified_data = self._modify_message_text(message_data, protected_text)
                
                await self._log_filter_action(
                    event, FilterType.PREFIX_PROTECTION, 
                    f"触发前缀保护: {prefix}", FilterAction.MODIFY
                )
                
                return True, f"应用前缀保护: {prefix}", modified_data
        
        return True, "通过前缀保护", message_data
    
    async def _apply_group_filters(self, event: GroupMessageEvent, 
                                 message_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """应用群组过滤词"""
        group_config = self.config_manager.get_group_config(str(event.group_id))
        if not group_config:
            return True, "无群组配置", message_data
        
        filters = group_config.get("filters", {})
        if not filters:
            return True, "无群组过滤词", message_data
        
        # 提取消息文本
        message_text = self._extract_message_text(message_data)
        if not message_text:
            return True, "无文本内容", message_data
        
        # 获取用户权限等级
        user_level = self.permission_manager.get_user_permission_level(event)
        
        # 先检查超级用户设置的过滤词
        superuser_filters = filters.get("superuser_filters", [])
        for filter_word in superuser_filters:
            if filter_word in message_text:
                await self._log_filter_action(
                    event, FilterType.GROUP_FILTER, 
                    f"包含群组超级用户过滤词: {filter_word}", FilterAction.BLOCK
                )
                return False, f"包含群组过滤词: {filter_word}", message_data
        
        # 再检查群管设置的过滤词（超级用户不受此限制）
        if user_level != PermissionLevel.SUPERUSER:
            admin_filters = filters.get("admin_filters", [])
            for filter_word in admin_filters:
                if filter_word in message_text:
                    await self._log_filter_action(
                        event, FilterType.GROUP_FILTER, 
                        f"包含群组管理员过滤词: {filter_word}", FilterAction.BLOCK
                    )
                    return False, f"包含群组过滤词: {filter_word}", message_data
        
        return True, "通过群组过滤", message_data
    
    def _extract_message_text(self, message_data: Dict[str, Any]) -> str:
        """提取消息文本内容"""
        # 优先使用raw_message
        if "raw_message" in message_data:
            return message_data["raw_message"]
        
        # 从message数组中提取
        if "message" in message_data and isinstance(message_data["message"], list):
            text_parts = []
            for segment in message_data["message"]:
                if segment.get("type") == "text":
                    text_parts.append(segment.get("data", {}).get("text", ""))
            return "".join(text_parts)
        
        # 从message字符串中提取
        if "message" in message_data and isinstance(message_data["message"], str):
            return message_data["message"]
        
        return ""
    
    def _modify_message_text(self, message_data: Dict[str, Any], new_text: str) -> Dict[str, Any]:
        """修改消息文本内容"""
        modified_data = message_data.copy()
        
        # 修改raw_message
        if "raw_message" in modified_data:
            modified_data["raw_message"] = new_text
        
        # 修改message数组
        if "message" in modified_data and isinstance(modified_data["message"], list):
            # 找到第一个文本段并修改
            for segment in modified_data["message"]:
                if segment.get("type") == "text":
                    segment["data"]["text"] = new_text
                    break
        
        # 修改message字符串
        elif "message" in modified_data and isinstance(modified_data["message"], str):
            modified_data["message"] = new_text
        
        return modified_data
    
    async def _log_filter_action(self, event: Event, filter_type: FilterType, 
                               reason: str, action: FilterAction):
        """记录过滤动作"""
        try:
            log_info = {
                "self_id": getattr(event, 'self_id', None),
                "user_id": event.user_id,
                "filter_type": filter_type.value,
                "reason": reason,
                "action": action.value
            }
            
            if isinstance(event, GroupMessageEvent):
                log_info["group_id"] = event.group_id
            
            if action == FilterAction.BLOCK:
                self.logger.warning(f"消息被过滤: {log_info}")
            else:
                self.logger.info(f"过滤动作: {log_info}")
                
        except Exception as e:
            self.logger.error(f"记录过滤动作失败: {e}")

    
    def validate_filter_word(self, word: str) -> Tuple[bool, str]:
        """验证过滤词"""
        if not word or not word.strip():
            return False, "过滤词不能为空"
        
        if len(word) > 100:
            return False, "过滤词长度不能超过100个字符"
        
        # 检查是否包含特殊字符（可根据需要调整）
        if re.search(r'[<>"\']', word):
            return False, "过滤词不能包含特殊字符"
        
        return True, "验证通过"
