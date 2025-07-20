"""
指令系统模块
提供完整的指令处理框架
"""

from .base_command import BaseCommand, CommandResponse, CommandResult, command_registry
from .command_handler import CommandHandler
from .help_command import register_basic_commands
from .query_command import register_query_commands
from .blacklist_command import register_blacklist_commands

def initialize_commands():
    """初始化所有指令"""
    # 注册基础指令
    register_basic_commands()
    
    # 注册统计查询指令
    register_query_commands()

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

# 还没想好插件怎么支持
initialize_commands()