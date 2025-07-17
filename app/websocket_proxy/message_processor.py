"""
消息处理器
负责消息的预处理和后处理
"""

import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..onebotv11 import EventParser, MessageNormalizer
from ..onebotv11.models import Event, PrivateMessageEvent, GroupMessageEvent, MessageSegment
from ..onebotv11.message_segment import MessageSegmentParser
from ..utils.logger import log_message_flat

class MessageProcessor:
    """消息处理器"""
    
    def __init__(self, config_manager, database_manager, logger):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.logger = logger
        
        # 消息解析器和标准化器
        self.event_parser = EventParser()
        self.message_normalizer = MessageNormalizer()
    
    async def preprocess_client_message(self, message_data: Dict[str, Any], 
                                      connection_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[Event]]:
        """预处理客户端消息"""
        try:
            # 记录原始消息
            self._log_message(message_data, "RECV", "RAW")
            
            # 消息标准化
            normalized_data = await self._normalize_message(message_data)
            if not normalized_data:
                return None, None
            
            # 解析事件
            event = self.event_parser.parse_event_data(normalized_data)
            if not event and not normalized_data.get("echo"):
                self.logger.debug(f"无法解析事件，已忽略")
                self.logger.debug(f"忽略事件内容：{normalized_data}")
                return normalized_data, None
            
            # 更新账号活动时间
            if hasattr(event, 'self_id'):
                await self.config_manager.update_account_last_activity(
                    str(event.self_id), "receive"
                )
            
            # 消息事件特殊处理
            if isinstance(event, (PrivateMessageEvent, GroupMessageEvent)):
                processed_data = await self._preprocess_message_event(event, normalized_data)
                if not processed_data:
                    return None, None   
                normalized_data = processed_data
            
            # 记录处理后的消息
            self._log_message(normalized_data, "RECV", "PROCESSED")
            
            return normalized_data, event
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.error(f"预处理客户端消息失败: {e}")
            return None, None
    
    async def postprocess_target_message(self, message_data: Dict[str, Any], 
                                       connection_id: str) -> Optional[Dict[str, Any]]:
        """后处理目标消息"""
        try:
            # 记录原始消息
            self._log_message(message_data, "SEND", "RAW")
            
            # 解析事件
            event = self.event_parser.parse_event_data(message_data)
            if event:
                # 更新账号活动时间
                if hasattr(event, 'self_id'):
                    await self.config_manager.update_account_last_activity(
                        str(event.self_id), "send"
                    )
                
                # 消息事件特殊处理
                if isinstance(event, (PrivateMessageEvent, GroupMessageEvent)):
                    processed_data = await self._postprocess_message_event(event, message_data)
                    if not processed_data:
                        return None
                    message_data = processed_data
            
            # 记录处理后的消息
            self._log_message(message_data, "SEND", "PROCESSED")
            
            return message_data
            
        except Exception as e:
            self.logger.error(f"后处理目标消息失败: {e}")
            return message_data
    
    async def _normalize_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化消息"""
        global_config = await self.config_manager.get_global_config()
        normalization_config = global_config.get("message_normalization", {})
        
        if normalization_config.get("enabled", False):
            return self.message_normalizer.normalize_message_event(
                message_data,
                enable_napcat_normalization=normalization_config.get("normalize_napcat_sent", True)
            )
        
        return message_data
    
    async def _preprocess_message_event(self, event: Event, 
                                      message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """预处理消息事件"""
        # 检查账号是否启用
        account_config = self.config_manager.get_account_config(str(event.self_id))
        if account_config and not account_config.get("enabled", True):
            self.logger.info(f"账号 {event.self_id} 已禁用，跳过消息处理")
            return None
        
        # 检查群组是否启用和过期
        if isinstance(event, GroupMessageEvent):
            group_config = self.config_manager.get_group_config(str(event.group_id))
            if group_config:
                if not group_config.get("enabled", True):
                    self.logger.info(f"群组 {event.group_id} 已禁用，跳过消息处理")
                    return None
                
                if self.config_manager.is_group_expired(str(event.group_id)):
                    self.logger.info(f"群组 {event.group_id} 已过期，跳过消息处理")
                    return None
            
            # 更新群组最后消息时间
            await self.config_manager.update_group_last_message_time(str(event.group_id))
        
        # 检查黑名单
        if self._is_in_blacklist(event):
            self.logger.info(f"消息来自黑名单，跳过处理: user={event.user_id}, group={getattr(event, 'group_id', None)}")
            return None
        
        # 检查私聊设置
        if isinstance(event, PrivateMessageEvent):
            if not await self._check_private_message_allowed(event):
                self.logger.info(f"私聊消息被拒绝: user={event.user_id}, sub_type={event.sub_type}")
                return None
        
        return message_data
    
    async def _postprocess_message_event(self, event: Event, 
                                       message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """后处理消息事件"""
        # 更新群组最后消息时间（机器人发送的消息）
        if isinstance(event, GroupMessageEvent):
            await self.config_manager.update_group_last_message_time(str(event.group_id))
        
        return message_data
    
    def _is_in_blacklist(self, event: Event) -> bool:
        """检查是否在黑名单中"""
        # 检查用户黑名单
        if self.config_manager.is_in_blacklist("users", str(event.user_id)):
            return True
        
        # 检查群组黑名单
        if isinstance(event, GroupMessageEvent):
            if self.config_manager.is_in_blacklist("groups", str(event.group_id)):
                return True
        
        return False
    
    async def _check_private_message_allowed(self, event: PrivateMessageEvent) -> bool:
        """检查私聊消息是否允许"""
        global_config = await self.config_manager.get_global_config()
        
        # 检查是否允许私聊
        if not global_config.get("allow_private", True):
            return False
        
        # 检查是否仅允许好友私聊
        if global_config.get("private_friend_only", True):
            return event.sub_type == "friend"
        
        return True
    
    def _log_message(self, message_data: Dict[str, Any], direction: str, stage: str):
        """记录消息日志"""
        try:
            # 确定消息类型
            post_type = message_data.get("post_type", "unknown")
            message_type = message_data.get("message_type", "")
            action = message_data.get("action", "")
            
            if action:
                msg_type = f"API_{action}"
            elif post_type == "message" or post_type == "message_sent":
                msg_type = f"MSG_{message_type}"
            elif post_type == "notice":
                notice_type = message_data.get("notice_type", "")
                msg_type = f"NOTICE_{notice_type}"
            elif post_type == "request":
                request_type = message_data.get("request_type", "")
                msg_type = f"REQUEST_{request_type}"
            else:
                msg_type = post_type.upper()
            
            # 生成内容摘要
            if "message" in message_data:
                if isinstance(message_data["message"], list):
                    # 提取文本内容
                    text_parts = []
                    for segment in message_data["message"]:
                        # 处理字典格式的消息段
                        if isinstance(segment, dict):
                            if segment.get("type") == "text":
                                text_parts.append(segment.get("data", {}).get("text", ""))
                        # 处理MessageSegment对象
                        elif hasattr(segment, 'type') and hasattr(segment, 'data'):
                            if segment.type == "text":
                                text_parts.append(segment.data.get("text", ""))
                    content_summary = "".join(text_parts)[:100]
                else:
                    content_summary = str(message_data["message"])[:100]
            elif "raw_message" in message_data:
                content_summary = message_data["raw_message"][:100]
            else:
                content_summary = ""
            
            # 额外信息
            extra_info = []
            if "self_id" in message_data:
                extra_info.append(f"bot={message_data['self_id']}")
            if "user_id" in message_data:
                extra_info.append(f"user={message_data['user_id']}")
            if "group_id" in message_data:
                extra_info.append(f"group={message_data['group_id']}")
            
            extra_str = " ".join(extra_info) if extra_info else ""
            
            # 记录扁平化日志
            log_message_flat(
                direction=f"{direction}_{stage}",
                message_type=msg_type,
                content_summary=content_summary,
                extra_info=extra_str
            )
            
        except Exception as e:
            self.logger.error(f"记录消息日志失败: {e}")
    
    async def extract_command_info(self, event: Event) -> Optional[Dict[str, Any]]:
        """提取指令信息"""
        if not isinstance(event, (PrivateMessageEvent, GroupMessageEvent)):
            return None
        
        global_config = await self.config_manager.get_global_config()
        command_prefix = global_config.get("command_prefix", "bs")
        
        return self.message_normalizer.extract_command_info(event, command_prefix)
    
    async def apply_global_aliases(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用全局别名"""
        try:
            if "message" not in message_data or not isinstance(message_data["message"], list):
                return message_data
            
            global_config = await self.config_manager.get_global_config()
            aliases = global_config.get("global_aliases", {})
            
            if not aliases:
                return message_data
            
            # 处理消息段
            modified = False
            for segment in message_data["message"]:
                # 处理字典格式的消息段
                if isinstance(segment, dict):
                    if segment.get("type") == "text":
                        text = segment.get("data", {}).get("text", "")

                        # 检查是否匹配别名
                        for target, alias_list in aliases.items():
                            for alias in alias_list:
                                if text.startswith(alias):
                                    # 替换别名
                                    new_text = target + text[len(alias):]
                                    segment["data"]["text"] = new_text
                                    modified = True
                                    break
                            if modified:
                                break
                # 处理MessageSegment对象
                elif hasattr(segment, 'type') and hasattr(segment, 'data'):
                    if segment.type == "text":
                        text = segment.data.get("text", "")

                        # 检查是否匹配别名
                        for target, alias_list in aliases.items():
                            for alias in alias_list:
                                if text.startswith(alias):
                                    # 替换别名
                                    new_text = target + text[len(alias):]
                                    segment.data["text"] = new_text
                                    modified = True
                                    break
                            if modified:
                                break
                if modified:
                    break
            
            # 更新raw_message
            if modified and "raw_message" in message_data:
                # 重新生成raw_message
                text_parts = []
                for segment in message_data["message"]:
                    # 处理字典格式的消息段
                    if isinstance(segment, dict):
                        if segment.get("type") == "text":
                            text_parts.append(segment.get("data", {}).get("text", ""))
                    # 处理MessageSegment对象
                    elif hasattr(segment, 'type') and hasattr(segment, 'data'):
                        if segment.type == "text":
                            text_parts.append(segment.data.get("text", ""))
                message_data["raw_message"] = "".join(text_parts)
            
            return message_data
            
        except Exception as e:
            self.logger.error(f"应用全局别名失败: {e}")
            return message_data
