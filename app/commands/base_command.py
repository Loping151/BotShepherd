"""
指令基类
定义指令的基础结构和接口
"""

import argparse
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from ..onebotv11.models import Event, PrivateMessageEvent, GroupMessageEvent
from .permission_manager import PermissionLevel

class CommandResult(Enum):
    """指令执行结果"""
    SUCCESS = "success"
    ERROR = "error"
    PERMISSION_DENIED = "permission_denied"
    INVALID_ARGS = "invalid_args"
    NOT_FOUND = "not_found"

@dataclass
class CommandResponse:
    """指令响应"""
    result: CommandResult
    message: str | list
    data: Optional[Dict[str, Any]] = None
    reply_to_message: bool = True
    use_forward: bool = False
    private_reply: bool = False

class BaseCommand(ABC):
    """指令基类"""
    
    def __init__(self):
        self.name = ""
        self.description = ""
        self.usage = ""
        self.example = ""
        self.aliases = []
        self.required_permission = PermissionLevel.MEMBER
        self.enabled = True
        self.group_only = False
        self.private_only = False
        
        # 参数解析器
        self.parser = None
        self._setup_parser()
    
    @abstractmethod
    def _setup_parser(self):
        """设置参数解析器"""
        self.parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
            add_help=False
        )
    
    @abstractmethod
    async def execute(self, event: Event, args: List[str], 
                     context: Dict[str, Any]) -> CommandResponse:
        """执行指令"""
        pass
    
    def parse_args(self, args: List[str]) -> Union[argparse.Namespace, str]:
        """解析参数"""
        try:
            return self.parser.parse_args(args)
        except SystemExit:
            return self.get_help()
        except Exception as e:
            return f"参数解析错误: {e}"
    
    def get_help(self) -> str:
        """获取帮助信息"""
        help_text = f"指令: {self.name}\n"
        help_text += f"描述: {self.description}\n"
        if self.usage:
            help_text += f"用法: {self.usage}\n"
        if self.example:
            help_text += f"示例: {self.example}\n"
        if self.aliases:
            help_text += f"别名: {', '.join(self.aliases)}\n"
        
        # 添加参数帮助
        if self.parser:
            help_text += "\n参数说明:\n"
            help_text += self.parser.format_help()
        
        return help_text
    
    def check_context(self, event: Event) -> Optional[str]:
        """检查执行上下文"""
        if self.group_only and not isinstance(event, GroupMessageEvent):
            return "此指令只能在群聊中使用"
        
        if self.private_only and not isinstance(event, PrivateMessageEvent):
            return "此指令只能在私聊中使用"
        
        return None
    
    def format_response(self, message: str | list, result: CommandResult = CommandResult.SUCCESS,
                       data: Optional[Dict[str, Any]] = None,
                       reply_to_message: bool = True,
                       use_forward: bool = False,
                       private_reply: bool = False) -> CommandResponse:
        """格式化响应"""
        return CommandResponse(
            result=result,
            message=message,
            data=data,
            reply_to_message=reply_to_message if not use_forward else False,
            use_forward=use_forward,
            private_reply=private_reply
        )
    
    def format_error(self, message: str, 
                    result: CommandResult = CommandResult.ERROR, **kwargs) -> CommandResponse:
        """格式化错误响应"""
        return self.format_response(f"❌ {message}", result, **kwargs)
    
    def format_success(self, message: str, 
                      data: Optional[Dict[str, Any]] = None, **kwargs) -> CommandResponse:
        """格式化成功响应"""
        return self.format_response(f"✅ {message}", CommandResult.SUCCESS, data, **kwargs)
    
    def format_info(self, message: str, **kwargs) -> CommandResponse:
        """格式化信息响应"""
        return self.format_response(f"ℹ️ {message}", **kwargs)
    
    def format_warning(self, message: str, **kwargs) -> CommandResponse:
        """格式化警告响应"""
        return self.format_response(f"⚠️ {message}", **kwargs)

class CommandRegistry:
    """指令注册器"""
    
    def __init__(self):
        self.commands: Dict[str, BaseCommand] = {}
        self.aliases: Dict[str, str] = {}  # alias -> command_name
    
    def register(self, command: BaseCommand):
        """注册指令"""
        if not command.name:
            raise ValueError("指令名称不能为空")
        
        if command.name in self.commands:
            raise ValueError(f"指令 {command.name} 已存在")
        
        self.commands[command.name] = command
        
        # 注册别名
        for alias in command.aliases:
            if alias in self.aliases:
                raise ValueError(f"别名 {alias} 已被指令 {self.aliases[alias]} 使用")
            self.aliases[alias] = command.name
    
    def unregister(self, command_name: str):
        """注销指令"""
        if command_name not in self.commands:
            return
        
        command = self.commands[command_name]
        
        # 移除别名
        for alias in command.aliases:
            if alias in self.aliases:
                del self.aliases[alias]
        
        # 移除指令
        del self.commands[command_name]
    
    def get_command(self, name: str) -> Optional[BaseCommand]:
        """获取指令"""
        # 直接查找指令名
        if name in self.commands:
            return self.commands[name]
        
        # 查找别名
        if name in self.aliases:
            return self.commands[self.aliases[name]]
        
        return None
    
    def get_all_commands(self) -> List[BaseCommand]:
        """获取所有指令"""
        return list(self.commands.values())
    
    def get_enabled_commands(self) -> List[BaseCommand]:
        """获取启用的指令"""
        return [cmd for cmd in self.commands.values() if cmd.enabled]
    
    def get_commands_by_permission(self, permission: PermissionLevel) -> List[BaseCommand]:
        """根据权限获取指令"""
        return [cmd for cmd in self.commands.values() 
                if cmd.enabled and cmd.required_permission.value <= permission.value]
    
    def search_commands(self, keyword: str) -> List[BaseCommand]:
        """搜索指令"""
        results = []
        keyword = keyword.lower()
        
        for command in self.commands.values():
            if (keyword in command.name.lower() or 
                keyword in command.description.lower() or
                any(keyword in alias.lower() for alias in command.aliases)):
                results.append(command)
        
        return results
    
    def get_command_info(self) -> Dict[str, Any]:
        """获取指令信息"""
        return {
            "total_commands": len(self.commands),
            "enabled_commands": len(self.get_enabled_commands()),
            "total_aliases": len(self.aliases),
            "commands": [
                {
                    "name": cmd.name,
                    "description": cmd.description,
                    "aliases": cmd.aliases,
                    "required_permission": cmd.required_permission.name,
                    "enabled": cmd.enabled,
                    "group_only": cmd.group_only,
                    "private_only": cmd.private_only
                }
                for cmd in self.commands.values()
            ]
        }

# 全局指令注册器实例
command_registry = CommandRegistry()
