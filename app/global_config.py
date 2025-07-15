"""
全局配置管理模块
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"  # sqlite, mysql, postgresql
    host: str = "localhost"
    port: int = 3306
    username: str = ""
    password: str = ""
    database: str = "botshepherd"
    data_path: str = "./data"
    auto_expire_days: int = 30  # 数据自动过期天数
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WebUIConfig:
    """WebUI配置"""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    secret_key: str = "botshepherd-secret-key"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebUIConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CommandConfig:
    """指令配置"""
    default_prefixes: List[str] = field(default_factory=lambda: ["/", "!", "#", ".", "。"])
    admin_prefixes: List[str] = field(default_factory=lambda: ["sudo ", "admin "])
    case_sensitive: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SecurityConfig:
    """安全配置"""
    enable_rate_limit: bool = True
    rate_limit_window: int = 60  # 秒
    rate_limit_max_requests: int = 30
    enable_ip_whitelist: bool = False
    ip_whitelist: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_to_file: bool = True
    log_file_path: str = "logs/botshepherd.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoggingConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GlobalConfig:
    """全局配置"""
    # 管理员配置
    admin_qq_list: List[int] = field(default_factory=list)
    super_admin_qq: Optional[int] = None
    
    # 系统配置
    system_name: str = "BotShepherd"
    version: str = "2.0.0"
    timezone: str = "UTC"
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    webui: WebUIConfig = field(default_factory=WebUIConfig)
    command: CommandConfig = field(default_factory=CommandConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # 功能开关
    enable_message_statistics: bool = True
    enable_keyword_monitoring: bool = True
    enable_auto_reply: bool = False
    enable_forward_message: bool = True
    
    # 其他配置
    max_message_length: int = 4096
    default_timeout: float = 30.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "admin_qq_list": self.admin_qq_list,
            "super_admin_qq": self.super_admin_qq,
            "system_name": self.system_name,
            "version": self.version,
            "timezone": self.timezone,
            "database": self.database.to_dict(),
            "webui": self.webui.to_dict(),
            "command": self.command.to_dict(),
            "security": self.security.to_dict(),
            "logging": self.logging.to_dict(),
            "enable_message_statistics": self.enable_message_statistics,
            "enable_keyword_monitoring": self.enable_keyword_monitoring,
            "enable_auto_reply": self.enable_auto_reply,
            "enable_forward_message": self.enable_forward_message,
            "max_message_length": self.max_message_length,
            "default_timeout": self.default_timeout
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlobalConfig':
        # 处理子配置对象
        database_data = data.get("database", {})
        webui_data = data.get("webui", {})
        command_data = data.get("command", {})
        security_data = data.get("security", {})
        logging_data = data.get("logging", {})
        
        return cls(
            admin_qq_list=data.get("admin_qq_list", []),
            super_admin_qq=data.get("super_admin_qq"),
            system_name=data.get("system_name", "BotShepherd"),
            version=data.get("version", "2.0.0"),
            timezone=data.get("timezone", "UTC"),
            database=DatabaseConfig.from_dict(database_data),
            webui=WebUIConfig.from_dict(webui_data),
            command=CommandConfig.from_dict(command_data),
            security=SecurityConfig.from_dict(security_data),
            logging=LoggingConfig.from_dict(logging_data),
            enable_message_statistics=data.get("enable_message_statistics", True),
            enable_keyword_monitoring=data.get("enable_keyword_monitoring", True),
            enable_auto_reply=data.get("enable_auto_reply", False),
            enable_forward_message=data.get("enable_forward_message", True),
            max_message_length=data.get("max_message_length", 4096),
            default_timeout=data.get("default_timeout", 30.0)
        )


class GlobalConfigManager:
    """全局配置管理器"""
    
    def __init__(self, config_file: str = "config/global_config.json"):
        self.config_file = config_file
        self.config = GlobalConfig()
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = GlobalConfig.from_dict(data)
            else:
                # 创建默认配置文件
                self.save_config()
        except Exception as e:
            print(f"Error loading global config: {e}")
            self.config = GlobalConfig()
    
    def save_config(self) -> bool:
        """保存配置"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving global config: {e}")
            return False
    
    def get_config(self) -> GlobalConfig:
        """获取配置"""
        return self.config
    
    def update_config(self, **kwargs) -> bool:
        """更新配置"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            return self.save_config()
        except Exception as e:
            print(f"Error updating global config: {e}")
            return False
    
    def is_admin(self, qq: int) -> bool:
        """检查是否为管理员"""
        return qq in self.config.admin_qq_list or qq == self.config.super_admin_qq
    
    def is_super_admin(self, qq: int) -> bool:
        """检查是否为超级管理员"""
        return qq == self.config.super_admin_qq
    
    def add_admin(self, qq: int) -> bool:
        """添加管理员"""
        if qq not in self.config.admin_qq_list:
            self.config.admin_qq_list.append(qq)
            return self.save_config()
        return True
    
    def remove_admin(self, qq: int) -> bool:
        """移除管理员"""
        if qq in self.config.admin_qq_list:
            self.config.admin_qq_list.remove(qq)
            return self.save_config()
        return True
    
    def set_super_admin(self, qq: int) -> bool:
        """设置超级管理员"""
        self.config.super_admin_qq = qq
        return self.save_config()
    
    def get_command_prefixes(self) -> List[str]:
        """获取指令前缀"""
        return self.config.command.default_prefixes
    
    def get_admin_prefixes(self) -> List[str]:
        """获取管理员指令前缀"""
        return self.config.command.admin_prefixes
