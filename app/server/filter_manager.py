"""
过滤管理器
处理消息过滤和内容检查
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

from ..onebotv11.models import ApiRequest, Event, MessageEvent, MessageSegmentType, PrivateMessageEvent, GroupMessageEvent
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
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
    
    async def filter_receive_message(self, event: Event, 
                                   message_data: Dict[str, Any]) -> bool:
        """过滤接收消息 True表示被过滤"""
        try:            
            
            # 检查全局接收过滤词
            if isinstance(event, MessageEvent):
                filtered = await self._apply_global_receive_filters(event, message_data)
                if filtered:
                    return True
                
                # 检查群组过滤词
                if isinstance(event, GroupMessageEvent):
                    filtered = await self._apply_group_filters(event, message_data)
                    if filtered:
                        return True
            
            return False
            
        except Exception as e:
            self.logger.message.error(f"过滤接收消息失败: {e}，将拦截！")
            return True
    
    async def filter_send_message(self, event: Event, 
                                message_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """过滤发送消息"""
        try:
            # 检查全局发送过滤词
            if isinstance(event, ApiRequest):
                filtered = await self._apply_global_send_filters(event, message_data)
                if filtered:
                    return None
                
                modified_data = await self._apply_prefix_protection(event, message_data)
                message_data = modified_data
            
            return message_data
            
        except Exception as e:
            self.logger.message.error(f"过滤发送消息失败: {e}，将拦截！{message_data}"[:1000])
            return None
    
    async def _apply_global_receive_filters(self, event: Event, 
                                          message_data: Dict[str, Any]) -> bool:
        """应用全局接收过滤词"""
        global_config = self.config_manager.get_global_config()
        receive_filters = global_config.get("global_filters", {}).get("receive_filters", [])
        
        if not receive_filters:
            return False
        
        # 提取消息文本
        message_text = self._extract_message_text(message_data)
        if not message_text:
            return False
        
        if message_text.startswith(global_config.get("command_prefix")):
            return False
        
        # 检查过滤词
        for filter_word in receive_filters:
            if filter_word in message_text or \
                ("+" in filter_word and all(part in message_text for part in filter_word.split("+"))) or \
                    ("|" in filter_word and any(part in message_text for part in filter_word.split("|"))):
                await self._log_filter_action(
                    event, FilterType.RECEIVE_FILTER, 
                    f"包含全局接收过滤词: {filter_word}", FilterAction.BLOCK
                )
                return True
        
        return False
    
    async def _apply_global_send_filters(self, event: Event, 
                                       message_data: Dict[str, Any]) -> bool:
        """应用全局发送过滤词"""
        global_config = self.config_manager.get_global_config()
        send_filters = global_config.get("global_filters", {}).get("send_filters", [])
        
        if not send_filters:
            return False
        
        # 提取消息文本
        message_text = self._extract_message_text(message_data.get("params", {}))
        if not message_text:
            return False
        
        # 检查过滤词
        for filter_word in send_filters:
            if filter_word in message_text or \
                ("+" in filter_word and all(part in message_text for part in filter_word.split("+"))) or \
                    ("|" in filter_word and any(part in message_text for part in filter_word.split("|"))):
                await self._log_filter_action(
                    event, FilterType.SEND_FILTER, 
                    f"包含全局发送过滤词: {filter_word}", FilterAction.BLOCK
                )
                return True
        
        return False
    
    async def _apply_prefix_protection(self, event: Event, 
                                     message_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用前缀保护"""
        global_config = self.config_manager.get_global_config()
        prefix_protections = global_config.get("global_filters", {}).get("prefix_protections", []).copy()
        if global_config.get("trigger_prefix"):
            prefix_protections.append(global_config.get("trigger_prefix"))
        
        if not prefix_protections or not message_data.get("params", {}).get("message"):
            return message_data
        
        # 检查保护前缀
        for prefix in prefix_protections:
            for idx, item in enumerate(message_data.get("params", {}).get("message")):
                if isinstance(item, dict):
                    t, text = item.get("type"), item.get("data", {}).get("text", "")
                    if t == MessageSegmentType.TEXT:
                        if isinstance(text, list):
                            text = "\n".join(text)
                        if text.startswith(prefix):
                            message_data["params"]["message"][idx]["data"]["text"] = f"[禁止诱导触发]{text}"
                            await self._log_filter_action(
                                event, FilterType.PREFIX_PROTECTION, 
                                f"触发前缀保护: {prefix}", FilterAction.MODIFY
                            )
                            return message_data
                        break
                elif isinstance(item, str):
                    if item.startswith(prefix):
                        message_data["params"]["message"][idx] = f"[禁止诱导触发]{item}"
                        await self._log_filter_action(
                            event, FilterType.PREFIX_PROTECTION, 
                            f"触发前缀保护: {prefix}", FilterAction.MODIFY
                        )
                        return message_data
                    break
                        
        return message_data
    
    async def _apply_group_filters(self, event: GroupMessageEvent, 
                                 message_data: Dict[str, Any]) -> bool:
        """应用群组过滤词，具有额外规则：可以设为QQ号，实现群内机器人的开关或不响应单个群员"""
        global_config = self.config_manager.get_global_config()
        group_config = await self.config_manager.get_group_config(str(event.group_id))
        if not group_config:
            return False
        
        filters = group_config.get("filters", {})
        if not filters:
            return False
        
        # 提取消息文本
        message_text = self._extract_message_text(message_data)
        if not message_text:
            return False
        
        self_id = str(event.self_id)
        user_id = str(event.user_id)
        message_text = message_text + self_id + user_id
                        
        if message_text.startswith(global_config.get("command_prefix")):
            return False
        
        # 先检查超级用户设置的过滤词
        superuser_filters = filters.get("superuser_filters", [])
        for filter_word in superuser_filters:
            if filter_word in message_text or \
                ("+" in filter_word and all(part in message_text for part in filter_word.split("+"))) or \
                    ("|" in filter_word and any(part in message_text for part in filter_word.split("|"))):
                await self._log_filter_action(
                    event, FilterType.GROUP_FILTER, 
                    f"包含群组超级用户过滤词: {filter_word}", FilterAction.BLOCK
                )
                return True
        
        # 再检查群管设置的过滤词（超级用户不受此限制）
        if not self.config_manager.is_superuser(event.user_id):
            admin_filters = filters.get("admin_filters", [])
            for filter_word in admin_filters:
                if filter_word in message_text or \
                    ("+" in filter_word and all(part in message_text for part in filter_word.split("+"))) or \
                        ("|" in filter_word and any(part in message_text for part in filter_word.split("|"))):
                    await self._log_filter_action(
                        event, FilterType.GROUP_FILTER, 
                        f"包含群组管理员过滤词: {filter_word}", FilterAction.BLOCK
                    )
                    return True
        
        return False
    
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
                "user_id": event.user_id if isinstance(event, GroupMessageEvent) else event.params.get("user_id"),
                "filter_type": filter_type.value,
                "reason": reason,
                "action": action.value
            }
            
            if isinstance(event, GroupMessageEvent):
                log_info["group_id"] = event.group_id
            elif event.params.get("group_id"):
                log_info["group_id"] = event.params.get("group_id")
            
            if action == FilterAction.BLOCK:
                self.logger.message.info(f"消息被过滤: {log_info}")
            else:
                self.logger.message.info(f"过滤动作: {log_info}")
                
        except Exception as e:
            self.logger.message.error(f"记录过滤动作失败: {e}")

    
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
