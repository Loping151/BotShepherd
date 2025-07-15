"""
每个QQ号的独立配置管理
"""

import json
import os
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class GroupConfig:
    """群组配置"""
    group_id: int
    enabled: bool = True
    expire_time: Optional[str] = None  # ISO格式时间字符串，-1表示永久
    blacklisted: bool = False
    custom_prefixes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GroupConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expire_time is None or self.expire_time == "-1":
            return False
        try:
            expire_dt = datetime.fromisoformat(self.expire_time)
            return datetime.now() > expire_dt
        except:
            return False
    
    def is_active(self) -> bool:
        """检查是否激活（未过期且未被拉黑且已启用）"""
        return self.enabled and not self.blacklisted and not self.is_expired()


@dataclass
class FilterConfig:
    """过滤配置"""
    # 上行违禁词（接收到的消息过滤）
    upstream_forbidden_words: List[str] = field(default_factory=list)
    # 下行违禁词（发送消息过滤）
    downstream_forbidden_words: List[str] = field(default_factory=list)
    # 防误触前缀词
    anti_trigger_prefixes: List[str] = field(default_factory=lambda: ["指令", "命令", "help"])
    # 是否启用过滤
    enable_upstream_filter: bool = True
    enable_downstream_filter: bool = True
    enable_anti_trigger: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CommandConfig:
    """指令配置"""
    # 指令别名：原指令 -> 别名列表
    command_aliases: Dict[str, List[str]] = field(default_factory=dict)
    # 自定义指令前缀
    custom_prefixes: List[str] = field(default_factory=list)
    # 是否启用指令别名
    enable_aliases: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_command_for_alias(self, alias: str) -> Optional[str]:
        """根据别名获取原指令"""
        for command, aliases in self.command_aliases.items():
            if alias in aliases:
                return command
        return None


@dataclass
class StatisticsConfig:
    """统计配置"""
    # 是否启用消息统计
    enable_message_stats: bool = True
    # 是否启用关键词统计
    enable_keyword_stats: bool = True
    # 关键词监控列表（startswith匹配）
    monitored_keywords: List[str] = field(default_factory=list)
    # 统计数据保留天数
    stats_retention_days: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatisticsConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class BotConfig:
    """单个QQ号的配置"""
    self_id: int
    nickname: str = ""
    # 总开关
    enabled: bool = True
    # 群组配置
    groups: Dict[int, GroupConfig] = field(default_factory=dict)
    # 过滤配置
    filter_config: FilterConfig = field(default_factory=FilterConfig)
    # 指令配置
    command_config: CommandConfig = field(default_factory=CommandConfig)
    # 统计配置
    statistics_config: StatisticsConfig = field(default_factory=StatisticsConfig)
    # 黑名单用户
    blacklisted_users: Set[int] = field(default_factory=set)
    # 白名单用户（优先级高于黑名单）
    whitelisted_users: Set[int] = field(default_factory=set)
    # 配置创建和更新时间
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "self_id": self.self_id,
            "nickname": self.nickname,
            "enabled": self.enabled,
            "groups": {str(k): v.to_dict() for k, v in self.groups.items()},
            "filter_config": self.filter_config.to_dict(),
            "command_config": self.command_config.to_dict(),
            "statistics_config": self.statistics_config.to_dict(),
            "blacklisted_users": list(self.blacklisted_users),
            "whitelisted_users": list(self.whitelisted_users),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotConfig':
        # 处理groups字典
        groups_data = data.get("groups", {})
        groups = {}
        for group_id_str, group_data in groups_data.items():
            group_id = int(group_id_str)
            groups[group_id] = GroupConfig.from_dict(group_data)
        
        # 处理子配置
        filter_config = FilterConfig.from_dict(data.get("filter_config", {}))
        command_config = CommandConfig.from_dict(data.get("command_config", {}))
        statistics_config = StatisticsConfig.from_dict(data.get("statistics_config", {}))
        
        return cls(
            self_id=data.get("self_id", 0),
            nickname=data.get("nickname", ""),
            enabled=data.get("enabled", True),
            groups=groups,
            filter_config=filter_config,
            command_config=command_config,
            statistics_config=statistics_config,
            blacklisted_users=set(data.get("blacklisted_users", [])),
            whitelisted_users=set(data.get("whitelisted_users", [])),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )
    
    def is_user_allowed(self, user_id: int) -> bool:
        """检查用户是否被允许"""
        if user_id in self.whitelisted_users:
            return True
        if user_id in self.blacklisted_users:
            return False
        return True
    
    def is_group_active(self, group_id: int) -> bool:
        """检查群组是否激活"""
        if not self.enabled:
            return False
        
        group_config = self.groups.get(group_id)
        if group_config is None:
            return True  # 默认允许
        
        return group_config.is_active()
    
    def add_group(self, group_id: int, enabled: bool = True, expire_days: Optional[int] = None) -> None:
        """添加群组配置"""
        expire_time = None
        if expire_days is not None and expire_days > 0:
            expire_time = (datetime.now() + timedelta(days=expire_days)).isoformat()
        elif expire_days == -1:
            expire_time = "-1"
        
        self.groups[group_id] = GroupConfig(
            group_id=group_id,
            enabled=enabled,
            expire_time=expire_time
        )
        self.updated_at = datetime.now().isoformat()
    
    def update_group(self, group_id: int, **kwargs) -> bool:
        """更新群组配置"""
        if group_id not in self.groups:
            return False
        
        group_config = self.groups[group_id]
        for key, value in kwargs.items():
            if hasattr(group_config, key):
                setattr(group_config, key, value)
        
        self.updated_at = datetime.now().isoformat()
        return True
    
    def remove_group(self, group_id: int) -> bool:
        """移除群组配置"""
        if group_id in self.groups:
            del self.groups[group_id]
            self.updated_at = datetime.now().isoformat()
            return True
        return False
    
    def cleanup_expired_groups(self) -> List[int]:
        """清理过期的群组，返回被清理的群组ID列表"""
        expired_groups = []
        for group_id, group_config in list(self.groups.items()):
            if group_config.is_expired():
                expired_groups.append(group_id)
                group_config.enabled = False  # 设为禁用而不是删除
        
        if expired_groups:
            self.updated_at = datetime.now().isoformat()
        
        return expired_groups


