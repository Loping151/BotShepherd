"""
指令系统模块
提供完整的指令处理框架
"""

from .base_command import BaseCommand, CommandResponse, CommandResult, command_registry
from .command_handler import CommandHandler
from .help_command import register_basic_commands
from .blacklist_command import register_blacklist_commands

def initialize_commands():
    """初始化所有指令"""
    # 注册基础指令
    register_basic_commands()

    # 注册黑名单管理指令
    register_blacklist_commands()

    print(f"已注册 {len(command_registry.commands)} 个指令")

__all__ = [
    "BaseCommand",
    "CommandResponse",
    "CommandResult",
    "CommandHandler",
    "command_registry",
    "initialize_commands"
]

# 还是import自己注册吧，虽然不知道为啥要注册，都没打算实现自定义插件。。先留着吧。。万一呢
initialize_commands()