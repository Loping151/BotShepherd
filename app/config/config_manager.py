"""
配置管理器
负责管理所有配置文件的读写和验证
"""

import json
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .config_validator import ConfigValidator, ConfigTemplate
# from .config_watcher import ConfigWatcher

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_dir = Path("config")
        self.connections_dir = self.config_dir / "connections"
        self.account_dir = self.config_dir / "account"
        self.group_dir = self.config_dir / "group"
        
        # 配置缓存
        self._global_config = None
        self._connections_config = {}
        self._account_configs = {}
        self._group_configs = {}
        
        # 配置文件监控
        self._config_watcher = None
        # self._config_backup = None

        # 配置验证器
        self._validator = ConfigValidator()
        
    async def initialize(self):
        """初始化配置管理器"""
        # 创建配置目录
        self._ensure_directories()
        
        # 加载所有配置
        await self._load_all_configs()
        
        # 初始化配置备份管理器
        # self._config_backup = ConfigBackup(self.config_dir)

        # 启动配置文件监控
        # await self._start_config_watchers()
    
    def _ensure_directories(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(exist_ok=True)
        self.connections_dir.mkdir(exist_ok=True)
        self.account_dir.mkdir(exist_ok=True)
        self.group_dir.mkdir(exist_ok=True)
    
    async def _load_all_configs(self):
        """加载所有配置文件"""
        # 加载全局配置
        await self._load_global_config()
        
        # 加载连接配置
        await self._load_connections_config()
        
        # 加载账号配置
        await self._load_account_configs()
        
        # 加载群组配置
        await self._load_group_configs()
    
    async def _load_global_config(self):
        """加载全局配置"""
        global_config_file = self.config_dir / "global_config.json"
        
        if global_config_file.exists():
            try:
                with open(global_config_file, 'r', encoding='utf-8') as f:
                    self._global_config = json.load(f)
            except Exception as e:
                print(f"加载全局配置失败: {e}")
                self._global_config = ConfigTemplate.get_default_global_config()
        else:
            self._global_config = ConfigTemplate.get_default_global_config()
            await self._save_global_config()
    
    async def _load_connections_config(self):
        """加载连接配置"""
        self._connections_config = {}
        
        if not self.connections_dir.exists():
            return
        
        for config_file in self.connections_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    connection_id = config_file.stem
                    self._connections_config[connection_id] = config
            except Exception as e:
                print(f"加载连接配置失败 {config_file}: {e}")
    
    async def _load_account_configs(self):
        """加载账号配置"""
        self._account_configs = {}
        
        if not self.account_dir.exists():
            return
        
        for config_file in self.account_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    account_id = config_file.stem
                    self._account_configs[account_id] = config
            except Exception as e:
                print(f"加载账号配置失败 {config_file}: {e}")
    
    async def _load_group_configs(self):
        """加载群组配置"""
        self._group_configs = {}
        
        if not self.group_dir.exists():
            return
        
        for config_file in self.group_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    group_id = config_file.stem
                    self._group_configs[group_id] = config
            except Exception as e:
                print(f"加载群组配置失败 {config_file}: {e}")
    
    # async def _start_config_watchers(self):
    #     """启动配置文件监控"""
    #     self._config_watcher = ConfigWatcher(self)
    #     await self._config_watcher.start()

    # async def stop_config_watchers(self):
    #     """停止配置文件监控"""
    #     if self._config_watcher:
    #         await self._config_watcher.stop()
    #         self._config_watcher = None
            
    def config_exists(self) -> bool:
        """检查配置文件是否存在"""
        global_config_file = self.config_dir / "global_config.json"
        return global_config_file.exists()
    
    # 全局配置相关方法
    def get_global_config(self) -> Dict[str, Any]:
        """获取全局配置"""
        return self._global_config.copy()
    
    def get_superuser(self) -> List:
        """获取超级用户列表"""
        return self._global_config.get("superusers", [])
    
    async def update_global_config(self, updates: Dict[str, Any]):
        """更新全局配置"""
        # 创建临时配置进行验证
        temp_config = self._global_config.copy()
        temp_config.update(updates)

        # 验证配置
        is_valid, errors = self._validator.validate_global_config(temp_config)
        if not is_valid:
            raise ValueError(f"全局配置验证失败: {', '.join(errors)}")

        self._global_config.update(updates)
        await self._save_global_config()
    
    async def _save_global_config(self):
        """保存全局配置"""
        global_config_file = self.config_dir / "global_config.json"
        try:
            with open(global_config_file, 'w', encoding='utf-8') as f:
                json.dump(self._global_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存全局配置失败: {e}")
    
    # 连接配置相关方法
    def get_connections_config(self) -> Dict[str, Dict[str, Any]]:
        """获取所有连接配置"""
        return self._connections_config.copy()
    
    def get_connection_config(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取指定连接配置"""
        return self._connections_config.get(connection_id)
    
    async def save_connection_config(self, connection_id: str, config: Dict[str, Any]):
        """保存连接配置"""
        # 验证配置
        is_valid, errors = self._validator.validate_connection_config(config)
        if not is_valid:
            raise ValueError(f"连接配置验证失败: {', '.join(errors)}")

        self._connections_config[connection_id] = config

        config_file = self.connections_dir / f"{connection_id}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存连接配置失败 {connection_id}: {e}")
            raise
    
    async def delete_connection_config(self, connection_id: str):
        """删除连接配置"""
        if connection_id in self._connections_config:
            del self._connections_config[connection_id]
        
        config_file = self.connections_dir / f"{connection_id}.json"
        if config_file.exists():
            config_file.unlink()
    
    # 账号配置相关方法
    def get_all_account_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有账号配置"""
        return self._account_configs.copy()
    
    def get_account_config(self, account_id: str) -> Optional[Dict[str, Any]]:
        """获取账号配置"""
        return self._account_configs.get(account_id)
    
    async def save_account_config(self, account_id: str, config: Dict[str, Any]):
        """保存账号配置"""
        self._account_configs[account_id] = config
        
        config_file = self.account_dir / f"{account_id}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存账号配置失败 {account_id}: {e}")
    
    async def update_account_last_activity(self, account_id: str, activity_type: str):
        """更新账号最后活动时间"""
        config = self.get_account_config(account_id)
        if not config:
            # 创建新的账号配置
            config = ConfigTemplate.get_default_account_config(account_id)
        
        # 更新时间
        current_time = datetime.now().isoformat()
        if activity_type == "receive":
            config["last_receive_time"] = current_time
        elif activity_type == "send":
            config["last_send_time"] = current_time
        
        await self.save_account_config(account_id, config)
        
    async def get_recently_active_accounts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近活跃的账号"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        active_accounts = []
        for account_id, config in self._account_configs.items():
            last_receive_time = config.get("last_receive_time", "1970-01-01T00:00:00")
            last_send_time = config.get("last_send_time", "1970-01-01T00:00:00")
            if not last_receive_time or not last_send_time:
                continue
            
            if datetime.fromisoformat(last_send_time) >= cutoff_time:
                active_accounts.append({
                    "account_id": account_id,
                    "last_receive_time": last_receive_time,
                    "last_send_time": last_send_time
                })
        
        return active_accounts
    
    # 群组配置相关方法
    def get_all_group_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有群组配置"""
        return self._group_configs.copy()
    
    def get_group_config(self, group_id: str) -> Optional[Dict[str, Any]]:
        """获取群组配置"""
        return self._group_configs.get(group_id)
    
    async def save_group_config(self, group_id: str, config: Dict[str, Any]):
        """保存群组配置"""
        # 验证配置
        is_valid, errors = self._validator.validate_group_config(config)
        if not is_valid:
            raise ValueError(f"群组配置验证失败: {', '.join(errors)}")

        self._group_configs[group_id] = config

        config_file = self.group_dir / f"{group_id}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存群组配置失败 {group_id}: {e}")
            raise

    async def delete_group_config(self, group_id: str):
        """删除群组配置"""
        if group_id in self._group_configs:
            del self._group_configs[group_id]

        config_file = self.group_dir / f"{group_id}.json"
        if config_file.exists():
            config_file.unlink()

    # 群组配置相关方法
    def get_all_group_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有群组配置"""
        return self._group_configs.copy()

    async def update_group_last_message_time(self, group_id: str):
        """更新群组最后消息时间"""
        config = self.get_group_config(group_id)
        if not config:
            # 创建新的群组配置
            config = ConfigTemplate.get_default_group_config(group_id)

        # 更新最后消息时间
        config["last_message_time"] = datetime.now().isoformat()
        await self.save_group_config(group_id, config)
        
        
    async def get_recently_active_groups(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取最近活跃的群组"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        active_groups = []
        for group_id, config in self._group_configs.items():
            last_message_time = config.get("last_message_time", "1970-01-01T00:00:00")
            if not last_message_time:
                continue
            if datetime.fromisoformat(last_message_time) >= cutoff_time:
                active_groups.append({
                    "group_id": group_id,
                    "last_message_time": last_message_time
                })
        
        return active_groups

    async def set_group_expire_time(self, group_id: str, expire_days: int):
        """设置群组到期时间"""
        from ..utils.logger import get_operation_logger

        config = self.get_group_config(group_id)
        if not config:
            config = {
                "group_id": group_id,
                "description": f"群组_{group_id}",
                "enabled": True,
                "expire_time": -1,
                "last_message_time": None,
                "filters": {
                    "superuser_filters": [],
                    "admin_filters": []
                }
            }

        old_expire_time = config.get("expire_time", -1)

        if expire_days == -1:
            new_expire_time = -1
        else:
            expire_date = datetime.now() + timedelta(days=expire_days)
            new_expire_time = expire_date.isoformat()

        config["expire_time"] = new_expire_time
        await self.save_group_config(group_id, config)

        # 记录操作日志
        operation_logger = get_operation_logger()
        operation_logger.info(f"群组到期时间修改 - 群号: {group_id}, 原到期时间: {old_expire_time}, 新到期时间: {new_expire_time}")

    def is_group_expired(self, group_id: str) -> bool:
        """检查群组是否已过期"""
        config = self.get_group_config(group_id)
        if not config:
            return False

        expire_time = config.get("expire_time", -1)
        if expire_time == -1:
            return False

        try:
            expire_date = datetime.fromisoformat(expire_time)
            return datetime.now() > expire_date
        except (ValueError, TypeError):
            return False

    # 黑名单管理
    async def add_to_blacklist(self, item_type: str, item_id: str):
        """添加到黑名单"""
        from ..utils.logger import get_operation_logger

        if item_type not in ["groups", "users"]:
            raise ValueError("item_type must be 'groups' or 'users'")

        blacklist = self._global_config.get("blacklist", {})
        if item_type not in blacklist:
            blacklist[item_type] = []

        if item_id not in blacklist[item_type]:
            blacklist[item_type].append(item_id)
            self._global_config["blacklist"] = blacklist
            await self._save_global_config()

            # 记录操作日志
            operation_logger = get_operation_logger()
            operation_logger.info(f"黑名单添加 - 类型: {item_type}, ID: {item_id}")

    async def remove_from_blacklist(self, item_type: str, item_id: str):
        """从黑名单移除"""
        from ..utils.logger import get_operation_logger

        if item_type not in ["groups", "users"]:
            raise ValueError("item_type must be 'groups' or 'users'")

        blacklist = self._global_config.get("blacklist", {})
        if item_type in blacklist and item_id in blacklist[item_type]:
            blacklist[item_type].remove(item_id)
            self._global_config["blacklist"] = blacklist
            await self._save_global_config()

            # 记录操作日志
            operation_logger = get_operation_logger()
            operation_logger.info(f"黑名单移除 - 类型: {item_type}, ID: {item_id}")

    def is_in_blacklist(self, item_type: str, item_id: str) -> bool:
        """检查是否在黑名单中"""
        if item_type not in ["groups", "users"]:
            return False

        blacklist = self._global_config.get("blacklist", {})
        return item_id in blacklist.get(item_type, [])

    # 超级用户管理
    async def add_superuser(self, user_id: str):
        """添加超级用户"""
        superusers = self.get_superuser()
        if user_id not in superusers:
            superusers.append(user_id)
            self._global_config["superusers"] = superusers
            await self._save_global_config()

    async def remove_superuser(self, user_id: str):
        """移除超级用户"""
        superusers = self.get_superuser()
        if user_id in superusers and len(superusers) > 1:  # 保证至少有一个超级用户
            superusers.remove(user_id)
            self._global_config["superusers"] = superusers
            await self._save_global_config()
            return True
        return False

    def is_superuser(self, user_id: str) -> bool:
        """检查是否为超级用户"""
        assert isinstance(user_id, (str, int))
        if isinstance(user_id, int):
            user_id = str(user_id)
        superusers = self.get_superuser()
        return user_id in superusers
    
    # 别名管理
    async def add_global_alias(self, alias: str, target: str):
        """添加全局别名"""
        aliases = self._global_config.get("global_aliases", {})
        if alias not in aliases:
            aliases[alias] = []
        if target not in aliases[alias]:
            aliases[alias].append(target)
            self._global_config["global_aliases"] = aliases
            await self._save_global_config()
            
    ### 正在写别名！！！！！！！！

    # 过滤词管理
    async def add_global_filter(self, filter_type: str, word: str):
        """添加全局过滤词"""
        if filter_type not in ["receive_filters", "send_filters", "prefix_protections"]:
            raise ValueError("Invalid filter_type")

        filters = self._global_config.get("global_filters", {})
        if filter_type not in filters:
            filters[filter_type] = []

        if word not in filters[filter_type]:
            filters[filter_type].append(word)
            self._global_config["global_filters"] = filters
            await self._save_global_config()

    async def remove_global_filter(self, filter_type: str, word: str):
        """移除全局过滤词"""
        if filter_type not in ["receive_filters", "send_filters", "prefix_protections"]:
            raise ValueError("Invalid filter_type")

        filters = self._global_config.get("global_filters", {})
        if filter_type in filters and word in filters[filter_type]:
            filters[filter_type].remove(word)
            self._global_config["global_filters"] = filters
            await self._save_global_config()
            
    async def list_global_filters(self) -> Dict[str, List[str]]:
        """列出全局过滤词"""
        filters = self._global_config.get("global_filters", {})
        return filters

    async def add_group_filter(self, group_id: str, filter_level: str, word: str):
        """添加群组过滤词"""
        if filter_level not in ["superuser_filters", "admin_filters"]:
            raise ValueError("filter_level must be 'superuser_filters' or 'admin_filters'")

        config = self.get_group_config(group_id)
        if not config:
            config = ConfigTemplate.get_default_group_config()

        filters = config.get("filters", {})
        if filter_level not in filters:
            filters[filter_level] = []

        if word not in filters[filter_level]:
            filters[filter_level].append(word)
            config["filters"] = filters
            await self.save_group_config(group_id, config)

    async def remove_group_filter(self, group_id: str, filter_level: str, word: str):
        """移除群组过滤词"""
        if filter_level not in ["superuser_filters", "admin_filters"]:
            raise ValueError("filter_level must be 'superuser_filters' or 'admin_filters'")

        config = self.get_group_config(group_id)
        if not config:
            return

        filters = config.get("filters", {})
        if filter_level in filters and word in filters[filter_level]:
            filters[filter_level].remove(word)
            config["filters"] = filters
            await self.save_group_config(group_id, config)
            
    async def list_group_filters(self, group_id: str) -> Dict[str, List[str]]:
        """列出群组过滤词"""
        config = self.get_group_config(group_id)
        if not config:
            return {}

        filters = config.get("filters", {})
        return filters

    # 配置验证
    def validate_connection_config(self, config: Dict[str, Any]) -> bool:
        """验证连接配置"""
        required_fields = ["name", "description", "client_endpoint", "target_endpoints", "enabled"]

        for field in required_fields:
            if field not in config:
                return False

        # 验证端点格式
        if not config["client_endpoint"].startswith("ws://"):
            return False

        if not isinstance(config["target_endpoints"], list) or len(config["target_endpoints"]) == 0:
            return False

        for endpoint in config["target_endpoints"]:
            if not endpoint.startswith("ws://"):
                return False

        return True

    # def validate_global_config(self, config: Dict[str, Any]) -> bool:
    #     """验证全局配置"""
    #     required_fields = ["superusers", "command_prefix"]

    #     for field in required_fields:
    #         if field not in config:
    #             return False

    #     # 验证超级用户列表
    #     if not isinstance(config["superusers"], list) or len(config["superusers"]) == 0:
    #         return False

    #     # 验证指令前缀
    #     if not isinstance(config["command_prefix"], str) or len(config["command_prefix"]) == 0:
    #         return False

    #     return True

    # 配置备份和恢复
    # async def create_config_backup(self, backup_name: Optional[str] = None) -> str:
    #     """创建配置备份"""
    #     if not self._config_backup:
    #         raise RuntimeError("配置备份管理器未初始化")

    #     backup_path = await self._config_backup.create_backup(backup_name)
    #     return str(backup_path)

    # async def restore_config_backup(self, backup_name: str):
    #     """恢复配置备份"""
    #     if not self._config_backup:
    #         raise RuntimeError("配置备份管理器未初始化")

    #     await self._config_backup.restore_backup(backup_name)
    #     # 重新加载所有配置
    #     await self._load_all_configs()

    # def list_config_backups(self) -> List[Dict[str, Any]]:
    #     """列出所有配置备份"""
    #     if not self._config_backup:
    #         return []

    #     return self._config_backup.list_backups()

    # async def cleanup_old_backups(self, keep_count: int = 10):
    #     """清理旧备份"""
    #     if self._config_backup:
    #         await self._config_backup.cleanup_old_backups(keep_count)

    async def setup_initial_config(self):
        """设置初始配置"""
        print("创建默认配置文件...")

        # 确保目录存在
        self._ensure_directories()

        # 创建默认全局配置
        self._global_config = self._get_default_global_config()
        await self._save_global_config()

        # 创建示例连接配置
        example_connection = ConfigTemplate.get_default_connection_config()
        await self.save_connection_config("default", example_connection)

        print("配置文件创建完成！")
        print("请编辑以下配置文件：")
        print(f"- 全局配置: {self.config_dir}/global_config.json")
        print(f"- 连接配置: {self.connections_dir}/default.json")
