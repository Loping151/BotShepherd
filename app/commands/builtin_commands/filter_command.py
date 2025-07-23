import asyncio
import os
import sys
from typing import Dict, Any, List
from ...onebotv11.models import Event
from ...utils.reboot import reboot
from ..permission_manager import PermissionLevel
from ..base_command import BaseCommand, CommandResponse, CommandResult, command_registry


class FilterCommand(BaseCommand):
    """过滤管理指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "过滤"
        self.description = "管理群组过滤词，全局>主人设置的群过滤>群管"
        self.usage = "过滤器"
        self.example = """
    过滤 添加 今日运势
    过滤 移除 鹿
    过滤 查看 123456"""
        self.aliases = ["违禁词", "禁用词", "ban", "bw"]
        self.required_permission = PermissionLevel.ADMIN
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
        
        subparsers = self.parser.add_subparsers(dest="action", help="操作类型")
        
        # 添加子命令
        add_parser = subparsers.add_parser("add", aliases=["a", "添加", "+"], help="添加过滤词")
        add_parser.add_argument("word", help="过滤词")

        remove_parser = subparsers.add_parser("remove", aliases=["r", "rm", "移除", "-"], help="移除过滤词")
        remove_parser.add_argument("word", help="过滤词")

        list_parser = subparsers.add_parser("list", aliases=["ls", "查看"], help="查看过滤词")
        list_parser.add_argument("group_id", nargs="?", help="群组ID（可选）")
        
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行过滤器指令"""
        try:
            parsed_args = self.parse_args(args)
            if isinstance(parsed_args, str):
                return self.format_error(parsed_args, CommandResult.INVALID_ARGS, use_forward=True)
            if not hasattr(event, "group_id"):
                return self.format_error("仅支持在群聊中使用")
            
            config_manager = context["config_manager"]
            
            group_id = str(event.group_id)
            is_superuser = config_manager.is_superuser(event.user_id)
            
            if parsed_args.action in ["add", "a", "添加", "+"]:
                return await self._add_filter(group_id, is_superuser, parsed_args, config_manager)
            elif parsed_args.action in ["remove", "r", "rm", "移除", "-"]:
                return await self._remove_filter(group_id, is_superuser, parsed_args, config_manager)
            elif parsed_args.action in ["list", "ls", "查看"]:
                return await self._list_filters(group_id, is_superuser, parsed_args, config_manager)
            else:
                return self.format_error("不支持的操作类型")
            
        except Exception as e:
            return self.format_error(f"过滤器操作失败: {e}")
        
    async def _add_filter(self, group_id, is_superuser, args, config_manager) -> CommandResponse:
        """添加过滤词"""
        try:
            word = args.word.strip()
            filter_type = "superuser_filters" if is_superuser else "admin_filters"
            await config_manager.add_group_filter(group_id, filter_type, word)
            return self.format_success(f"已将 {word} 添加到群 {group_id} 过滤词")
            
        except Exception as e:
            return self.format_error(f"添加过滤词失败: {e}")
        
    async def _remove_filter(self, group_id, is_superuser, args, config_manager) -> CommandResponse:
        """移除过滤词"""
        try:
            word = args.word.strip()
            filter_type = "superuser_filters" if is_superuser else "admin_filters"
            await config_manager.remove_group_filter(group_id, filter_type, word)
            return self.format_success(f"已将 {word} 从群 {group_id} 过滤词移除")
            
        except Exception as e:
            return self.format_error(f"移除过滤词失败: {e}")
        
    async def _list_filters(self, group_id, is_superuser, args, config_manager) -> CommandResponse:
        """查看过滤词"""
        if args.group_id and is_superuser:
            group_id = args.group_id.strip()
        if not group_id.isdigit():
            return self.format_error("群组ID必须是数字")
        try:
            filters = await config_manager.list_group_filters(group_id)
            result = f"群组 {group_id} 的过滤词:\n"
            for level, words in filters.items():
                result += f"{level}:\n"
                for word in words:
                    result += f"  - {word}\n"
                    
            if result.count("\n") > 10:            
                return self.format_info(result.strip(), use_forward=True)
            else:
                return self.format_info(result.strip())
                
        except Exception as e:
            return self.format_error(f"查看过滤词失败: {e}")


class GlobalFilterCommand(BaseCommand):
    """全局过滤管理指令，其中前缀保护和发送过滤请在配置文件或控制台管理"""
    
    def __init__(self):
        super().__init__()
        self.name = "全局过滤"
        self.description = "管理全局群组过滤词"
        self.usage = "过滤器"
        self.example = """
    全局过滤 添加 今日运势
    全局过滤 移除 鹿
    全局过滤 强制查看"""
        self.aliases = ["全局违禁词", "全局禁用词", "gban", "gbw"]
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
        
        subparsers = self.parser.add_subparsers(dest="action", help="操作类型")
        
        # 添加子命令
        add_parser = subparsers.add_parser("add", aliases=["a", "添加", "+"], help="添加过滤词")
        add_parser.add_argument("word", help="过滤词")

        remove_parser = subparsers.add_parser("remove", aliases=["r", "rm", "移除", "-"], help="移除过滤词")
        remove_parser.add_argument("word", help="过滤词")
        
        list_parser = subparsers.add_parser("forcelist", aliases=["强制查看"], help="查看过滤词")
        
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行过滤器指令"""
        try:
            parsed_args = self.parse_args(args)
            if isinstance(parsed_args, str):
                return self.format_error(parsed_args, CommandResult.INVALID_ARGS, use_forward=True)
            
            config_manager = context["config_manager"]
                        
            if parsed_args.action in ["add", "a", "添加", "+"]:
                return await self._add_filter(parsed_args, config_manager)
            elif parsed_args.action in ["remove", "r", "rm", "移除", "-"]:
                return await self._remove_filter(parsed_args, config_manager)
            elif parsed_args.action in ["forcelist", "强制查看"]:
                return await self._list_filters(parsed_args, config_manager)
            else:
                return self.format_error("不支持的操作类型")
            
        except Exception as e:
            return self.format_error(f"过滤器操作失败: {e}")
        
    async def _add_filter(self, args, config_manager) -> CommandResponse:
        """添加过滤词"""
        try:
            word = args.word.strip()
            await config_manager.add_global_filter("receive_filters", word)
            return self.format_success(f"已将 {word} 添加到全局过滤词")
            
        except Exception as e:
            return self.format_error(f"添加过滤词失败: {e}")
        
    async def _remove_filter(self, args, config_manager) -> CommandResponse:
        """移除过滤词"""
        try:
            word = args.word.strip()
            await config_manager.remove_global_filter("receive_filters", word)
            return self.format_success(f"已将 {word} 从全局过滤词移除")
            
        except Exception as e:
            return self.format_error(f"移除过滤词失败: {e}")
        
    async def _list_filters(self, args, config_manager) -> CommandResponse:
        """查看过滤词"""
        try:
            filters = await config_manager.list_global_filters()
            result = "全局过滤词:\n"
            for filter_type, words in filters.items():
                result += f"{filter_type}:\n"
                for word in words:
                    result += f"  - {word}\n"
                    
            if result.count("\n") > 10:            
                return self.format_info(result.strip(), use_forward=True)
            else:
                return self.format_info(result.strip())
            
        except Exception as e:
            return self.format_error(f"查看过滤词失败: {e}")
            
def register_filter_commands():
    command_registry.register(FilterCommand())
    command_registry.register(GlobalFilterCommand())

register_filter_commands()