class BotConfigManager:
    """Bot配置管理器"""
    
    def __init__(self, config_dir: str = "config/bots"):
        self.config_dir = config_dir
        self.configs: Dict[int, BotConfig] = {}
        self.ensure_config_dir()
    
    def ensure_config_dir(self) -> None:
        """确保配置目录存在"""
        os.makedirs(self.config_dir, exist_ok=True)
    
    def get_config_file_path(self, self_id: int) -> str:
        """获取配置文件路径"""
        return os.path.join(self.config_dir, f"{self_id}.json")
    
    def load_config(self, self_id: int) -> BotConfig:
        """加载指定QQ号的配置"""
        config_file = self.get_config_file_path(self_id)
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = BotConfig.from_dict(data)
            else:
                # 创建默认配置
                config = BotConfig(self_id=self_id)
                self.save_config(config)
            
            self.configs[self_id] = config
            return config
            
        except Exception as e:
            print(f"Error loading bot config for {self_id}: {e}")
            # 返回默认配置
            config = BotConfig(self_id=self_id)
            self.configs[self_id] = config
            return config
    
    def save_config(self, config: BotConfig) -> bool:
        """保存配置"""
        try:
            config.updated_at = datetime.now().isoformat()
            config_file = self.get_config_file_path(config.self_id)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            
            self.configs[config.self_id] = config
            return True
            
        except Exception as e:
            print(f"Error saving bot config for {config.self_id}: {e}")
            return False
    
    def get_config(self, self_id: int) -> BotConfig:
        """获取配置（如果不存在则加载）"""
        if self_id not in self.configs:
            return self.load_config(self_id)
        return self.configs[self_id]
    
    def get_all_configs(self) -> Dict[int, BotConfig]:
        """获取所有已加载的配置"""
        return self.configs.copy()
    
    def delete_config(self, self_id: int) -> bool:
        """删除配置"""
        try:
            config_file = self.get_config_file_path(self_id)
            if os.path.exists(config_file):
                os.remove(config_file)
            
            if self_id in self.configs:
                del self.configs[self_id]
            
            return True
        except Exception as e:
            print(f"Error deleting bot config for {self_id}: {e}")
            return False
    
    def cleanup_all_expired_groups(self) -> Dict[int, List[int]]:
        """清理所有Bot的过期群组"""
        result = {}
        for self_id, config in self.configs.items():
            expired_groups = config.cleanup_expired_groups()
            if expired_groups:
                result[self_id] = expired_groups
                self.save_config(config)
        return result
