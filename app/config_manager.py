import json
import os
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigManager:
    """配置管理器，负责连接配置的存储和管理"""
    
    def __init__(self, config_file: str = "config/connections.json"):
        self.config_file = config_file
        self.config_data = {}
        self.load_config()
    
    def load_config(self) -> None:
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                # 创建默认配置
                self.config_data = {
                    "connections": {},
                    "settings": {
                        "log_to_file": True,
                        "log_file_name": "logs/ws_log.txt",
                        "auto_start": True
                    }
                }
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config_data = {"connections": {}, "settings": {}}
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_connections(self) -> Dict[str, Any]:
        """获取所有连接配置"""
        return self.config_data.get("connections", {})
    
    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取指定连接配置"""
        return self.config_data.get("connections", {}).get(connection_id)
    
    def add_connection(self, connection_id: str, config: Dict[str, Any]) -> bool:
        """添加新的连接配置"""
        try:
            if "connections" not in self.config_data:
                self.config_data["connections"] = {}
            
            # 添加时间戳
            config["created_at"] = datetime.now().isoformat()
            config["updated_at"] = datetime.now().isoformat()
            
            self.config_data["connections"][connection_id] = config
            return self.save_config()
        except Exception as e:
            print(f"Error adding connection: {e}")
            return False
    
    def update_connection(self, connection_id: str, config: Dict[str, Any]) -> bool:
        """更新连接配置"""
        try:
            if connection_id not in self.config_data.get("connections", {}):
                return False
            
            # 保留创建时间，更新修改时间
            existing_config = self.config_data["connections"][connection_id]
            config["created_at"] = existing_config.get("created_at", datetime.now().isoformat())
            config["updated_at"] = datetime.now().isoformat()
            
            self.config_data["connections"][connection_id] = config
            return self.save_config()
        except Exception as e:
            print(f"Error updating connection: {e}")
            return False
    
    def delete_connection(self, connection_id: str) -> bool:
        """删除连接配置"""
        try:
            if connection_id in self.config_data.get("connections", {}):
                del self.config_data["connections"][connection_id]
                return self.save_config()
            return False
        except Exception as e:
            print(f"Error deleting connection: {e}")
            return False
    
    def get_settings(self) -> Dict[str, Any]:
        """获取系统设置"""
        return self.config_data.get("settings", {})
    
    def update_settings(self, settings: Dict[str, Any]) -> bool:
        """更新系统设置"""
        try:
            if "settings" not in self.config_data:
                self.config_data["settings"] = {}
            
            self.config_data["settings"].update(settings)
            return self.save_config()
        except Exception as e:
            print(f"Error updating settings: {e}")
            return False
    
    def get_enabled_connections(self) -> Dict[str, Any]:
        """获取所有启用的连接配置"""
        connections = self.get_connections()
        return {
            conn_id: conn_config 
            for conn_id, conn_config in connections.items() 
            if conn_config.get("enabled", False)
        }
