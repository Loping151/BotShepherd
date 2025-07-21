"""
指令系统模块
提供完整的指令处理框架
"""

from .base_command import BaseCommand, CommandResponse, CommandResult, command_registry
from .command_handler import CommandHandler
from .help_command import register_basic_commands
from .query_command import register_query_commands
from .control_command import register_control_commands
from .blacklist_command import register_blacklist_commands
import os

PLUGIN_PATH = os.path.join(os.path.dirname(__file__), "plugins")

def initialize_builtin_commands(logger):
    """初始化所有指令"""
    # 注册基础指令
    register_basic_commands()
    
    # 注册统计查询指令
    register_query_commands()
    
    # 注册控制指令
    register_control_commands()

    # 注册黑名单管理指令
    register_blacklist_commands()

    logger.info(f"已注册 {len(command_registry.commands)} 个内置指令")

def load_plugins(logger):
    """加载所有插件"""
    if not os.path.isdir(PLUGIN_PATH):
        logger.info("未找到插件目录")
        return
    
    for filename in os.listdir(PLUGIN_PATH):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"app.commands.plugins.{filename[:-3]}"
            try:
                __import__(module_name)
                logger.info(f"已加载插件: {module_name}")
            except ImportError as e:
                logger.error(f"加载插件 {module_name} 失败: {e}")
                
        elif os.path.isdir(os.path.join(PLUGIN_PATH, filename)) and not filename.startswith("__"):
            try:
                __import__(f"app.commands.plugins.{filename}")
                logger.info(f"已加载插件目录: {filename}")
            except ImportError as e:
                logger.error(f"加载插件目录 {filename} 失败: {e}")
                

__all__ = [
    "BaseCommand",
    "CommandResponse",
    "CommandResult",
    "CommandHandler",
    "command_registry",
    "initialize_commands"
]
