import asyncio
import os
import sys
from typing import Dict, Any, List
from ...onebotv11.models import Event
from ...utils.reboot import reboot
from ..permission_manager import PermissionLevel
from ..base_command import BaseCommand, CommandResponse, CommandResult, command_registry


class AliasCommand(BaseCommand):
    """别名管理指令"""

    def __init__(self):
        super().__init__()
        self.name = "别名"
        self.description = "管理群组、账号或全局的指令别名"
        self.usage = "别名 [add/remove/list] [类型] [别名] [目标指令名] [群号/QQ号]"
        self.example = """
    别名 添加 # yunzai，# echo (当前群，如果保留原指令需要把原指令设为别名，逗号隔开)
    别名 移除 # yunzai echo
    别名 添加 账号 # yunzai 123456789
    别名 添加 全局 # yunzai
    别名 移除 全局 # yunzai
    别名 查看 全局
    别名 查看 账号 123456789
    别名 查看 (在群聊中，默认查看当前群别名)""" # 更新了示例
        self.aliases = ["alias", "bm"]
        self.required_permission = PermissionLevel.ADMIN

    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()

        subparsers = self.parser.add_subparsers(dest="action", help="操作类型")

        # 添加子命令
        add_parser = subparsers.add_parser("添加", aliases=["add", "+"], help="添加别名")
        # 修改：type 参数变为可选
        add_parser.add_argument("type", choices=["群聊", "账号", "全局"], nargs="?", default="群聊", help="别名类型：群聊、账号、全局 (默认为群聊)")
        add_parser.add_argument("target", help="目标指令名")
        add_parser.add_argument("alias", help="要移除的别名")
        add_parser.add_argument("id", nargs="?", help="群号或账号 (仅用于账号类型或指定群聊)")

        # 移除子命令
        remove_parser = subparsers.add_parser("移除", aliases=["remove", "rm", "-"], help="移除别名")
        # 修改：type 参数变为可选
        remove_parser.add_argument("type", choices=["群聊", "账号", "全局"], nargs="?", default="群聊", help="别名类型：群聊、账号、全局 (默认为群聊)")
        remove_parser.add_argument("target", help="目标指令名")
        remove_parser.add_argument("alias", help="要移除的别名")
        remove_parser.add_argument("id", nargs="?", help="群号或账号 (仅用于账号类型或指定群聊)")

        # 查看子命令
        list_parser = subparsers.add_parser("查看", aliases=["list", "ls"], help="查看别名")
        list_parser.add_argument("type_or_id", nargs="?", help="别名类型（群聊、账号、全局）或群号/账号。如果只提供一个数字，则认为是群号/账号。")
        list_parser.add_argument("id_optional", nargs="?", help="群号或账号 (仅在 type_or_id 是类型时使用)")


    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行别名指令"""
        try:
            parsed_args = self.parse_args(args)
            if isinstance(parsed_args, str):
                return self.format_error(parsed_args, CommandResult.INVALID_ARGS, use_forward=True)

            config_manager = context["config_manager"]
            is_superuser = config_manager.is_superuser(event.user_id)

            action = parsed_args.action
            
            # 处理 '查看' 命令的特殊逻辑
            if action in ["查看", "list", "ls"]:
                alias_type = "群聊"  # 默认类型为群聊
                entity_id = None
                
                if parsed_args.type_or_id:
                    if parsed_args.type_or_id in ["群聊", "账号", "全局"]:
                        alias_type = parsed_args.type_or_id
                        if parsed_args.id_optional:
                            entity_id = parsed_args.id_optional
                    elif parsed_args.type_or_id.isdigit(): # 如果只提供一个数字，认为是群号/QQ号，默认为群聊
                        alias_type = "群聊"
                        entity_id = parsed_args.type_or_id
                    else: # 非法的第一个参数
                        return self.format_error("无效的查看类型或ID。请使用 '群聊', '账号', '全局' 或指定数字ID。", CommandResult.INVALID_ARGS)

                # 权限检查 for '查看'
                if alias_type in ["账号", "全局"] and not is_superuser:
                    return None

                if alias_type == "群聊":
                    if not entity_id: # 如果没有指定群ID，则默认查看当前群
                        if not hasattr(event, "group_id"):
                            return self.format_error("请在群聊中使用 '别名 查看' 或指定群号。", CommandResult.INVALID_ARGS)
                        entity_id = str(event.group_id)
                    elif not entity_id.isdigit():
                        return self.format_error("群号必须是数字。", CommandResult.INVALID_ARGS)
                elif alias_type == "账号":
                    if not entity_id or not entity_id.isdigit():
                         return self.format_error("查看账号别名必须指定有效的账号。", CommandResult.INVALID_ARGS)
                # 全局类型不需要entity_id

                return await self._list_aliases_action(alias_type, entity_id, config_manager)
            
            # 处理 '添加' 和 '移除' 命令
            else:
                # parsed_args.type 现在有了 default="群聊"
                alias_type = parsed_args.type 
                alias = parsed_args.alias
                target_cmd = parsed_args.target
                target_id = parsed_args.id

                # 权限检查 for '添加'/'移除'
                if alias_type in ["账号", "全局"] and not is_superuser:
                    return None
                
                # 确定操作的实体ID
                actual_id = None
                if alias_type == "群聊":
                    if not target_id: # 如果没有指定群ID，使用当前群的ID
                        if not hasattr(event, "group_id"):
                            return self.format_error("添加/移除群聊别名必须在群内执行或指定群号。", CommandResult.INVALID_ARGS)
                        actual_id = str(event.group_id)
                    elif not target_id.isdigit():
                        return self.format_error("群号必须是数字。", CommandResult.INVALID_ARGS)
                    else:
                        actual_id = target_id
                elif alias_type == "账号":
                    if not target_id or not target_id.isdigit():
                        return self.format_error("管理账号别名必须指定有效的账号。", CommandResult.INVALID_ARGS)
                    actual_id = target_id
                # 全局类型不需要 actual_id


                if action in ["添加", "add", "+"]:
                    return await self._add_alias_action(alias_type, alias, target_cmd, actual_id, config_manager)
                elif action in ["移除", "remove", "rm", "-"]:
                    return await self._remove_alias_action(alias_type, alias, target_cmd, actual_id, config_manager)

        except ValueError as ve:
            return self.format_error(f"别名操作失败: {ve}", CommandResult.FAILED)
        except Exception as e:
            return self.format_error(f"别名操作失败: {e}")

    async def _add_alias_action(self, alias_type: str, alias: str, target: str, entity_id: str, config_manager) -> CommandResponse:
        """添加别名操作的逻辑封装"""
        try:
            if alias_type == "全局":
                await config_manager.add_global_alias(alias, target)
                return self.format_success(f"已将全局别名 {alias} -> {target} 添加成功。")
            elif alias_type == "账号":
                await config_manager.add_account_alias(entity_id, alias, target)
                return self.format_success(f"已将账号 {entity_id} 的别名 {alias} -> {target} 添加成功。")
            elif alias_type == "群聊":
                await config_manager.add_group_alias(entity_id, alias, target)
                return self.format_success(f"已将群 {entity_id} 的别名 {alias} -> {target} 添加成功。")
            
        except ValueError as ve:
            return self.format_error(f"添加别名失败: {ve}")
        except Exception as e:
            return self.format_error(f"添加别名时发生错误: {e}")


    async def _remove_alias_action(self, alias_type: str, alias: str, target: str, entity_id: str, config_manager) -> CommandResponse:
        """移除别名操作的逻辑封装"""
        try:
            if alias_type == "全局":
                await config_manager.remove_global_alias(alias, target)
                return self.format_success(f"已将全局别名 {alias} -> {target} 移除成功。")
            elif alias_type == "账号":
                await config_manager.remove_account_alias(entity_id, alias, target)
                return self.format_success(f"已将账号 {entity_id} 的别名 {alias} -> {target} 移除成功。")
            elif alias_type == "群聊":
                await config_manager.remove_group_alias(entity_id, alias, target)
                return self.format_success(f"已将群 {entity_id} 的别名 {alias} -> {target} 移除成功。")
        except ValueError as ve:
            return self.format_error(f"移除别名失败: {ve}")
        except Exception as e:
            return self.format_error(f"移除别名时发生错误: {e}")

    async def _list_aliases_action(self, alias_type: str, entity_id: str, config_manager) -> CommandResponse:
        """查看别名操作的逻辑封装"""
        result = ""
        try:
            if alias_type == "全局":
                aliases = config_manager._global_config.get("global_aliases", {})
                result = "全局别名:\n"
            elif alias_type == "账号":
                account_config = config_manager.get_account_config(entity_id)
                if not account_config:
                    return self.format_error(f"账号 {entity_id} 未找到。")
                aliases = account_config.get("aliases", {})
                result = f"账号 {entity_id} 的别名:\n"
            elif alias_type == "群聊":
                group_config = config_manager.get_group_config(entity_id)
                if not group_config:
                    return self.format_error(f"群组 {entity_id} 未找到。")
                aliases = group_config.get("aliases", {})
                result = f"群组 {entity_id} 的别名:\n"
            
            if not aliases:
                result += "  暂无别名。"
            else:
                for target, alias_list in aliases.items():
                    result += f"  - {",".join(alias_list)} -> {target}\n"

            if result.count("\n") > 10: # 如果行数过多，使用转发消息
                return self.format_info(result.strip(), use_forward=True)
            else:
                return self.format_info(result.strip())

        except Exception as e:
            return self.format_error(f"查看别名失败: {e}")


def register_alias_command():
    command_registry.register(AliasCommand())

register_alias_command()