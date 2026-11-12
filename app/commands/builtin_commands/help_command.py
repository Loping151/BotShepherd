"""
帮助指令
显示系统帮助信息和指令列表
"""

import psutil
from typing import Dict, Any, List
from ...onebotv11.models import Event
from ..permission_manager import PermissionLevel
from ..base_command import BaseCommand, CommandResponse, CommandResult, command_registry

class HelpCommand(BaseCommand):
    """帮助指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "帮助"
        self.description = "显示帮助信息和可用指令列表"
        self.usage = "帮助 [指令名称]"
        self.aliases = ["help", "h", "?"]
        self.required_permission = PermissionLevel.ADMIN
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
        self.parser.add_argument(
            "command", 
            nargs="?", 
            help="要查看帮助的指令名称"
        )
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行帮助指令"""
        try:
            parsed_args = self.parse_args(args)
            if isinstance(parsed_args, str):
                return self.format_error(parsed_args, CommandResult.INVALID_ARGS)
            
            permission_manager = context["permission_manager"]
            config_manager = context["config_manager"]
            
            # 如果指定了具体指令
            if parsed_args.command:
                return await self._show_command_help(parsed_args.command, event, permission_manager)
            
            # 显示总体帮助
            return await self._show_general_help(event, permission_manager, config_manager)
            
        except Exception as e:
            return self.format_error(f"获取帮助信息失败: {e}")
    
    async def _show_command_help(self, command_name: str, event: Event, permission_manager) -> CommandResponse:
        """显示特定指令的帮助"""
        command = command_registry.get_command(command_name)
        if not command:
            # return self.format_error(f"未找到指令: {command_name}")
            return # 不提示
        
        # 检查用户是否有权限查看此指令
        user_level = permission_manager.get_user_permission_level(event)
        if user_level.value < command.required_permission.value:
            # return self.format_error(f"您没有权限查看指令 {command_name} 的帮助")
            return # 不提示
        
        help_text = command.get_help()
        
        # 添加权限信息
        required_permission = permission_manager.get_permission_description(command.required_permission)
        help_text += f"\n需要权限: {required_permission}"
        
        # 添加使用限制
        restrictions = []
        if command.group_only:
            restrictions.append("仅限群聊")
        if command.private_only:
            restrictions.append("仅限私聊")
        
        if restrictions:
            help_text += "\n使用限制: {}".format(', '.join(restrictions))
        
        return self.format_response(help_text, use_forward=True)
    
    async def _show_general_help(self, event: Event, permission_manager, config_manager) -> CommandResponse:
        """显示总体帮助"""
        user_level = permission_manager.get_user_permission_level(event)
        available_commands = command_registry.get_commands_by_permission(user_level)
        
        if not available_commands:
            return self.format_warning("暂无可用指令")
        
        # 获取指令前缀
        global_config = config_manager.get_global_config()
        command_prefix = global_config.get("command_prefix", "bs")
        
        # 构建帮助信息
        help_text = "🐏 BotShepherd 帮助信息\n\n"
        
        # 用户权限信息
        permission_desc = permission_manager.get_permission_description(user_level)
        help_text += f"您的权限等级: {permission_desc}\n"
        help_text += f"指令前缀: {command_prefix}\n\n"
        
        # 按权限等级分组显示指令
        commands_by_level = {
            PermissionLevel.MEMBER: [],
            PermissionLevel.ADMIN: [],
            PermissionLevel.SUPERUSER: []
        }
        
        for command in available_commands:
            if command.enabled:
                commands_by_level[command.required_permission].append(command)
        
        # 显示各等级指令
        level_names = {
            PermissionLevel.MEMBER: "📝 普通指令",
            PermissionLevel.ADMIN: "👥 群管指令", 
            PermissionLevel.SUPERUSER: "⚡ 主人指令"
        }
        
        for level in [PermissionLevel.MEMBER, PermissionLevel.ADMIN, PermissionLevel.SUPERUSER]:
            commands = commands_by_level[level]
            if commands and user_level.value >= level.value:
                help_text += f"{level_names[level]}:\n"
                
                for command in sorted(commands, key=lambda x: x.name):
                    # 指令名称和别名
                    cmd_info = command.name
                    if command.aliases:
                        cmd_info += " ({})".format(', '.join(command.aliases[:2]))
                    
                    help_text += f"  • {cmd_info} - {command.description}\n"
                        
        # 使用说明
        help_text += "💡 使用说明:\n"
        help_text += f"• 使用 {command_prefix}指令名 执行指令\n"
        help_text += f"• 使用 {command_prefix}帮助 指令名 查看详细帮助\n"
        
        return self.format_response(help_text, use_forward=True)

