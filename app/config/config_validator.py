"""
配置验证器
验证各种配置文件的格式和内容
"""

import re
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse

class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_global_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证全局配置"""
        errors = []
        
        # 验证必需字段
        required_fields = {
            "superusers": list,
            "command_prefix": str,
            "trigger_prefix": str,
            "command_ignore_at_other": str,
            "global_aliases": dict,
            "blacklist": dict,
            "allow_private": bool,
            "private_friend_only": bool,
            "global_filters": dict,
            "database": dict,
            "logging": dict,
            "message_normalization": dict,
            "sendcount_notifications": bool,
            "web_auth": dict
        }
        
        for field, expected_type in required_fields.items():
            if field not in config:
                errors.append(f"缺少必需字段: {field}")
            elif not isinstance(config[field], expected_type):
                errors.append(f"字段 {field} 类型错误，期望 {expected_type.__name__}")
        
        # 验证超级用户
        if "superusers" in config:
            superusers = config["superusers"]
            if not isinstance(superusers, list) or len(superusers) == 0:
                errors.append("superusers 必须是非空列表")
            else:
                for i, user_id in enumerate(superusers):
                    if not isinstance(user_id, str) or not user_id.isdigit():
                        errors.append(f"superusers[{i}] 必须是数字字符串")
        
        # 验证指令前缀
        if "command_prefix" in config:
            prefix = config["command_prefix"]
            if not isinstance(prefix, str) or len(prefix) == 0:
                errors.append("command_prefix 不能为空")
            elif len(prefix) > 10:
                errors.append("command_prefix 长度不能超过10个字符")
        
        # 验证全局别名
        if "global_aliases" in config:
            aliases = config["global_aliases"]
            if isinstance(aliases, dict):
                for key, value in aliases.items():
                    if not isinstance(key, str):
                        errors.append(f"global_aliases 键必须是字符串: {key}")
                    if not isinstance(value, list):
                        errors.append(f"global_aliases[{key}] 值必须是列表")
                    else:
                        for alias in value:
                            if not isinstance(alias, str):
                                errors.append(f"global_aliases[{key}] 中的别名必须是字符串: {alias}")
        
        # 验证黑名单
        if "blacklist" in config:
            blacklist = config["blacklist"]
            if isinstance(blacklist, dict):
                for list_type in ["groups", "users"]:
                    if list_type in blacklist:
                        if not isinstance(blacklist[list_type], list):
                            errors.append(f"blacklist.{list_type} 必须是列表")
                        else:
                            for item in blacklist[list_type]:
                                if not isinstance(item, str) or not item.isdigit():
                                    errors.append(f"blacklist.{list_type} 中的项目必须是数字字符串: {item}")
        
        # 验证全局过滤器
        if "global_filters" in config:
            filters = config["global_filters"]
            if isinstance(filters, dict):
                filter_types = ["receive_filters", "send_filters", "prefix_protections"]
                for filter_type in filter_types:
                    if filter_type in filters:
                        if not isinstance(filters[filter_type], list):
                            errors.append(f"global_filters.{filter_type} 必须是列表")
                        else:
                            for word in filters[filter_type]:
                                if not isinstance(word, str):
                                    errors.append(f"global_filters.{filter_type} 中的过滤词必须是字符串: {word}")
        
        # 验证数据库配置
        if "database" in config:
            db_config = config["database"]
            if isinstance(db_config, dict):
                if "type" in db_config and db_config["type"] not in ["sqlite"]:
                    errors.append(f"不支持的数据库类型: {db_config['type']}")
                
                if "auto_expire_days" in db_config:
                    expire_days = db_config["auto_expire_days"]
                    if not isinstance(expire_days, int) or expire_days < 3:
                        errors.append("auto_expire_days 必须是大于等于3的整数")
        
        # 验证Web认证配置
        if "web_auth" in config:
            web_auth = config["web_auth"]
            if isinstance(web_auth, dict):
                for field in ["username", "password"]:
                    if field in web_auth:
                        if not isinstance(web_auth[field], str) or len(web_auth[field]) == 0:
                            errors.append(f"web_auth.{field} 不能为空")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_connection_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证连接配置"""
        errors = []
        
        # 验证必需字段
        required_fields = {
            "name": str,
            "description": str,
            "client_endpoint": str,
            "target_endpoints": list,
            "enabled": bool
        }
        
        for field, expected_type in required_fields.items():
            if field not in config:
                errors.append(f"缺少必需字段: {field}")
            elif not isinstance(config[field], expected_type):
                errors.append(f"字段 {field} 类型错误，期望 {expected_type.__name__}")
        
        # 验证名称和描述
        if "name" in config:
            name = config["name"]
            if not isinstance(name, str) or len(name.strip()) == 0:
                errors.append("name 不能为空")
            elif len(name) > 50:
                errors.append("name 长度不能超过50个字符")
        
        # 验证客户端端点
        if "client_endpoint" in config:
            endpoint = config["client_endpoint"]
            if not ConfigValidator._validate_websocket_url(endpoint):
                errors.append(f"client_endpoint 格式无效: {endpoint}")
        
        # 验证目标端点
        if "target_endpoints" in config:
            endpoints = config["target_endpoints"]
            if isinstance(endpoints, list):
                if len(endpoints) == 0:
                    errors.append("target_endpoints 不能为空")
                else:
                    for i, endpoint in enumerate(endpoints):
                        if not isinstance(endpoint, str):
                            errors.append(f"target_endpoints[{i}] 必须是字符串")
                        elif not ConfigValidator._validate_websocket_url(endpoint):
                            errors.append(f"target_endpoints[{i}] 格式无效: {endpoint}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_account_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证账号配置"""
        errors = []
        
        # 验证必需字段
        required_fields = {
            "account_id": str,
            "name": str,
            "description": str,
            "enabled": bool,
            "aliases": dict
        }
        
        for field, expected_type in required_fields.items():
            if field not in config:
                errors.append(f"缺少必需字段: {field}")
            elif not isinstance(config[field], expected_type):
                errors.append(f"字段 {field} 类型错误，期望 {expected_type.__name__}")
        
        # 验证账号ID
        if "account_id" in config:
            account_id = config["account_id"]
            if not isinstance(account_id, str) or not account_id.isdigit():
                errors.append("account_id 必须是数字字符串")
                
        if "aliases" in config:
            aliases = config["aliases"]
            if not isinstance(aliases, dict):
                errors.append("aliases 必须是字典")
            else:
                for key, value in aliases.items():
                    if not isinstance(key, str):
                        errors.append(f"aliases 键必须是字符串: {key}")
                    if not isinstance(value, list):
                        errors.append(f"aliases[{key}] 值必须是列表")
                    else:
                        for alias in value:
                            if not isinstance(alias, str):
                                errors.append(f"aliases[{key}] 中的别名必须是字符串: {alias}")
        
        # 验证时间字段
        time_fields = ["last_receive_time", "last_send_time"]
        for field in time_fields:
            if field in config and config[field] is not None:
                if not isinstance(config[field], str):
                    errors.append(f"{field} 必须是ISO格式的时间字符串")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_group_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """验证群组配置"""
        errors = []
        
        # 验证必需字段
        required_fields = {
            "group_id": str,
            "description": str,
            "enabled": bool,
            "expire_time": (str, int),
            "aliases": dict,
            "filters": dict
        }
        
        for field, expected_type in required_fields.items():
            if field not in config:
                errors.append(f"缺少必需字段: {field}")
            elif isinstance(expected_type, tuple):
                if not any(isinstance(config[field], t) for t in expected_type):
                    type_names = " 或 ".join(t.__name__ for t in expected_type)
                    errors.append(f"字段 {field} 类型错误，期望 {type_names}")
            elif not isinstance(config[field], expected_type):
                errors.append(f"字段 {field} 类型错误，期望 {expected_type.__name__}")
        
        # 验证群组ID
        if "group_id" in config:
            group_id = config["group_id"]
            if not isinstance(group_id, str) or not group_id.isdigit():
                errors.append("group_id 必须是数字字符串")
        
        # 验证过期时间
        if "expire_time" in config:
            expire_time = config["expire_time"]
            if expire_time != -1 and not isinstance(expire_time, str):
                errors.append("expire_time 必须是 -1 或 ISO格式的时间字符串")
                
        if "aliases" in config:
            aliases = config["aliases"]
            if not isinstance(aliases, dict):
                errors.append("aliases 必须是字典")
            else:
                for key, value in aliases.items():
                    if not isinstance(key, str):
                        errors.append(f"aliases 键必须是字符串: {key}")
                    if not isinstance(value, list):
                        errors.append(f"aliases[{key}] 值必须是列表")
                    else:
                        for alias in value:
                            if not isinstance(alias, str):
                                errors.append(f"aliases[{key}] 中的别名必须是字符串: {alias}")
                                
        if "last_message_time" in config and config["last_message_time"] is not None:
            if not isinstance(config["last_message_time"], str):
                errors.append("last_message_time 必须是ISO格式的时间字符串")
        
        # 验证过滤器
        if "filters" in config:
            filters = config["filters"]
            if isinstance(filters, dict):
                filter_levels = ["superuser_filters", "admin_filters"]
                for level in filter_levels:
                    if level in filters:
                        if not isinstance(filters[level], list):
                            errors.append(f"filters.{level} 必须是列表")
                        else:
                            for word in filters[level]:
                                if not isinstance(word, str):
                                    errors.append(f"filters.{level} 中的过滤词必须是字符串: {word}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _validate_websocket_url(url: str) -> bool:
        """验证WebSocket URL格式"""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ["ws", "wss"] and parsed.netloc
        except Exception:
            return False
    
    @staticmethod
    def _validate_qq_number(qq: str) -> bool:
        """验证QQ号格式"""
        return isinstance(qq, str) and qq.isdigit() and len(qq) >= 5 and len(qq) <= 12

class ConfigTemplate:
    """配置模板"""
    
    @staticmethod
    def get_default_global_config() -> Dict[str, Any]:
        """获取默认全局配置模板"""
        return {
            "superusers": ["644572093"], # 不是后门奥，自己改
            "command_prefix": "bs",
            "trigger_prefix": "bs触发",
            "command_ignore_at_other": True,
            "global_aliases": {
                "ww": ["ww"]
            },
            "blacklist": {
                "groups": [],
                "users": []
            },
            "allow_private": True,
            "private_friend_only": True,
            "global_filters": {
                "receive_filters": [],
                "send_filters": [],
                "prefix_protections": []
            },
            "database": {
                "data_path": "./data",
                "auto_expire_days": 30
            },
            "logging": {
                "level": "INFO",
                "file_rotation": True,
                "keep_days": 7
            },
            "message_normalization": {
                "enabled": False,
                "normalize_napcat_sent": True
            },
            "sendcount_notifications": True,
            "web_auth": {
                "username": "admin",
                "password": "admin"
            }
        }
    
    @staticmethod
    def get_default_connection_config() -> Dict[str, Any]:
        """获取默认连接配置模板"""
        return {
            "name": "新连接",
            "description": "连接描述",
            "client_endpoint": "ws://localhost:2537/OneBotv11",
            "target_endpoints": [
                "ws://localhost:2536/OneBotv11"
            ],
            "enabled": True
        }
    
    @staticmethod
    def get_default_account_config(account_id: str) -> Dict[str, Any]:
        """获取默认账号配置模板"""
        return {
            "account_id": account_id,
            "name": f"Bot_{account_id}",
            "description": "自动创建的账号配置",
            "enabled": True,
            "aliases": {},
            "send_count": {"date": None, "group": {"total": 0}, "private": 0},
            "last_receive_time": None,
            "last_send_time": None
        }
    
    @staticmethod
    def get_default_group_config(group_id: str) -> Dict[str, Any]:
        """获取默认群组配置模板"""
        return {
            "group_id": group_id,
            "description": f"群组_{group_id}",
            "enabled": True,
            "expire_time": -1,
            "aliases": {},
            "last_message_time": None,
            "filters": {
                "superuser_filters": [],
                "admin_filters": []
            }
        }
