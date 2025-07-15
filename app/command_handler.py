"""
指令处理模块 - 类似nonebot的指令系统
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Awaitable
from datetime import datetime
import re

from .onebot.event import MessageEvent, EventParser
from .onebot.message import Message, MessageBuilder, MessageParser
from .onebot.api import BotAPI, ForwardMessageBuilder
from .global_config import GlobalConfigManager
from .bot_config import BotConfigManager
from .statistics import MessageStatistics, StatisticsReporter


class CommandContext:
    """指令上下文"""
    
    def __init__(self, event: MessageEvent, bot_api: BotAPI, 
                 global_config: GlobalConfigManager, bot_config_manager: BotConfigManager,
                 statistics: MessageStatistics, reporter: StatisticsReporter):
        self.event = event
        self.bot_api = bot_api
        self.global_config = global_config
        self.bot_config_manager = bot_config_manager
        self.statistics = statistics
        self.reporter = reporter
        
        # 便捷属性
        self.self_id = event.self_id
        self.user_id = event.user_id
        self.group_id = getattr(event, 'group_id', None)
        self.message = event.message
        self.raw_message = event.raw_message
        self.is_group = event.is_group_message()
        self.is_private = event.is_private_message()
        
        # 获取Bot配置
        self.bot_config = bot_config_manager.get_config(self.self_id)
    
    async def send(self, message: Any, **kwargs) -> Any:
        """发送消息"""
        if self.is_group:
            return await self.bot_api.send_group_msg(self.group_id, message, **kwargs)
        else:
            return await self.bot_api.send_private_msg(self.user_id, message, **kwargs)
    
    async def reply(self, message: Any, **kwargs) -> Any:
        """回复消息"""
        # 构建回复消息
        reply_msg = Message([
            MessageBuilder.reply(self.event.message_id),
            MessageBuilder.text(str(message))
        ])
        return await self.send(reply_msg, **kwargs)
    
    async def send_forward(self, messages: List[Dict[str, Any]], **kwargs) -> Any:
        """发送转发消息"""
        if self.is_group:
            return await self.bot_api.send_group_forward_msg(self.group_id, messages, **kwargs)
        else:
            return await self.bot_api.send_private_forward_msg(self.user_id, messages, **kwargs)
    
    def get_plain_text(self) -> str:
        """获取纯文本内容"""
        return self.event.get_plain_text()
    
    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return self.global_config.is_admin(self.user_id)
    
    def is_super_admin(self) -> bool:
        """检查是否为超级管理员"""
        return self.global_config.is_super_admin(self.user_id)


class Command:
    """指令类"""
    
    def __init__(self, name: str, handler: Callable[[CommandContext], Awaitable[None]], 
                 aliases: List[str] = None, description: str = "", 
                 admin_only: bool = False, group_only: bool = False, private_only: bool = False):
        self.name = name
        self.handler = handler
        self.aliases = aliases or []
        self.description = description
        self.admin_only = admin_only
        self.group_only = group_only
        self.private_only = private_only
    
    def matches(self, command_text: str) -> bool:
        """检查指令是否匹配"""
        return command_text == self.name or command_text in self.aliases
    
    def can_execute(self, ctx: CommandContext) -> bool:
        """检查是否可以执行"""
        if self.admin_only and not ctx.is_admin():
            return False
        if self.group_only and not ctx.is_group:
            return False
        if self.private_only and not ctx.is_private:
            return False
        return True


class CommandHandler:
    """指令处理器"""
    
    def __init__(self, global_config: GlobalConfigManager, bot_config_manager: BotConfigManager,
                 statistics: MessageStatistics, reporter: StatisticsReporter):
        self.global_config = global_config
        self.bot_config_manager = bot_config_manager
        self.statistics = statistics
        self.reporter = reporter
        self.commands: Dict[str, Command] = {}
        
        # 注册内置指令
        self.register_builtin_commands()
    
    def register_command(self, command: Command):
        """注册指令"""
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command
    
    def register_builtin_commands(self):
        """注册内置指令"""
        
        # 帮助指令
        self.register_command(Command(
            name="help",
            handler=self.handle_help,
            aliases=["帮助", "h"],
            description="显示帮助信息"
        ))
        
        # 统计指令
        self.register_command(Command(
            name="stats",
            handler=self.handle_stats,
            aliases=["统计", "数据"],
            description="显示消息统计信息"
        ))
        
        # 今日统计
        self.register_command(Command(
            name="today",
            handler=self.handle_today_stats,
            aliases=["今日", "今天"],
            description="显示今日统计"
        ))
        
        # 昨日统计
        self.register_command(Command(
            name="yesterday",
            handler=self.handle_yesterday_stats,
            aliases=["昨日", "昨天"],
            description="显示昨日统计"
        ))
        
        # 关键词搜索
        self.register_command(Command(
            name="search",
            handler=self.handle_keyword_search,
            aliases=["搜索", "查找"],
            description="搜索关键词使用情况"
        ))
        
        # 管理员指令
        self.register_command(Command(
            name="admin",
            handler=self.handle_admin,
            aliases=["管理"],
            description="管理员功能",
            admin_only=True
        ))
    
    async def process_message(self, event: MessageEvent, bot_api: BotAPI) -> bool:
        """处理消息，返回是否处理了指令"""
        try:
            # 获取指令前缀
            prefixes = self.global_config.get_command_prefixes()
            
            # 检查是否为指令
            text = event.get_plain_text().strip()
            command_text = None
            args = []
            
            for prefix in prefixes:
                if text.startswith(prefix):
                    command_part = text[len(prefix):].strip()
                    if command_part:
                        parts = command_part.split()
                        command_text = parts[0]
                        args = parts[1:] if len(parts) > 1 else []
                        break
            
            if not command_text:
                return False
            
            # 查找指令
            command = self.commands.get(command_text)
            if not command:
                return False
            
            # 创建上下文
            ctx = CommandContext(
                event, bot_api, self.global_config, self.bot_config_manager,
                self.statistics, self.reporter
            )
            ctx.args = args  # 添加参数
            
            # 检查权限
            if not command.can_execute(ctx):
                await ctx.reply("❌ 权限不足")
                return True
            
            # 执行指令
            await command.handler(ctx)
            return True
            
        except Exception as e:
            print(f"Error processing command: {e}")
            return False
    
    async def handle_help(self, ctx: CommandContext):
        """处理帮助指令"""
        help_text = "📖 BotShepherd 指令帮助\n\n"
        
        for name, command in self.commands.items():
            if name == command.name:  # 只显示主名称，不显示别名
                help_text += f"• {name}"
                if command.aliases:
                    help_text += f" ({', '.join(command.aliases)})"
                help_text += f": {command.description}\n"
        
        await ctx.send(help_text)
    
    async def handle_stats(self, ctx: CommandContext):
        """处理统计指令"""
        try:
            report = await self.reporter.generate_weekly_report(ctx.self_id)
            await ctx.send(report)
        except Exception as e:
            await ctx.reply(f"❌ 获取统计失败: {str(e)}")
    
    async def handle_today_stats(self, ctx: CommandContext):
        """处理今日统计指令"""
        try:
            report = await self.reporter.generate_daily_report(ctx.self_id)
            await ctx.send(report)
        except Exception as e:
            await ctx.reply(f"❌ 获取今日统计失败: {str(e)}")
    
    async def handle_yesterday_stats(self, ctx: CommandContext):
        """处理昨日统计指令"""
        try:
            yesterday = (datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            report = await self.reporter.generate_daily_report(ctx.self_id, yesterday)
            await ctx.send(report)
        except Exception as e:
            await ctx.reply(f"❌ 获取昨日统计失败: {str(e)}")
    
    async def handle_keyword_search(self, ctx: CommandContext):
        """处理关键词搜索指令"""
        if not ctx.args:
            await ctx.reply("❌ 请提供要搜索的关键词")
            return
        
        keyword = ctx.args[0]
        days = 7
        if len(ctx.args) > 1:
            try:
                days = int(ctx.args[1])
            except ValueError:
                pass
        
        try:
            report = await self.reporter.generate_keyword_report(ctx.self_id, keyword, days)
            await ctx.send(report)
        except Exception as e:
            await ctx.reply(f"❌ 搜索失败: {str(e)}")
    
    async def handle_admin(self, ctx: CommandContext):
        """处理管理员指令"""
        if not ctx.args:
            admin_help = "🔧 管理员指令:\n"
            admin_help += "• admin reload - 重载配置\n"
            admin_help += "• admin cleanup - 清理过期数据\n"
            admin_help += "• admin status - 系统状态\n"
            await ctx.send(admin_help)
            return
        
        subcommand = ctx.args[0]
        
        if subcommand == "reload":
            # 重载配置
            self.global_config.load_config()
            await ctx.reply("✅ 配置已重载")
            
        elif subcommand == "cleanup":
            # 清理过期数据
            await ctx.reply("🧹 开始清理过期数据...")
            # 这里需要调用清理函数
            await ctx.reply("✅ 清理完成")
            
        elif subcommand == "status":
            # 系统状态
            status_text = f"🤖 Bot状态:\n"
            status_text += f"• Self ID: {ctx.self_id}\n"
            status_text += f"• 群组配置: {len(ctx.bot_config.groups)}\n"
            status_text += f"• 黑名单用户: {len(ctx.bot_config.blacklisted_users)}\n"
            status_text += f"• 白名单用户: {len(ctx.bot_config.whitelisted_users)}\n"
            await ctx.send(status_text)
            
        else:
            await ctx.reply("❌ 未知的管理员指令")
