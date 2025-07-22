"""
权限管理器
管理用户权限和访问控制
"""

from typing import Dict, Any, Optional, List
from enum import Enum

from ..onebotv11.models import Event, PrivateMessageEvent, GroupMessageEvent, Role

class PermissionLevel(Enum):
    """权限等级"""
    SUPERUSER = 3
    ADMIN = 2
    MEMBER = 1
    UNKNOWN = 0

class PermissionManager:
    """权限管理器"""
    
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
    
    def get_user_permission_level(self, event: Event) -> PermissionLevel:
        """获取用户权限等级"""
        try:
            user_id = str(event.user_id)
            
            # 检查是否为超级用户
            if self.config_manager.is_superuser(user_id):
                return PermissionLevel.SUPERUSER
            
            # 群消息中检查群内角色
            if isinstance(event, GroupMessageEvent):
                sender_role = event.sender.role if event.sender else None
                
                if sender_role == Role.OWNER:
                    return PermissionLevel.ADMIN
                elif sender_role == Role.ADMIN:
                    return PermissionLevel.ADMIN
                elif sender_role == Role.MEMBER:
                    return PermissionLevel.MEMBER
                else:
                    return PermissionLevel.UNKNOWN
            
            # 私聊消息默认为普通成员
            elif isinstance(event, PrivateMessageEvent):
                return PermissionLevel.MEMBER
            
            return PermissionLevel.UNKNOWN
            
        except Exception as e:
            self.logger.command.error(f"获取用户权限等级失败: {e}")
            return PermissionLevel.UNKNOWN
    
    def check_permission(self, event: Event, required_level: PermissionLevel) -> bool:
        """检查权限"""
        user_level = self.get_user_permission_level(event)
        return user_level.value >= required_level.value
    
    def check_superuser_permission(self, event: Event) -> bool:
        """检查超级用户权限"""
        return self.check_permission(event, PermissionLevel.SUPERUSER)
    
    def check_admin_permission(self, event: Event) -> bool:
        """检查管理员权限"""
        return self.check_permission(event, PermissionLevel.ADMIN)
    
    def check_member_permission(self, event: Event) -> bool:
        """检查成员权限"""
        return self.check_permission(event, PermissionLevel.MEMBER)
    
    def get_permission_description(self, level: PermissionLevel) -> str:
        """获取权限等级描述"""
        descriptions = {
            PermissionLevel.SUPERUSER: "超级用户",
            PermissionLevel.ADMIN: "管理员",
            PermissionLevel.MEMBER: "普通成员",
            PermissionLevel.UNKNOWN: "未知用户"
        }
        return descriptions.get(level, "未知")
    