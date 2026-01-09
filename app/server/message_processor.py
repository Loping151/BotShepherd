"""
消息处理器
负责消息的预处理和后处理
"""

from typing import Dict, Any, Optional, List, Tuple
import uuid

from ..onebotv11 import EventParser, MessageNormalizer
from ..onebotv11.models import ApiRequest, Event, MessageEvent, MessageSegmentType, PrivateMessageEvent, GroupMessageEvent, NoticeEvent
from ..onebotv11.message_segment import MessageSegmentParser
from .filter_manager import FilterManager

class MessageProcessor:
    """消息处理器"""
    
    def __init__(self, config_manager, database_manager, logger):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.logger = logger
        
        # 消息解析器和标准化器
        self.event_parser = EventParser()
        self.message_normalizer = MessageNormalizer()
        self.filter_manager = FilterManager(config_manager, logger)
    
    async def preprocess_client_message(self, message_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Event]]:
        """预处理客户端消息"""
        try:
            # 记录原始消息
            self._log_message(message_data, "RECV", "RAW", "debug")
            
            # 消息标准化
            normalized_data = await self._normalize_message(message_data)
            if not normalized_data:
                return None, None
            
            # 解析事件
            event = self.event_parser.parse_event_data(normalized_data)
            if not event and not normalized_data.get("echo"):
                self.logger.message.debug(f"无法解析事件，已忽略")
                self.logger.message.debug(f"忽略事件内容：{normalized_data}")
                return normalized_data, None
            
            # 更新账号活动时间
            if isinstance(event, MessageEvent) or isinstance(event, NoticeEvent):
                if isinstance(event, MessageEvent):
                    await self.config_manager.update_account_last_activity(
                        str(event.self_id), None, "receive"
                    )
            
                # 消息事件预处理，包括决定是否拦截，应用别名等
                processed_data = await self._preprocess_message_event(event, normalized_data)
                if not processed_data:
                    return None, None   
                normalized_data = processed_data
            
            # 记录处理后的消息
            self._log_message(normalized_data, "RECV", "PROCESSED")
            
            # 重新解析事件，事件也受到预处理的影响，会作用到本体指令集
            event = self.event_parser.parse_event_data(normalized_data)
            
            return normalized_data, event
            
        except Exception as e:
            self.logger.message.error(f"预处理客户端消息失败: {e}")
            return None, None
    
    async def postprocess_target_message(self, message_data: Dict[str, Any], self_id: str) -> Optional[Dict[str, Any]]:
        """后处理目标消息"""
        try:            
            # 记录原始消息
            self._log_message(message_data, "SEND", "RAW", "debug")
            
            # 解析事件
            event = self.event_parser.parse_event_data(message_data)
            if event:
                if isinstance(event, ApiRequest) and "send" in event.action:
                
                    # 消息事件特殊处理
                    processed_data = await self._postprocess_message_event(event, self_id, message_data)
                    if not processed_data:
                        return None
                    message_data = processed_data
                    
                    # 记录处理后的消息
                    self._log_message(message_data, "SEND", "PROCESSED")
            
            return message_data
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.logger.message.error(f"Traceback: {traceback.format_exc()}")
            self.logger.message.error(f"后处理目标消息失败: {e}")
            return None
    
    async def _normalize_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化消息"""
        global_config = self.config_manager.get_global_config()
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
        if isinstance(event, MessageEvent):
            # 检查账号是否启用
            is_su = self.config_manager.is_superuser(event.user_id)
            account_config = await self.config_manager.get_account_config(str(event.self_id))
            if account_config and not account_config.get("enabled", True) and not is_su:
                self.logger.message.info(f"账号 {event.self_id} 已禁用，跳过消息处理")
                return None
            
            # 检查群组是否启用和过期
            if isinstance(event, GroupMessageEvent):
                group_config = await self.config_manager.get_group_config(str(event.group_id))
                if group_config and not is_su: # 总是不拦截 su
                    if not group_config.get("enabled", True) and not (event.sender.role in ["owner", "admin"] and event.raw_message.startswith(self.config_manager.get_global_config().get("command_prefix", ""))):
                        # 具有管理员权限的成员发送内置命令不受拦截，除非过期
                        self.logger.message.info(f"群组 {event.group_id} 已禁用，跳过消息处理")
                        return None
                    
                    if await self.config_manager.is_group_expired(str(event.group_id)):
                        self.logger.message.info(f"群组 {event.group_id} 已过期，跳过消息处理")
                        return None

        # 检查黑名单，黑名单覆盖消息事件、入群欢迎、好友申请等
        if self._is_in_blacklist(event) and not is_su:
            self.logger.message.info("消息来自黑名单，跳过处理: user={}, group={}".format(event.user_id, getattr(event, 'group_id', None)))
            return None
        
        # 检查私聊设置
        if isinstance(event, PrivateMessageEvent) and not is_su:
            if not await self._check_private_message_allowed(event):
                self.logger.message.info(f"私聊消息被拒绝: user={event.user_id}, sub_type={event.sub_type}")
                return None
            
        if isinstance(message_data.get("params", {}).get("message"), str):
            message_data["params"]["message"] = [{"type": "text", "data": {"text": message_data["params"]["message"]}}]
            message_data["message_format"] = "array"
        elif isinstance(message_data.get("params", {}).get("message"), list):
            message_data["params"]["message"] = [seg if not isinstance(seg, str) else {"type": "text", "data": {"text": seg}} for seg in message_data["params"]["message"]]
        
        # 应用多级别名转换，优先级为全局->账号->群组
        if isinstance(event, MessageEvent):
            message_data = await self.apply_global_aliases(message_data)
            message_data = await self.apply_account_aliases(message_data)
            if isinstance(event, GroupMessageEvent):
                message_data = await self.apply_group_aliases(message_data)

        # 然后应用过滤词。也就是说，可以通过全局禁用原来的前缀，使用账号别名来使单个账号绕过过滤，实现启用功能的目的。
        if await self.filter_manager.filter_receive_message(event, message_data):
            return None

        return message_data
    
    async def _postprocess_message_event(self, event: Event, self_id: str,
                                       message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """后处理消息事件"""
        if "message" not in message_data.get("params", {}):
            pass # 无消息内容，跳过处理
        elif isinstance(message_data.get("params", {}).get("message"), str):
            message_data["params"]["message"] = [{"type": "text", "data": {"text": message_data["params"]["message"]}}]
            message_data["message_format"] = "array"
        elif isinstance(message_data.get("params", {}).get("message"), list):
            message_data["params"]["message"] = [seg if not isinstance(seg, str) else {"type": "text", "data": {"text": seg}} for seg in message_data["params"]["message"]]
            
        message_data = await self.filter_manager.filter_send_message(event, message_data)
        message_data = await self.decorate_message(event, self_id, message_data)
                
        if not message_data:
            return None
        
        # 更新群组最后消息时间（机器人发送的消息）
        if isinstance(event, ApiRequest):
            if event.params.get("group_id"):
                await self.config_manager.update_group_last_message_time(str(event.params.get("group_id")), self_id)
                await self.config_manager.update_account_last_activity(self_id, str(event.params.get("group_id")), "send")
            elif not "packet" in event.action: # 排除包发送行为
                await self.config_manager.update_account_last_activity(self_id, None, "send")
        
        return message_data
    
    async def decorate_message(self, event: Event, self_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """装饰消息"""
        if not isinstance(event, ApiRequest):
            return message_data
        
        global_config = self.config_manager.get_global_config()
        if not global_config.get("sendcount_notifications", True):
            return message_data
        
        account_config = await self.config_manager.get_account_config(str(self_id))
        send_info = account_config.get("send_count", {"date": None, "group": {"total": 0}, "private": 0})
        
        decorate_info = None
        if event.params.get("group_id"):
            total_count = send_info["group"]["total"]
            group_count = send_info["group"].get(str(event.params.get("group_id")), 0)
            group_deco_template = f"\n今日发了{total_count + 1}条咯，本群{group_count + 1}条，发言过多(~5000)将遭限制"
            if total_count < 3000:
                if (total_count + 1) % 100 == 0:
                    decorate_info = group_deco_template
            elif total_count < 4500:
                if (total_count + 1) % 25 == 0 or (group_count + 1) % 15 == 0:
                    decorate_info = group_deco_template
            else:
                if (group_count + 1) % 10 == 0:
                    decorate_info = group_deco_template
        else:
            private_count = send_info["private"]
            private_deco_template = f"\n今日私聊发了{private_count + 1}条啦"
            if (private_count + 1) % 10 == 0:
                decorate_info = private_deco_template

        
        if decorate_info and isinstance(message_data.get("params", {}), dict) and "message" in message_data["params"] and isinstance(message_data["params"]["message"], list):
            existing_types = set()
            allowed_types = set([MessageSegmentType.AT, MessageSegmentType.TEXT, MessageSegmentType.IMAGE, MessageSegmentType.REPLY])
            for seg in message_data["params"]["message"]:
                existing_types.add(seg["type"])
            if existing_types <= allowed_types:
                message_data["params"]["message"].append({"type": "text", "data": {"text": decorate_info}})
        
        return message_data
    
    def _is_in_blacklist(self, event: Event) -> bool:
        """检查是否在黑名单中"""
                
        if hasattr(event, "user_id"):
            # superuser总是允许
            if self.config_manager.is_superuser(event.user_id):
                return False
            
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
        global_config = self.config_manager.get_global_config()
        
        # superuser和人机合一总是允许
        if event.user_id in self.config_manager.get_superuser() + [event.self_id]:
            return True
        
        # 检查是否允许私聊
        if not global_config.get("allow_private", True):
            return False
        
        # 检查是否仅允许好友私聊
        if global_config.get("private_friend_only", True):
            return event.sub_type == "friend"
        
        return True
    
    def _log_message(self, message_data: Dict[str, Any], direction: str, stage: str, level: str="info"):
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
                return # 暂时不记录其他类型
            
            # 生成内容摘要
            if "params" in message_data:
                message_data = message_data["params"]
            if "message" in message_data:
                if isinstance(message_data["message"], list):
                    # 提取文本内容
                    text_parts = []
                    for segment in message_data["message"]:
                        # 处理字典格式的消息段
                        if isinstance(segment, dict):
                            if segment.get("type") == "text":
                                text_parts.append(str(segment.get("data", {}).get("text", "")))
                            elif segment.get("type") == "at":
                                text_parts.append(f"@{segment.get('data', {}).get('qq', '')}")
                            else:
                                text_parts.append(str(segment)[:1000])
                        # 处理MessageSegment对象
                        elif segment.get("type") and segment.get("data"):
                            if segment.type == "text":
                                text_parts.append(str(segment.data.get("text", "")))
                            elif segment.type == "at":
                                text_parts.append("@{}".format(segment.data.get('qq', '')))
                            else:
                                text_parts.append(str(segment)[:1000])
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
                extra_info.append("bot={}".format(message_data['self_id']))
            if "user_id" in message_data:
                extra_info.append("user={}".format(message_data['user_id']))
            if "group_id" in message_data:
                extra_info.append("group={}".format(message_data['group_id']))
            
            extra_str = " ".join(extra_info) if extra_info else ""
            
            # 记录扁平化日志
            self.logger.log_message(
                direction=f"{direction}_{stage}",
                message_type=msg_type,
                content_summary=content_summary,
                extra_info=extra_str,
                level=level
            )
            
        except Exception as e:
            self.logger.message.error(f"记录消息日志失败: {e}")
    
    async def extract_command_info(self, event: Event) -> Optional[Dict[str, Any]]:
        """提取指令信息"""
        if not isinstance(event, (PrivateMessageEvent, GroupMessageEvent)):
            return None
        
        global_config = self.config_manager.get_global_config()
        command_prefix = global_config.get("command_prefix", "bs")
        
        return self.message_normalizer.extract_command_info(event, command_prefix)
    
    async def _apply_aliases(self, message_data: Dict[str, Any], aliases: Dict[str, List[str]]) -> Dict[str, Any]:
        # 处理消息段
        modified = False
        for sid, segment in enumerate(message_data["message"]):
            if segment.get("type") == "text":
                text = segment.get("data", {}).get("text", "")
                # 检查是否匹配别名
                for target, alias_list in aliases.items():
                    if text.startswith(target) and target not in alias_list: # 旁路原名
                        message_data["message"][sid]["data"]["text"] = uuid.uuid4().hex + text[len(target):] # 我讨厌yunzai
                        # message_data["message"][sid]["data"]["text"] = text[len(target):] # 为了支持取消前缀
                        modified = True
                        break
                    for alias in alias_list:
                        if text.startswith(alias):
                            # 替换别名
                            new_text = target + text[len(alias):]
                            message_data["message"][sid]["data"]["text"] = new_text
                            modified = True
                            break
                    if modified:
                        break
                break # 只替换第一个字符部分，毕竟叫做指令别名
        
        # 更新raw_message
        if modified and "raw_message" in message_data:
            # 重新生成raw_message
            message_data["raw_message"] = MessageSegmentParser.message2raw_message(message_data["message"])
            
        return message_data
    
    async def apply_global_aliases(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用全局别名"""
        try:
            if "message" not in message_data or not isinstance(message_data["message"], list):
                return message_data
            
            global_config = self.config_manager.get_global_config()
            aliases = global_config.get("global_aliases", {})
            
            if not aliases:
                return message_data
            
            return await self._apply_aliases(message_data, aliases)
            
        except Exception as e:
            self.logger.message.error(f"应用全局别名失败: {e}")
            return message_data

    async def apply_account_aliases(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if "message" not in message_data or not isinstance(message_data["message"], list):
                return message_data
            
            account_config = await self.config_manager.get_account_config(str(message_data["self_id"]))
            aliases = account_config.get("aliases", {})
            
            if not aliases:
                return message_data
            
            return await self._apply_aliases(message_data, aliases)
            
        except Exception as e:
            self.logger.message.error(f"应用账号别名失败: {e}")
            return message_data
    
    async def apply_group_aliases(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if "message" not in message_data or not isinstance(message_data["message"], list):
                return message_data
            
            group_config = await self.config_manager.get_group_config(str(message_data["group_id"]))
            aliases = group_config.get("aliases", {})
            
            if not aliases:
                return message_data
            
            return await self._apply_aliases(message_data, aliases)
            
        except Exception as e:
            self.logger.message.error(f"应用群组别名失败: {e}，{message_data}")
            return message_data
