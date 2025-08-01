"""
指令处理器
处理指令的解析、权限检查和执行
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone

from ..onebotv11.models import Event, MessageSegment, MessageSegmentType, PrivateMessageEvent, GroupMessageEvent
from ..onebotv11.message_segment import MessageSegmentParser, MessageSegmentBuilder
from ..onebotv11.api_handler import ApiHandler
from .permission_manager import PermissionManager
from .base_command import BaseCommand, CommandResponse, CommandResult, command_registry

class CommandHandler:
    """指令处理器"""
    
    def __init__(self, config_manager, database_manager, logger):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.permission_manager = PermissionManager(config_manager, logger)
        self.logger = logger
        
        
    async def preprocesser(self, message_data: dict) -> dict:
        """预处理消息数据"""
        try:
            # 仅超级用户和自己（人机合一）允许执行
            if not "user_id" in message_data or (not self.config_manager.is_superuser(message_data.get("user_id")) and message_data.get("user_id") != message_data.get("self_id")):
                return message_data
            
            global_config = self.config_manager.get_global_config()
            trigger_prefix = global_config.get("trigger_prefix", "")
            if not trigger_prefix: # 长度不得为 0
                return message_data
            
            at_id = None
            for message_seg in message_data.get("message", []):
                if message_seg["type"] == "at" and message_seg["data"]["qq"] != "all":
                    at_id = message_seg["data"]["qq"]
            
            for message_seg in message_data.get("message", []):
                if message_seg["type"] == "text" and message_seg["data"]["text"].startswith(trigger_prefix):
                    # 触发指令
                    args = message_seg["data"]["text"][len(trigger_prefix):].strip()
                    if " " not in args and not at_id:
                        raise ValueError("触发指令需要至少两个参数：id 和 指令名称")
                    
                    self.logger.command.info(f"使用触发指令: {args}")
                    if at_id:
                        user_id, command = at_id, args
                    else:
                        user_id, command = args.split(maxsplit=1)
                        
                    if not user_id.isdigit():
                        raise ValueError("触发指令的用户ID必须是数字")
                    
                    message_data["user_id"] = user_id
                    if "sender" in message_data:
                        message_data["sender"]["user_id"] = user_id
                        message_data["sender"]["nickname"] = "被触发用户"
                        message_data["sender"]["role"] = "member"
                    message_data["message"] = [{"type": "text", "data": {"text": command}}]
                    message_data["raw_message"] = command
            
            return message_data
            
        except Exception as e:
            self.logger.command.error(f"预处理器配置错误: {e}")
            return message_data
        
    
    async def handle_message(self, event: Event) -> Optional[Dict[str, Any]]:
        """处理消息中的指令"""
        try:
            # 检查是否为消息事件
            if not isinstance(event, (PrivateMessageEvent, GroupMessageEvent)):
                return None
            
            # 检查是否为指令
            command_info = await self._extract_command_info(event)
            if not command_info:
                return None
            
            # 检查是否 at 别人
            if await self._check_at_other(event):
                return None
            
            # 执行指令
            response = await self._execute_command(event, command_info)
            if not response:
                return None
            
            # 生成回复消息
            return await self._generate_reply(event, response)
            
        except Exception as e:
            self.logger.command.error(f"处理指令失败: {e}")
            return None
    
    async def _extract_command_info(self, event: Event) -> Optional[Dict[str, Any]]:
        """提取指令信息"""
        global_config = self.config_manager.get_global_config()
        command_prefix = global_config.get("command_prefix", "bs")
        
        # 检查是否为指令
        if not MessageSegmentParser.is_command(event.message, command_prefix):
            return None
        
        # 解析指令
        command_result = MessageSegmentParser.parse_command(event.message, command_prefix)
        if not command_result:
            return None
        
        command_name, args = command_result
        
        return {
            "command_name": command_name,
            "args": args,
            "raw_command": MessageSegmentParser.extract_text(event.message).strip(),
            "prefix": command_prefix
        }
    
    async def _check_at_other(self, event: Event) -> bool:
        """检查是否 at 别人"""
        global_config = self.config_manager.get_global_config()
        if global_config.get("command_ignore_at_other", True):
            for message_seg in event.message:
                if message_seg.type == MessageSegmentType.AT and str(message_seg.data["qq"]) != str(event.self_id):
                    return True
        return False
    
    async def _execute_command(self, event: Event, command_info: Dict[str, Any]) -> Optional[CommandResponse]:
        """执行指令"""
        command_name = command_info["command_name"]
        args = command_info["args"]
        
        try:
            # 获取指令
            command = command_registry.get_command(command_name)
            if not command:
                if self.config_manager.is_superuser(event.user_id):
                    return CommandResponse(
                        result=CommandResult.NOT_FOUND,
                        message="未找到指令: {}\n使用 {}帮助 查看可用指令".format(command_name, command_info['prefix'])
                    )
                else:
                    return None
            
            # 检查指令是否启用
            if not command.enabled:
                return CommandResponse(
                    result=CommandResult.ERROR,
                    message=f"指令 {command_name} 已被禁用"
                )
            
            # 检查执行上下文
            context_error = command.check_context(event)
            if context_error:
                return CommandResponse(
                    result=CommandResult.ERROR,
                    message=context_error
                )
            
            # 检查权限
            permission_check = await self._check_command_permission(event, command)
            if not permission_check[0]:
                return None
                # return CommandResponse(
                #     result=CommandResult.PERMISSION_DENIED,
                #     message=permission_check[1]
                # )
            
            # 准备执行上下文
            context = {
                "config_manager": self.config_manager,
                "database_manager": self.database_manager,
                "permission_manager": self.permission_manager,
                "logger": self.logger,
                "command_info": command_info,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 执行指令
            response = await command.execute(event, args, context)
            
            # 记录指令执行日志
            await self._log_command_execution(event, command, args, response)
            
            return response
            
        except Exception as e:
            self.logger.command.error(f"执行指令失败 {command_name}: {e}")
            
            return CommandResponse(
                result=CommandResult.ERROR,
                message=f"指令执行出错: {str(e)}"
            )
    
    async def _check_command_permission(self, event: Event, command: BaseCommand) -> Tuple[bool, str]:
        """检查指令权限"""
        user_level = self.permission_manager.get_user_permission_level(event)
        
        if user_level.value < command.required_permission.value:
            required_desc = self.permission_manager.get_permission_description(command.required_permission)
            user_desc = self.permission_manager.get_permission_description(user_level)
            
            return False, f"权限不足，需要 {required_desc} 权限，当前权限: {user_desc}"
        
        return True, "权限检查通过"
    
    async def _generate_reply(self, event: Event, response: CommandResponse) -> Dict[str, Any]:
        """生成回复消息"""
        try:
            # 构建消息段
            message_segments = []
            # 如果需要回复原消息
            if response.reply_to_message and hasattr(event, 'message_id'):
                message_segments.append(MessageSegmentBuilder.reply(event.message_id))
            
            # 处理响应文本，支持多段
            if isinstance(response.message, list):
                for msg in response.message:
                    if isinstance(msg, MessageSegment):
                        message_segments.append(msg)
                    else:
                        message_segments.append(MessageSegmentBuilder.text(msg))
            else:
                message_segments.append(MessageSegmentBuilder.text(response.message))
            
            # 构建API请求
            if isinstance(event, GroupMessageEvent) and not response.private_reply:
                if response.use_forward:
                    # 合并转发，支持多段
                    forward_messages = []
                    if isinstance(response.message, list):
                        for msg in response.message:
                            forward_messages.append([MessageSegmentBuilder.text(msg)])
                    else:
                        forward_messages = [message_segments]
                    api_request = ApiHandler.create_send_group_forward_msg_request(
                        group_id=event.group_id,
                        messages=forward_messages
                    )
                else:
                    # 群聊回复
                    api_request = ApiHandler.create_send_group_msg_request(
                        group_id=event.group_id,
                        message=message_segments
                    )
            else:
                if response.use_forward:
                    # 合并转发，支持多段
                    forward_messages = []
                    if isinstance(response.message, list):
                        for msg in response.message:
                            forward_messages.append([MessageSegmentBuilder.text(msg)])
                    else:
                        forward_messages = [message_segments]
                    api_request = ApiHandler.create_send_private_forward_msg_request(
                        user_id=event.user_id,
                        messages=forward_messages
                    )
                else:
                    # 私聊回复
                    api_request = ApiHandler.create_send_private_msg_request(
                        user_id=event.user_id,
                        message=message_segments
                    )
            
            return api_request.model_dump()
            
        except Exception as e:
            self.logger.command.error(f"生成回复消息失败: {e}")
            return None
    
    async def _log_command_execution(self, event: Event, command: BaseCommand, 
                                   args: List[str], response: CommandResponse):
        """记录指令执行日志"""
        try:
            log_info = {
                "command": command.name,
                "user_id": event.user_id,
                "args": args,
                "result": response.result.value,
                "message_length": len(response.message),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if isinstance(event, GroupMessageEvent):
                log_info["group_id"] = event.group_id
            
            if response.result == CommandResult.SUCCESS:
                self.logger.command.info(f"指令执行成功: {log_info}")
            else:
                self.logger.command.warning(f"指令执行失败: {log_info}")
                
        except Exception as e:
            self.logger.command.error(f"记录指令执行日志失败: {e}")
    
    
    def get_available_commands(self, event: Event) -> List[BaseCommand]:
        """获取用户可用的指令列表"""
        user_level = self.permission_manager.get_user_permission_level(event)
        return command_registry.get_commands_by_permission(user_level)
