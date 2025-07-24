"""
指令系统模块
提供完整的指令处理框架
"""

from .base_command import BaseCommand, CommandResponse, CommandResult, command_registry
from .command_handler import CommandHandler
import os

BUILTIN_PATH = os.path.join(os.path.dirname(__file__), "builtin_commands")
PLUGIN_PATH = os.path.join(os.path.dirname(__file__), "../plugins")

def initialize_builtin_commands(logger):
    """初始化所有指令"""
    
    if not os.path.isdir(BUILTIN_PATH):
        logger.command.error("未找到内置指令目录")
        return
    
    for filename in os.listdir(BUILTIN_PATH):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"app.commands.builtin_commands.{filename[:-3]}"
            try:
                __import__(module_name)
            except ImportError as e:
                logger.command.error(f"注册内置指令 {module_name} 失败: {e}")

    logger.command.info(f"已注册 {len(command_registry.commands)} 个内置指令")

def load_plugins(logger):
    """加载所有插件"""
    if not os.path.isdir(PLUGIN_PATH):
        logger.command.info("未找到插件目录")
        return
    
    for filename in os.listdir(PLUGIN_PATH):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"app.plugins.{filename[:-3]}"
            try:
                __import__(module_name)
                logger.command.info(f"已加载插件: {module_name}")
            except ImportError as e:
                logger.command.error(f"加载插件 {module_name} 失败: {e}")
                
        elif os.path.isdir(os.path.join(PLUGIN_PATH, filename)) and not filename.startswith("__"):
            try:
                __import__(f"app.plugins.{filename}")
                logger.command.info(f"已加载插件目录: {filename}")
            except ImportError as e:
                logger.command.error(f"加载插件目录 {filename} 失败: {e}")
                

__all__ = [
    "BaseCommand",
    "CommandResponse",
    "CommandResult",
    "CommandHandler",
    "command_registry",
    "initialize_commands"
]
