"""
示例插件
"""

from typing import Dict, Any, List
import base64
from ....onebotv11.models import Event, MessageSegment
from ....onebotv11.message_segment import MessageSegmentBuilder
from ...permission_manager import PermissionLevel
from ...base_command import BaseCommand, CommandResponse, CommandResult, command_registry
        
class SamplePluginCommand(BaseCommand):
    """PING指令"""
    
    def __init__(self):
        super().__init__()
        self.name = "image"
        self.description = "样例插件实现"
        self.usage = "image"
        self.aliases = []
        self.required_permission = PermissionLevel.SUPERUSER
    
    def _setup_parser(self):
        """设置参数解析器"""
        super()._setup_parser()
    
    async def execute(self, event: Event, args: List[str], context: Dict[str, Any]) -> CommandResponse:
        """执行PING指令"""
        test_image = "./data/test.png"
        with open(test_image, "rb") as f:
            image_data = f.read()
            image_base64 = "base64://" + base64.b64encode(image_data).decode("utf-8")
        test_image_seg = MessageSegmentBuilder.image(file=image_base64)

        return self.format_response(["这是一个测试nonebot插件直接移植，你应该看到图片：", test_image_seg], use_forward=True if "转发" in args else False)

# 注册指令
def register_sample_commands():
    """注册基础指令"""
    command_registry.register(SamplePluginCommand())
    
register_sample_commands()
