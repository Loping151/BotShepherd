"""
指令处理器
处理指令的解析、权限检查和执行
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..onebotv11.models import Event, PrivateMessageEvent, GroupMessageEvent
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
        
        # 指令执行统计
        self.command_stats = {
            "total_executed": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "permission_denials": 0
        }
        
        # 指令冷却缓存
        self.cooldown_cache = {}
    
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
            
            # 执行指令
            response = await self._execute_command(event, command_info)
            if not response:
                return None
            
            # 生成回复消息
            return await self._generate_reply(event, response)
            
        except Exception as e:
            self.logger.error(f"处理指令失败: {e}")
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
    
    async def _execute_command(self, event: Event, command_info: Dict[str, Any]) -> Optional[CommandResponse]:
        """执行指令"""
        command_name = command_info["command_name"]
        args = command_info["args"]
        
        try:
            # 获取指令
            command = command_registry.get_command(command_name)
            if not command:
                return CommandResponse(
                    result=CommandResult.NOT_FOUND,
                    message=f"未找到指令: {command_name}\n使用 {command_info['prefix']}帮助 查看可用指令"
                )
            
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
                self.command_stats["permission_denials"] += 1
                return CommandResponse(
                    result=CommandResult.PERMISSION_DENIED,
                    message=permission_check[1]
                )
            
            # 检查冷却时间
            cooldown_check = await self._check_command_cooldown(event, command)
            if not cooldown_check[0]:
                return CommandResponse(
                    result=CommandResult.ERROR,
                    message=cooldown_check[1]
                )
            
            # 准备执行上下文
            context = {
                "config_manager": self.config_manager,
                "database_manager": self.database_manager,
                "permission_manager": self.permission_manager,
                "logger": self.logger,
                "command_info": command_info
            }
            
            # 执行指令
            self.command_stats["total_executed"] += 1
            response = await command.execute(event, args, context)
            
            # 更新统计
            if response.result == CommandResult.SUCCESS:
                self.command_stats["successful_executions"] += 1
            else:
                self.command_stats["failed_executions"] += 1
            
            # 记录指令执行日志
            await self._log_command_execution(event, command, args, response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"执行指令失败 {command_name}: {e}")
            self.command_stats["failed_executions"] += 1
            
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
    
    async def _check_command_cooldown(self, event: Event, command: BaseCommand) -> Tuple[bool, str]:
        """检查指令冷却时间"""
        # 获取冷却配置
        global_config = self.config_manager.get_global_config()
        cooldown_config = global_config.get("command_cooldown", {})
        
        if not cooldown_config.get("enabled", False):
            return True, "无冷却限制"
        
        # 构建缓存键
        cache_key = f"{event.user_id}_{command.name}"
        current_time = datetime.now()
        
        # 检查冷却时间
        if cache_key in self.cooldown_cache:
            last_execution = self.cooldown_cache[cache_key]
            cooldown_seconds = cooldown_config.get("default_cooldown", 3)
            
            time_diff = (current_time - last_execution).total_seconds()
            if time_diff < cooldown_seconds:
                remaining = cooldown_seconds - time_diff
                return False, f"指令冷却中，请等待 {remaining:.1f} 秒"
        
        # 更新冷却缓存
        self.cooldown_cache[cache_key] = current_time
        
        return True, "冷却检查通过"
    
    async def _generate_reply(self, event: Event, response: CommandResponse) -> Dict[str, Any]:
        """生成回复消息"""
        try:
            # 构建消息段
            message_segments = []
            
            # 如果需要回复原消息
            if response.reply_to_message and hasattr(event, 'message_id'):
                message_segments.append(MessageSegmentBuilder.reply(event.message_id))
            
            # 添加响应文本
            message_segments.append(MessageSegmentBuilder.text(response.message))
            
            # 构建API请求
            if isinstance(event, GroupMessageEvent) and not response.private_reply:
                # 群聊回复
                api_request = ApiHandler.create_send_group_msg_request(
                    group_id=event.group_id,
                    message=message_segments
                )
            else:
                # 私聊回复
                api_request = ApiHandler.create_send_private_msg_request(
                    user_id=event.user_id,
                    message=message_segments
                )
            
            return api_request.dict()
            
        except Exception as e:
            self.logger.error(f"生成回复消息失败: {e}")
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
                "timestamp": datetime.now().isoformat()
            }
            
            if isinstance(event, GroupMessageEvent):
                log_info["group_id"] = event.group_id
            
            if response.result == CommandResult.SUCCESS:
                self.logger.info(f"指令执行成功: {log_info}")
            else:
                self.logger.warning(f"指令执行失败: {log_info}")
                
        except Exception as e:
            self.logger.error(f"记录指令执行日志失败: {e}")
    
    def get_command_stats(self) -> Dict[str, Any]:
        """获取指令统计"""
        return {
            **self.command_stats,
            "success_rate": (
                self.command_stats["successful_executions"] / 
                max(self.command_stats["total_executed"], 1)
            ),
            "cooldown_cache_size": len(self.cooldown_cache),
            "registered_commands": len(command_registry.commands),
            "enabled_commands": len(command_registry.get_enabled_commands())
        }
    
    def reset_command_stats(self):
        """重置指令统计"""
        self.command_stats = {
            "total_executed": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "permission_denials": 0
        }
    
    async def cleanup_cooldown_cache(self):
        """清理冷却缓存"""
        current_time = datetime.now()
        expired_keys = []
        
        for cache_key, last_execution in self.cooldown_cache.items():
            # 清理5分钟前的记录
            if (current_time - last_execution).total_seconds() > 300:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.cooldown_cache[key]
    
    def get_available_commands(self, event: Event) -> List[BaseCommand]:
        """获取用户可用的指令列表"""
        user_level = self.permission_manager.get_user_permission_level(event)
        return command_registry.get_commands_by_permission(user_level)
