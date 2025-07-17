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
            self.logger.error(f"获取用户权限等级失败: {e}")
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
    
    def can_execute_command(self, event: Event, command_name: str) -> bool:
        """检查是否可以执行指令"""
        # 获取指令权限要求
        required_level = self._get_command_permission_requirement(command_name)
        
        # 检查权限
        return self.check_permission(event, required_level)
    
    def _get_command_permission_requirement(self, command_name: str) -> PermissionLevel:
        """获取指令权限要求"""
        # 超级用户指令
        superuser_commands = [
            "设置黑名单", "移除黑名单", "添加超级用户", "移除超级用户",
            "设置全局过滤", "移除全局过滤", "系统重启", "系统关闭",
            "配置备份", "配置恢复", "数据库优化"
        ]
        
        # 管理员指令
        admin_commands = [
            "设置群过滤", "移除群过滤", "设置群到期", "群组开关",
            "踢出群员", "禁言", "解除禁言", "设置管理员"
        ]
        
        # 普通成员指令
        member_commands = [
            "帮助", "统计", "查询", "状态"
        ]
        
        if command_name in superuser_commands:
            return PermissionLevel.SUPERUSER
        elif command_name in admin_commands:
            return PermissionLevel.ADMIN
        elif command_name in member_commands:
            return PermissionLevel.MEMBER
        else:
            # 默认需要成员权限
            return PermissionLevel.MEMBER
    
    def get_permission_description(self, level: PermissionLevel) -> str:
        """获取权限等级描述"""
        descriptions = {
            PermissionLevel.SUPERUSER: "超级用户",
            PermissionLevel.ADMIN: "管理员",
            PermissionLevel.MEMBER: "普通成员",
            PermissionLevel.UNKNOWN: "未知用户"
        }
        return descriptions.get(level, "未知")
    
    def format_permission_info(self, event: Event) -> str:
        """格式化权限信息"""
        level = self.get_user_permission_level(event)
        description = self.get_permission_description(level)
        
        info_parts = [f"权限等级: {description}"]
        
        if isinstance(event, GroupMessageEvent):
            role_desc = {
                Role.OWNER: "群主",
                Role.ADMIN: "管理员", 
                Role.MEMBER: "成员"
            }
            sender_role = event.sender.role if event.sender else None
            if sender_role:
                info_parts.append(f"群内角色: {role_desc.get(sender_role, '未知')}")
        
        if self.config_manager.is_superuser(str(event.user_id)):
            info_parts.append("✓ 超级用户")
        
        return " | ".join(info_parts)
    
    async def log_permission_check(self, event: Event, command_name: str, 
                                 allowed: bool, reason: str = ""):
        """记录权限检查日志"""
        try:
            user_level = self.get_user_permission_level(event)
            required_level = self._get_command_permission_requirement(command_name)
            
            log_info = {
                "user_id": event.user_id,
                "command": command_name,
                "user_level": user_level.name,
                "required_level": required_level.name,
                "allowed": allowed,
                "reason": reason
            }
            
            if isinstance(event, GroupMessageEvent):
                log_info["group_id"] = event.group_id
                log_info["sender_role"] = event.sender.role.value if event.sender and event.sender.role else None
            
            if allowed:
                self.logger.info(f"权限检查通过: {log_info}")
            else:
                self.logger.warning(f"权限检查失败: {log_info}")
                
        except Exception as e:
            self.logger.error(f"记录权限检查日志失败: {e}")
    
    def get_available_commands(self, event: Event) -> List[str]:
        """获取用户可用的指令列表"""
        user_level = self.get_user_permission_level(event)
        
        available_commands = []
        
        # 所有指令列表
        all_commands = {
            # 普通成员指令
            "帮助": PermissionLevel.MEMBER,
            "统计": PermissionLevel.MEMBER,
            "查询": PermissionLevel.MEMBER,
            "状态": PermissionLevel.MEMBER,
            
            # 管理员指令
            "设置群过滤": PermissionLevel.ADMIN,
            "移除群过滤": PermissionLevel.ADMIN,
            "设置群到期": PermissionLevel.ADMIN,
            "群组开关": PermissionLevel.ADMIN,
            "踢出群员": PermissionLevel.ADMIN,
            "禁言": PermissionLevel.ADMIN,
            "解除禁言": PermissionLevel.ADMIN,
            "设置管理员": PermissionLevel.ADMIN,
            
            # 超级用户指令
            "设置黑名单": PermissionLevel.SUPERUSER,
            "移除黑名单": PermissionLevel.SUPERUSER,
            "添加超级用户": PermissionLevel.SUPERUSER,
            "移除超级用户": PermissionLevel.SUPERUSER,
            "设置全局过滤": PermissionLevel.SUPERUSER,
            "移除全局过滤": PermissionLevel.SUPERUSER,
            "系统重启": PermissionLevel.SUPERUSER,
            "系统关闭": PermissionLevel.SUPERUSER,
            "配置备份": PermissionLevel.SUPERUSER,
            "配置恢复": PermissionLevel.SUPERUSER,
            "数据库优化": PermissionLevel.SUPERUSER,
        }
        
        for command, required_level in all_commands.items():
            if user_level.value >= required_level.value:
                available_commands.append(command)
        
        return available_commands
    
    def check_group_permission(self, event: Event, group_id: str, 
                             action: str) -> tuple[bool, str]:
        """检查群组权限"""
        if not isinstance(event, GroupMessageEvent):
            return False, "非群组消息"
        
        if str(event.group_id) != group_id:
            return False, "群组不匹配"
        
        user_level = self.get_user_permission_level(event)
        
        # 超级用户可以执行所有操作
        if user_level == PermissionLevel.SUPERUSER:
            return True, "超级用户权限"
        
        # 群主和管理员可以执行群组管理操作
        if user_level == PermissionLevel.ADMIN:
            admin_actions = ["设置群过滤", "移除群过滤", "踢出群员", "禁言", "解除禁言"]
            if action in admin_actions:
                return True, "管理员权限"
        
        # 普通成员只能执行查询操作
        if user_level == PermissionLevel.MEMBER:
            member_actions = ["查询", "统计", "帮助"]
            if action in member_actions:
                return True, "成员权限"
        
        return False, f"权限不足，需要更高权限执行 {action}"
    
    def bypass_whitelist_check(self, event: Event) -> bool:
        """检查是否绕过白名单检查"""
        # 超级用户消息绕过白名单检查
        return self.check_superuser_permission(event)