class StatusCommand(BaseCommand):
    """状态指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "状态"
        self.description = "显示系统运行状态"
        self.usage = "状态"
        self.aliases = ["status", "stat"]
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行状态指令"""
        try:
            config_manager = context["config_manager"]
            database_manager = context["database_manager"]
            
            # 获取系统状态
            status_info = "🔍 系统状态信息\n\n"
            
            # 配置信息
            global_config = config_manager.get_global_config()
            connections_config = config_manager.get_connections_config()
            
            status_info += f"📋 配置状态:\n"
            status_info += f"  • 连接配置: {len(connections_config)} 个\n"
            status_info += f"  • 最近活跃账号: {len(await config_manager.get_recently_active_accounts())}/{len(config_manager.get_all_account_configs())}个\n"
            status_info += f"  • 最近活跃群聊: {len(await config_manager.get_recently_active_groups())}/{len(config_manager.get_all_group_configs())}个\n"
            
            # 数据库信息
            try:
                db_config = global_config.get("database", {})
                status_info += f"💾 数据库状态:\n"
                status_info += f"  • 数据库大小: {database_manager.get_database_size() / 1024 / 1024:.2f} MB\n"
                status_info += f"  • 记录条数: {await database_manager.get_total_message_count()} 条\n"
                status_info += "  • 消息保留: {} 天\n".format(db_config.get('auto_expire_days', 30))
                
            except Exception as e:
                status_info += f"💾 数据库状态: 获取失败 ({e})\n"
                
            # 系统状态
            status_info += f"💻 系统状态:\n"
            # 获取当前进程和系统资源占用
            process = psutil.Process()
            app_cpu = process.cpu_percent(interval=3)
            total_cpu = psutil.cpu_percent(interval=3)
            app_mem = process.memory_info().rss / (1024 * 1024)  # MB
            total_mem = psutil.virtual_memory().used / (1024 * 1024)  # MB
            total_mem_percent = psutil.virtual_memory().percent

            status_info += f"  • CPU: {app_cpu:.1f}% / {total_cpu:.1f}%\n"
            status_info += f"  • 内存: {app_mem:.1f}MB / {total_mem:.1f}MB ({total_mem_percent:.1f}%)\n"
            
            status_info += "\n🕐 当前UTC时间: {}".format(context.get('timestamp', '未知'))
            
            return self.format_response(status_info, use_forward=True)
            
        except Exception as e:
            return self.format_error(f"获取状态信息失败: {e}")
        
class PINGCommand(BaseCommand):
    """PING指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "PING"
        self.description = "测试连接是否正常"
        self.usage = "PING"
        self.aliases = ["ping"]
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行PING指令"""
        return self.format_response("pong")


class EchoCommand(BaseCommand):
    """Echo指令"""

    def __init__(self):
        super().__init__()
        self.name = "echo"
        self.description = "复读"
        self.usage = "echo xxx"
        self.aliases = ["Echo"]
        self.required_permission = PermissionLevel.SUPERUSER

    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()

    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行PING指令"""
        return self.format_response(" ".join(args))


class UpdateCommand(BaseCommand):
    """更新指令"""

    def __init__(self):
        super().__init__()
        self.name = "更新"
        self.description = "检查并执行系统更新"
        self.usage = "更新"
        self.aliases = ["update"]
        self.required_permission = PermissionLevel.SUPERUSER

    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()

    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行更新指令"""
        try:
            import asyncio
            import subprocess
            import os
            import requests
            import re
            from app import __version__

            # 检查是否有新版本
            try:
                # 获取代理配置
                config_manager = context["config_manager"]
                global_config = config_manager.get_global_config()
                proxy = global_config.get("proxy", "")
                proxies = {"http": proxy, "https": proxy} if proxy else None

                # 联网和 git pull 都放线程里跑，别卡住消息转发
                response = await asyncio.to_thread(
                    requests.get,
                    "https://raw.githubusercontent.com/Loping151/BotShepherd/main/app/__init__.py",
                    timeout=5,
                    proxies=proxies
                )
                response.raise_for_status()
                content = response.text

                version_match = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", content)
                if not version_match:
                    return self.format_error("无法获取远程版本信息")

                remote_version = version_match.group(1)

                if remote_version == __version__:
                    return self.format_response(f"当前已是最新版本 {__version__}，无需更新")

                # 执行更新
                update_info = f"发现新版本 {remote_version}（当前版本：{__version__}）\n"

                # 获取项目根目录
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

                # 执行 git pull
                result = await asyncio.to_thread(
                    subprocess.run,
                    ['git', 'pull'],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    update_info += "✅ 更新成功！\n"
                    update_info += f"输出:\n{result.stdout}\n"
                    update_info += "⚠️ 请使用 bs重启 指令重启系统以应用更新"
                    return self.format_response(update_info, use_forward=True)
                else:
                    return self.format_error(f"更新失败:\n{result.stderr}", use_forward=True)

            except requests.RequestException as e:
                return self.format_error(f"无法连接到GitHub检查更新: {e}")
            except subprocess.TimeoutExpired:
                return self.format_error("更新超时，请稍后重试")
            except FileNotFoundError:
                return self.format_error("Git未安装，无法执行更新")

        except Exception as e:
            return self.format_error(f"更新失败: {e}")


# 注册指令
def register_basic_commands():
    """注册指令"""
    command_registry.register(HelpCommand())
    command_registry.register(StatusCommand())
    command_registry.register(PINGCommand())
    command_registry.register(EchoCommand())
    command_registry.register(UpdateCommand())

register_basic_commands()