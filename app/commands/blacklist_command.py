"""
黑名单管理指令
管理用户和群组黑名单
"""

from typing import Dict, Any, List
from ..onebotv11.models import Event, GroupMessageEvent
from .permission_manager import PermissionLevel
from .base_command import BaseCommand, CommandResponse, CommandResult, command_registry

class BlacklistCommand(BaseCommand):
    """黑名单管理指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "黑名单"
        self.description = "管理用户和群组黑名单"
        self.usage = "黑名单 <添加|移除|查看|查找> <用户|群> [ID]"
        self.example = """
    黑名单 add user 123456
    黑名单 查看
    黑名单 查找 123456"""
        self.aliases = ["blacklist", "bl"]
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
        
        self.user_aliases = ["用户", "u", "user"]
        self.group_aliases = ["群", "群组", "群聊", "g", "group"]
        subparsers = self.parser.add_subparsers(dest="action", help="操作类型")
        
        # 添加子命令
        add_parser = subparsers.add_parser("add", aliases=["a", "添加", "+"], help="添加到黑名单")
        add_parser.add_argument("type", choices=self.user_aliases + self.group_aliases, help="类型")
        add_parser.add_argument("id", help="用户ID或群组ID")
        
        remove_parser = subparsers.add_parser("remove", aliases=["r", "rm", "移除", "-"], help="从黑名单移除")
        remove_parser.add_argument("type", choices=self.user_aliases + self.group_aliases, help="类型")
        remove_parser.add_argument("id", help="用户ID或群组ID")
        
        list_parser = subparsers.add_parser("list", aliases=["ls", "查看"], help="查看黑名单")
        list_parser.add_argument("type", nargs="?", choices=self.user_aliases + self.group_aliases, help="类型（可选）")
        
        check_parser = subparsers.add_parser("check", aliases=["ck", "查找"], help="查找黑名单，不需要类型")
        check_parser.add_argument("id", help="用户ID或群组ID")
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行黑名单指令"""
        try:
            parsed_args = self.parse_args(args)
            if isinstance(parsed_args, str):
                return self.format_error(parsed_args, CommandResult.INVALID_ARGS)
            
            if not parsed_args.action:
                return self.format_error("请指定操作类型: 添加, 查看, 查找")
            
            config_manager = context["config_manager"]
            
            if parsed_args.action in ["add", "a", "添加", "+"]:
                return await self._add_to_blacklist(parsed_args, config_manager)
            elif parsed_args.action in ["remove", "r", "rm", "移除", "-"]:
                return await self._remove_from_blacklist(parsed_args, config_manager)
            elif parsed_args.action in ["list", "ls", "查看"]:
                return await self._list_blacklist(parsed_args, config_manager)
            elif parsed_args.action in ["check", "ck", "查找"]:
                return await self._check_blacklist(parsed_args, config_manager)
            else:
                return self.format_error("不支持的操作类型")
            
        except Exception as e:
            return self.format_error(f"黑名单操作失败: {e}")
    
    async def _add_to_blacklist(self, args, config_manager) -> CommandResponse:
        """添加到黑名单"""
        try:
            item_type = "users" if args.type in self.user_aliases else "groups"
            item_id = args.id.strip()
            
            # 验证ID格式
            if not item_id.isdigit():
                return self.format_error("ID必须是数字")
            
            # 检查是否已在黑名单中
            if config_manager.is_in_blacklist(item_type, item_id):
                type_name = "用户" if args.type in self.user_aliases else "群组"
                return self.format_warning(f"{type_name} {item_id} 已在黑名单中")
            
            # 添加到黑名单
            await config_manager.add_to_blacklist(item_type, item_id)
            
            type_name = "用户" if args.type in self.user_aliases else "群组"
            return self.format_success(f"已将{type_name} {item_id} 添加到黑名单")
            
        except Exception as e:
            return self.format_error(f"添加黑名单失败: {e}")
    
    async def _remove_from_blacklist(self, args, config_manager) -> CommandResponse:
        """从黑名单移除"""
        try:
            item_type = "users" if args.type in self.user_aliases else "groups"
            item_id = args.id.strip()
            
            # 验证ID格式
            if not item_id.isdigit():
                return self.format_error("ID必须是数字")
            
            # 检查是否在黑名单中
            if not config_manager.is_in_blacklist(item_type, item_id):
                type_name = "用户" if args.type in self.user_aliases else "群组"
                return self.format_warning(f"{type_name} {item_id} 不在黑名单中")
            
            # 从黑名单移除
            await config_manager.remove_from_blacklist(item_type, item_id)
            
            type_name = "用户" if args.type in self.user_aliases else "群组"
            return self.format_success(f"已将{type_name} {item_id} 从黑名单移除")
            
        except Exception as e:
            return self.format_error(f"移除黑名单失败: {e}")
    
    async def _list_blacklist(self, args, config_manager) -> CommandResponse:
        """查看黑名单"""
        try:
            global_config = config_manager.get_global_config()
            blacklist = global_config.get("blacklist", {})
            result_list = []
            
            if args.type:
                # 查看特定类型的黑名单
                item_type = "users" if args.type in self.user_aliases else "groups"
                type_name = "用户" if args.type in self.user_aliases else "群组"
                
                items = blacklist.get(item_type, [])
                if not items:
                    return self.format_info(f"{type_name}黑名单为空")
                
                result = f"📋 {type_name}黑名单 ({len(items)} 个):\n"
                for i, item_id in enumerate(items, 1):
                    result += f"{i}. {item_id}\n"
                    if len(result) > 2000:
                        result_list.append(result)
                        result = ""
                if result:
                    result_list.append(result)
                
                return self.format_response(result_list, use_forward=True)
            else:
                # 查看所有黑名单
                user_blacklist = blacklist.get("users", [])
                group_blacklist = blacklist.get("groups", [])
                
                result = "📋 黑名单统计:\n\n"
                result += f"👤 用户黑名单: {len(user_blacklist)} 个\n"
                result += f"👥 群组黑名单: {len(group_blacklist)} 个\n\n"
                
                if user_blacklist:
                    result += "用户黑名单:\n"
                    for i, user_id in enumerate(user_blacklist[:10], 1):  # 最多显示10个
                        result += f"  {i}. {user_id}\n"
                    if len(user_blacklist) > 10:
                        result += f"  ... 还有 {len(user_blacklist) - 10} 个\n"
                    result += "\n"
                
                if group_blacklist:
                    result += "群组黑名单:\n"
                    for i, group_id in enumerate(group_blacklist[:10], 1):  # 最多显示10个
                        result += f"  {i}. {group_id}\n"
                    if len(group_blacklist) > 10:
                        result += f"  ... 还有 {len(group_blacklist) - 10} 个\n"
                
                if result.count("\n") > 10:            
                    return self.format_response(result.strip(), use_forward=True)
                else:
                    return self.format_response(result.strip())
                
        except Exception as e:
            return self.format_error(f"查看黑名单失败: {e}")
        

    async def _check_blacklist(self, args, config_manager) -> CommandResponse:
        """查找黑名单"""
        try:
            item_id = args.id.strip()
            
            # 验证ID格式
            if not item_id.isdigit():
                return self.format_error("ID必须是数字")
            
            result = ""
            
            # 检查是否在黑名单中
            if config_manager.is_in_blacklist("users", item_id):
                result += f"用户 {item_id} 在黑名单中\n"
            elif config_manager.is_in_blacklist("groups", item_id):
                result += f"群组 {item_id} 在黑名单中\n"
            if not result:
                return self.format_warning(f"ID {item_id} 不在黑名单中")
            return self.format_info(result)
            
        except Exception as e:
            return self.format_error(f"查找黑名单失败: {e}")


