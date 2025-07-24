import asyncio
import os
import sys
from typing import Dict, Any, List
from ...onebotv11.models import Event
from ...utils.reboot import reboot
from ..permission_manager import PermissionLevel
from ..base_command import BaseCommand, CommandResponse, CommandResult, command_registry

class RestartCommand(BaseCommand):
    """重启指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "重启"
        self.description = "重启本程序"
        self.usage = "重启"
        self.aliases = ["restart"]
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行重启指令"""
        try:
            # 创建一个后台任务来执行重启逻辑，这样不会阻塞当前响应
            loop = asyncio.get_event_loop()
            loop.create_task(reboot(event, wait_seconds = 3))
            
            # 立即返回一个消息，告知用户重启指令已收到
            return self.format_info("将在3秒后重启...")

        except Exception as e:
            return self.format_error(f"执行重启指令失败: {e}")

class SettingCommand(BaseCommand):
    """切换指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "设置"
        self.description = "管理本群或指定账号的启用状态"
        self.usage = "bs设置 开启/关闭 [id/本账号]"
        self.example = """
    bs设置 开启 (默认为群)
    bs设置 关闭
    bs设置 开启 123456789 (SUPERUSER)
    bs设置 关闭 本账号 (SUPERUSER)"""
        self.aliases = ["set"]
        self.required_permission = PermissionLevel.ADMIN

    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()

        subparsers = self.parser.add_subparsers(dest="action", help="操作类型")

        # 开启子命令
        enable_parser = subparsers.add_parser("开启", aliases=["enable", "on"], help="开启功能")
        enable_parser.add_argument("target", nargs="?", help="目标QQ号或 '本账号' (仅限SUPERUSER)")

        # 关闭子命令
        disable_parser = subparsers.add_parser("关闭", aliases=["disable", "off"], help="关闭功能")
        disable_parser.add_argument("target", nargs="?", help="目标QQ号或 '本账号' (可选，仅限SUPERUSER)")

    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行设置指令"""
        try:
            parsed_args = self.parse_args(args)
            if isinstance(parsed_args, str):
                return self.format_error(parsed_args, CommandResult.INVALID_ARGS, use_forward=True)

            config_manager = context["config_manager"]
            is_superuser = config_manager.is_superuser(event.user_id)

            action = parsed_args.action
            target = parsed_args.target
            enabled = True if action in ["开启", "enable", "on"] else False

            if target:
                if not is_superuser:
                    return None

                if target in ["本账号", "你"]:
                    account_id = str(event.self_id)  # 假设 event.self_id 是当前机器人的QQ号
                    return await self._set_account_status(account_id, enabled, config_manager)
                elif target.isdigit():
                    account_id = target
                    return await self._set_account_status(account_id, enabled, config_manager)
                else:
                    return self.format_error("无效的目标，请提供 QQ 号或 '本账号'。", CommandResult.INVALID_ARGS)
            else:
                if not hasattr(event, "group_id"):
                    return self.format_error("使用方法错误！", CommandResult.INVALID_ARGS)
                group_id = str(event.group_id)
                return await self._set_group_status(group_id, enabled, config_manager)

        except Exception as e:
            return self.format_error(f"BS 设置操作失败: {e}")

    async def _set_group_status(self, group_id: str, enabled: bool, config_manager) -> CommandResponse:
        """设置群组启用状态"""
        try:
            await config_manager.set_group_enabled(group_id, enabled)
            status_text = "开启" if enabled else "关闭"
            return self.format_success(f"已将群 {group_id} 设置为 {status_text}")
        except Exception as e:
            return self.format_error(f"设置群组状态失败: {e}")

    async def _set_account_status(self, account_id: str, enabled: bool, config_manager) -> CommandResponse:
        """设置账号启用状态"""
        try:
            await config_manager.set_account_enabled(account_id, enabled)
            status_text = "开启" if enabled else "关闭"
            return self.format_success(f"已将账号 {account_id} 设置为 {status_text}")
        except Exception as e:
            return self.format_error(f"设置账号状态失败: {e}")
        
class ReloadCommand(BaseCommand):
    """重载指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "重载"
        self.description = "重载配置文件"
        self.usage = "重载"
        self.aliases = ["reload"]
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行重载指令"""
        try:
            config_manager = context["config_manager"]
            await config_manager._load_all_configs()
            return self.format_success("已重载配置文件")
        except Exception as e:
            return self.format_error(f"重载配置文件失败: {e}")
    
            
def register_control_commands():
    command_registry.register(RestartCommand())
    command_registry.register(SettingCommand())

register_control_commands()