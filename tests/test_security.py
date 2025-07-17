"""
安全系统测试
测试权限管理和过滤机制
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.onebotv11.models import PrivateMessageEvent, GroupMessageEvent, Sender, Role
from app.websocket_proxy.permission_manager import PermissionManager, PermissionLevel
from app.websocket_proxy.filter_manager import FilterManager, FilterAction, FilterType
from app.websocket_proxy.security_manager import SecurityManager

class TestPermissionManager:
    """权限管理器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.config_manager = Mock()
        self.logger = Mock()
        self.permission_manager = PermissionManager(self.config_manager, self.logger)
    
    def test_superuser_permission(self):
        """测试超级用户权限"""
        # 模拟超级用户
        self.config_manager.is_superuser.return_value = True
        
        # 创建测试事件
        event = PrivateMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="private",
            sub_type="friend",
            message_id=1,
            user_id=888888,
            message=[],
            raw_message="test",
            font=0,
            sender=Sender(user_id=888888, nickname="test")
        )
        
        # 测试权限等级
        level = self.permission_manager.get_user_permission_level(event)
        assert level == PermissionLevel.SUPERUSER
        
        # 测试权限检查
        assert self.permission_manager.check_superuser_permission(event)
        assert self.permission_manager.check_admin_permission(event)
        assert self.permission_manager.check_member_permission(event)
    
    def test_group_admin_permission(self):
        """测试群管理员权限"""
        # 模拟非超级用户
        self.config_manager.is_superuser.return_value = False
        
        # 创建群管理员事件
        sender = Sender(user_id=777777, nickname="admin", role=Role.ADMIN)
        event = GroupMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="group",
            sub_type="normal",
            message_id=1,
            user_id=777777,
            group_id=666666,
            message=[],
            raw_message="test",
            font=0,
            sender=sender
        )
        
        # 测试权限等级
        level = self.permission_manager.get_user_permission_level(event)
        assert level == PermissionLevel.ADMIN
        
        # 测试权限检查
        assert not self.permission_manager.check_superuser_permission(event)
        assert self.permission_manager.check_admin_permission(event)
        assert self.permission_manager.check_member_permission(event)
    
    def test_regular_member_permission(self):
        """测试普通成员权限"""
        # 模拟非超级用户
        self.config_manager.is_superuser.return_value = False
        
        # 创建普通成员事件
        sender = Sender(user_id=555555, nickname="member", role=Role.MEMBER)
        event = GroupMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="group",
            sub_type="normal",
            message_id=1,
            user_id=555555,
            group_id=666666,
            message=[],
            raw_message="test",
            font=0,
            sender=sender
        )
        
        # 测试权限等级
        level = self.permission_manager.get_user_permission_level(event)
        assert level == PermissionLevel.MEMBER
        
        # 测试权限检查
        assert not self.permission_manager.check_superuser_permission(event)
        assert not self.permission_manager.check_admin_permission(event)
        assert self.permission_manager.check_member_permission(event)

class TestFilterManager:
    """过滤管理器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.config_manager = Mock()
        self.permission_manager = Mock()
        self.logger = Mock()
        self.filter_manager = FilterManager(
            self.config_manager, self.permission_manager, self.logger
        )
    
    @pytest.mark.asyncio
    async def test_blacklist_filter(self):
        """测试黑名单过滤"""
        # 模拟黑名单检查
        self.config_manager.is_in_blacklist.return_value = True
        self.permission_manager.bypass_whitelist_check.return_value = False
        
        # 创建测试事件
        event = PrivateMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="private",
            sub_type="friend",
            message_id=1,
            user_id=999999,
            message=[],
            raw_message="test message",
            font=0,
            sender=Sender(user_id=999999, nickname="blocked")
        )
        
        message_data = {"raw_message": "test message"}
        
        # 测试过滤
        filtered, reason, modified_data = await self.filter_manager.filter_receive_message(
            event, message_data
        )
        
        assert not filtered
        assert "黑名单" in reason
    
    @pytest.mark.asyncio
    async def test_global_receive_filter(self):
        """测试全局接收过滤"""
        # 模拟配置
        self.config_manager.is_in_blacklist.return_value = False
        self.permission_manager.bypass_whitelist_check.return_value = False
        self.config_manager.get_global_config.return_value = {
            "global_filters": {
                "receive_filters": ["敏感词", "违禁内容"]
            }
        }
        
        # 创建测试事件
        event = PrivateMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="private",
            sub_type="friend",
            message_id=1,
            user_id=888888,
            message=[],
            raw_message="这是敏感词测试",
            font=0,
            sender=Sender(user_id=888888, nickname="test")
        )
        
        message_data = {"raw_message": "这是敏感词测试"}
        
        # 测试过滤
        filtered, reason, modified_data = await self.filter_manager.filter_receive_message(
            event, message_data
        )
        
        assert not filtered
        assert "敏感词" in reason
    
    @pytest.mark.asyncio
    async def test_prefix_protection(self):
        """测试前缀保护"""
        # 模拟配置
        self.config_manager.get_global_config.return_value = {
            "global_filters": {
                "send_filters": [],
                "prefix_protections": ["#", "!"]
            }
        }
        
        # 创建测试事件
        event = PrivateMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="private",
            sub_type="friend",
            message_id=1,
            user_id=888888,
            message=[],
            raw_message="#help",
            font=0,
            sender=Sender(user_id=888888, nickname="test")
        )
        
        message_data = {"raw_message": "#help"}
        
        # 测试过滤
        filtered, reason, modified_data = await self.filter_manager.filter_send_message(
            event, message_data
        )
        
        assert filtered
        assert "前缀保护" in reason
        assert "[禁止诱导触发]" in modified_data["raw_message"]

class TestSecurityManager:
    """安全管理器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.config_manager = Mock()
        self.database_manager = Mock()
        self.logger = Mock()
        self.security_manager = SecurityManager(
            self.config_manager, self.database_manager, self.logger
        )
    
    @pytest.mark.asyncio
    async def test_message_security_check(self):
        """测试消息安全检查"""
        # 模拟配置
        self.config_manager.get_account_config.return_value = {"enabled": True}
        self.config_manager.get_global_config.return_value = {
            "rate_limit": {"enabled": False},
            "global_filters": {"receive_filters": []}
        }
        self.config_manager.is_in_blacklist.return_value = False
        
        # 创建测试事件
        event = PrivateMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="private",
            sub_type="friend",
            message_id=1,
            user_id=888888,
            message=[],
            raw_message="正常消息",
            font=0,
            sender=Sender(user_id=888888, nickname="test")
        )
        
        message_data = {"raw_message": "正常消息"}
        
        # 测试安全检查
        passed, reason, modified_data = await self.security_manager.check_message_security(
            event, message_data, "receive"
        )
        
        assert passed
        assert "通过" in reason
    
    @pytest.mark.asyncio
    async def test_command_permission_check(self):
        """测试指令权限检查"""
        # 模拟配置
        self.config_manager.get_account_config.return_value = {"enabled": True}
        self.config_manager.is_superuser.return_value = True
        
        # 创建测试事件
        event = PrivateMessageEvent(
            time=int(datetime.now().timestamp()),
            self_id=123456,
            message_type="private",
            sub_type="friend",
            message_id=1,
            user_id=888888,
            message=[],
            raw_message="bs帮助",
            font=0,
            sender=Sender(user_id=888888, nickname="test")
        )
        
        # 测试指令权限
        allowed, reason = await self.security_manager.check_command_permission(
            event, "帮助"
        )
        
        assert allowed
        assert "通过" in reason

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
