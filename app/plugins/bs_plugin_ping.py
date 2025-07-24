"""
示例插件
"""

from typing import Dict, Any, List
from app.onebotv11.models import Event
from app.commands.permission_manager import PermissionLevel
from app.commands.base_command import BaseCommand, CommandResponse, CommandResult, command_registry
        
class SamplePluginCommand(BaseCommand):
    """PING指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "plugin"
        self.description = "样例单文件插件实现"
        self.usage = "plugin"
        self.aliases = []
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行PING指令"""
        return self.format_response("插件存在！这是一个单文件插件！")

# 注册指令
def register_sample_commands():
    """注册基础指令"""
    command_registry.register(SamplePluginCommand())
    
register_sample_commands()
