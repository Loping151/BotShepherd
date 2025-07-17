"""
安全管理器
集成权限管理和过滤机制
"""

from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta

from ..onebotv11.models import Event, PrivateMessageEvent, GroupMessageEvent
from .permission_manager import PermissionManager, PermissionLevel
from .filter_manager import FilterManager, FilterAction, FilterType

class SecurityManager:
    """安全管理器"""
    
    def __init__(self, config_manager, database_manager, logger):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.logger = logger
        
        # 初始化子管理器
        self.permission_manager = PermissionManager(config_manager, logger)
        self.filter_manager = FilterManager(config_manager, self.permission_manager, logger)
        
        # 安全统计
        self.security_stats = {
            "permission_denials": 0,
            "filter_blocks": 0,
            "blacklist_blocks": 0,
            "rate_limit_blocks": 0
        }
        
        # 速率限制缓存
        self.rate_limit_cache = {}
    
    async def check_message_security(self, event: Event, 
                                   message_data: Dict[str, Any],
                                   direction: str) -> Tuple[bool, str, Dict[str, Any]]:
        """检查消息安全性"""
        try:
            # 1. 权限检查
            if not await self._check_basic_permissions(event):
                self.security_stats["permission_denials"] += 1
                return False, "权限不足", message_data
            
            # 2. 速率限制检查
            if not await self._check_rate_limit(event):
                self.security_stats["rate_limit_blocks"] += 1
                return False, "触发速率限制", message_data
            
            # 3. 消息过滤
            if direction == "receive":
                filtered, reason, modified_data = await self.filter_manager.filter_receive_message(
                    event, message_data
                )
            else:
                filtered, reason, modified_data = await self.filter_manager.filter_send_message(
                    event, message_data
                )
            
            if not filtered:
                self.security_stats["filter_blocks"] += 1
                return False, reason, modified_data
            
            # 4. 记录安全日志
            await self._log_security_check(event, "PASS", f"安全检查通过 - {direction}")
            
            return True, "安全检查通过", modified_data
            
        except Exception as e:
            self.logger.error(f"安全检查失败: {e}")
            return True, "安全检查错误，默认通过", message_data
    
    async def check_command_permission(self, event: Event, command_name: str) -> Tuple[bool, str]:
        """检查指令权限"""
        try:
            # 检查基本权限
            if not await self._check_basic_permissions(event):
                return False, "基本权限不足"
            
            # 检查指令权限
            if not self.permission_manager.can_execute_command(event, command_name):
                user_level = self.permission_manager.get_user_permission_level(event)
                required_level = self.permission_manager._get_command_permission_requirement(command_name)
                
                await self.permission_manager.log_permission_check(
                    event, command_name, False, 
                    f"权限不足: {user_level.name} < {required_level.name}"
                )
                
                return False, f"权限不足，需要 {self.permission_manager.get_permission_description(required_level)} 权限"
            
            # 记录权限检查通过
            await self.permission_manager.log_permission_check(event, command_name, True)
            
            return True, "权限检查通过"
            
        except Exception as e:
            self.logger.error(f"指令权限检查失败: {e}")
            return False, "权限检查错误"
    
    async def _check_basic_permissions(self, event: Event) -> bool:
        """检查基本权限"""
        # 检查账号是否启用
        account_config = self.config_manager.get_account_config(str(event.self_id))
        if account_config and not account_config.get("enabled", True):
            return False
        
        # 检查群组权限
        if isinstance(event, GroupMessageEvent):
            group_config = self.config_manager.get_group_config(str(event.group_id))
            if group_config:
                # 检查群组是否启用
                if not group_config.get("enabled", True):
                    return False
                
                # 检查群组是否过期
                if self.config_manager.is_group_expired(str(event.group_id)):
                    return False
        
        return True
    
    async def _check_rate_limit(self, event: Event) -> bool:
        """检查速率限制"""
        try:
            # 获取速率限制配置
            global_config = await self.config_manager.get_global_config()
            rate_limit_config = global_config.get("rate_limit", {})
            
            if not rate_limit_config.get("enabled", False):
                return True
            
            # 用户级别速率限制
            user_id = str(event.user_id)
            user_limit = rate_limit_config.get("user_messages_per_minute", 60)
            
            if not await self._check_user_rate_limit(user_id, user_limit):
                return False
            
            # 群组级别速率限制
            if isinstance(event, GroupMessageEvent):
                group_id = str(event.group_id)
                group_limit = rate_limit_config.get("group_messages_per_minute", 300)
                
                if not await self._check_group_rate_limit(group_id, group_limit):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"速率限制检查失败: {e}")
            return True  # 出错时默认通过
    
    async def _check_user_rate_limit(self, user_id: str, limit: int) -> bool:
        """检查用户速率限制"""
        current_time = datetime.now()
        cache_key = f"user_{user_id}"
        
        if cache_key not in self.rate_limit_cache:
            self.rate_limit_cache[cache_key] = []
        
        # 清理过期记录
        cutoff_time = current_time - timedelta(minutes=1)
        self.rate_limit_cache[cache_key] = [
            timestamp for timestamp in self.rate_limit_cache[cache_key]
            if timestamp > cutoff_time
        ]
        
        # 检查是否超过限制
        if len(self.rate_limit_cache[cache_key]) >= limit:
            return False
        
        # 记录当前请求
        self.rate_limit_cache[cache_key].append(current_time)
        return True
    
    async def _check_group_rate_limit(self, group_id: str, limit: int) -> bool:
        """检查群组速率限制"""
        current_time = datetime.now()
        cache_key = f"group_{group_id}"
        
        if cache_key not in self.rate_limit_cache:
            self.rate_limit_cache[cache_key] = []
        
        # 清理过期记录
        cutoff_time = current_time - timedelta(minutes=1)
        self.rate_limit_cache[cache_key] = [
            timestamp for timestamp in self.rate_limit_cache[cache_key]
            if timestamp > cutoff_time
        ]
        
        # 检查是否超过限制
        if len(self.rate_limit_cache[cache_key]) >= limit:
            return False
        
        # 记录当前请求
        self.rate_limit_cache[cache_key].append(current_time)
        return True
    
    async def _log_security_check(self, event: Event, result: str, reason: str):
        """记录安全检查日志"""
        try:
            log_info = {
                "self_id": getattr(event, 'self_id', None),
                "user_id": event.user_id,
                "result": result,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            
            if isinstance(event, GroupMessageEvent):
                log_info["group_id"] = event.group_id
            
            if result == "PASS":
                self.logger.debug(f"安全检查: {log_info}")
            else:
                self.logger.warning(f"安全检查失败: {log_info}")
                
        except Exception as e:
            self.logger.error(f"记录安全日志失败: {e}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计"""
        return {
            **self.security_stats,
            "rate_limit_cache_size": len(self.rate_limit_cache),
            "timestamp": datetime.now().isoformat()
        }
    
    def reset_security_stats(self):
        """重置安全统计"""
        self.security_stats = {
            "permission_denials": 0,
            "filter_blocks": 0,
            "blacklist_blocks": 0,
            "rate_limit_blocks": 0
        }
    
    async def cleanup_rate_limit_cache(self):
        """清理速率限制缓存"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=5)  # 清理5分钟前的记录
        
        for cache_key in list(self.rate_limit_cache.keys()):
            self.rate_limit_cache[cache_key] = [
                timestamp for timestamp in self.rate_limit_cache[cache_key]
                if timestamp > cutoff_time
            ]
            
            # 删除空的缓存项
            if not self.rate_limit_cache[cache_key]:
                del self.rate_limit_cache[cache_key]
    
    def get_user_security_info(self, event: Event) -> Dict[str, Any]:
        """获取用户安全信息"""
        permission_level = self.permission_manager.get_user_permission_level(event)
        available_commands = self.permission_manager.get_available_commands(event)
        
        info = {
            "user_id": event.user_id,
            "permission_level": permission_level.name,
            "permission_description": self.permission_manager.get_permission_description(permission_level),
            "is_superuser": self.config_manager.is_superuser(str(event.user_id)),
            "available_commands": available_commands,
            "in_blacklist": self.config_manager.is_in_blacklist("users", str(event.user_id))
        }
        
        if isinstance(event, GroupMessageEvent):
            info.update({
                "group_id": event.group_id,
                "group_role": event.sender.role.value if event.sender and event.sender.role else None,
                "group_in_blacklist": self.config_manager.is_in_blacklist("groups", str(event.group_id)),
                "group_enabled": True,
                "group_expired": False
            })
            
            # 检查群组状态
            group_config = self.config_manager.get_group_config(str(event.group_id))
            if group_config:
                info["group_enabled"] = group_config.get("enabled", True)
                info["group_expired"] = self.config_manager.is_group_expired(str(event.group_id))
        
        return info
    
    async def validate_security_config(self) -> List[str]:
        """验证安全配置"""
        issues = []
        
        try:
            global_config = await self.config_manager.get_global_config()
            
            # 检查超级用户配置
            superusers = global_config.get("superusers", [])
            if not superusers:
                issues.append("未配置超级用户")
            
            # 检查黑名单配置
            blacklist = global_config.get("blacklist", {})
            if not isinstance(blacklist, dict):
                issues.append("黑名单配置格式错误")
            
            # 检查过滤词配置
            global_filters = global_config.get("global_filters", {})
            if not isinstance(global_filters, dict):
                issues.append("全局过滤词配置格式错误")
            
            # 检查权限配置
            if not global_config.get("command_prefix"):
                issues.append("未配置指令前缀")
            
        except Exception as e:
            issues.append(f"配置验证错误: {e}")
        
        return issues
