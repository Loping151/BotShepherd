"""
备份指令
立即执行配置备份并发送文件
"""

import base64
from typing import Dict, Any, List
from ...onebotv11.models import Event
from ...onebotv11.message_segment import MessageSegmentBuilder
from ..permission_manager import PermissionLevel
from ..base_command import BaseCommand, CommandResponse, CommandResult, command_registry


class BackupCommand(BaseCommand):
    """备份指令"""

    def __init__(self):
        super().__init__()
        self.name = "备份"
        self.description = "立即创建配置备份并发送"
        self.usage = "备份"
        self.aliases = ["backup"]
        self.required_permission = PermissionLevel.SUPERUSER

    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()

    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行备份指令"""
        try:
            # 获取backup_manager
            if "backup_manager" not in context:
                return self.format_error("备份管理器未初始化")

            backup_manager = context["backup_manager"]
            config_manager = context["config_manager"]

            # 获取密码
            global_config = config_manager.get_global_config()
            web_auth = global_config.get("web_auth", {})
            password = web_auth.get("password", "admin")

            # 执行备份
            backup_path = backup_manager.create_backup(password)

            if not backup_path:
                return self.format_error("备份失败，请检查日志")

            # 读取备份文件
            try:
                import os

                with open(backup_path, "rb") as f:
                    file_data = f.read()
                    file_base64 = "base64://" + base64.b64encode(file_data).decode("utf-8")

                # 获取文件名
                filename = os.path.basename(backup_path)

                # 创建文件消息段
                file_segment = MessageSegmentBuilder.file(
                    file=file_base64,
                    name=filename
                )

                # 删除临时备份文件（bs备份命令创建的备份仅用于发送，不保留）
                try:
                    os.remove(backup_path)
                except Exception as e:
                    # 删除失败不影响返回
                    pass

                return self.format_response([
                    file_segment
                ], use_forward=False)

            except Exception as e:
                # 如果读取失败，尝试清理备份文件
                try:
                    import os
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                except Exception:
                    pass
                return self.format_error(f"读取备份文件失败: {e}")

        except Exception as e:
            return self.format_error(f"执行备份失败: {e}")


# 注册指令
def register_backup_commands():
    """注册备份指令"""
    command_registry.register(BackupCommand())


register_backup_commands()