class QuickBlacklistCommand(BaseCommand):
    """快速黑名单指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "拉黑"
        self.description = "快速将用户或当前群组加入黑名单"
        self.usage = "拉黑 [用户ID] 或在群聊中直接使用"
        self.aliases = ["lh"]
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
        self.parser.add_argument(
            "user_id", 
            nargs="?", 
            help="要拉黑的用户ID（群聊中可省略表示拉黑当前群）"
        )
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行快速拉黑指令"""
        try:
            parsed_args = self.parse_args(args)
            if isinstance(parsed_args, str):
                return self.format_error(parsed_args, CommandResult.INVALID_ARGS)
            
            config_manager = context["config_manager"]
            
            # 拉黑群组
            if not parsed_args.user_id:
                if not isinstance(event, GroupMessageEvent):
                    return self.format_error("只能在群聊中拉黑群组")
                
                group_id = str(event.group_id)
                
                if config_manager.is_in_blacklist("groups", group_id):
                    return self.format_warning(f"群组 {group_id} 已在黑名单中")
                
                await config_manager.add_to_blacklist("groups", group_id)
                return self.format_success(f"已将群组 {group_id} 加入黑名单")
            
            # 拉黑用户
            if parsed_args.user_id:
                user_id = parsed_args.user_id.strip()
                
                if not user_id.isdigit():
                    return self.format_error("用户ID必须是数字")
                
                if config_manager.is_in_blacklist("users", user_id):
                    return self.format_warning(f"用户 {user_id} 已在黑名单中")
                
                await config_manager.add_to_blacklist("users", user_id)
                return self.format_success(f"已将用户 {user_id} 加入黑名单")
            
            return self.format_error("请指定要拉黑的用户ID或留空") # 有这种情况？
            
        except Exception as e:
            return self.format_error(f"快速拉黑失败: {e}")

# 注册指令
def register_blacklist_commands():
    """注册黑名单管理指令"""
    command_registry.register(BlacklistCommand())
    command_registry.register(QuickBlacklistCommand())
