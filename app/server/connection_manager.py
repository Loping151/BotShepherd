"""
连接管理器
管理WebSocket连接状态和统计
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

class ConnectionStatus(Enum):
    """连接状态"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

@dataclass
class ConnectionInfo:
    """连接信息"""
    connection_id: str
    client_ip: str
    client_endpoint: str
    target_endpoints: List[str]
    status: ConnectionStatus
    connected_at: datetime
    last_activity: datetime
    message_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class ConnectionManager:
    """连接管理器"""
    
    def __init__(self, logger):
        self.logger = logger
        self.connections: Dict[str, ConnectionInfo] = {}
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "total_messages": 0,
            "total_errors": 0
        }
        
        # 启动清理任务
        asyncio.create_task(self._cleanup_task())
    
    def add_connection(self, connection_id: str, client_ip: str, 
                      client_endpoint: str, target_endpoints: List[str]) -> ConnectionInfo:
        """添加连接"""
        connection_info = ConnectionInfo(
            connection_id=connection_id,
            client_ip=client_ip,
            client_endpoint=client_endpoint,
            target_endpoints=target_endpoints,
            status=ConnectionStatus.CONNECTING,
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        self.connections[connection_id] = connection_info
        self.connection_stats["total_connections"] += 1
        
        self.logger.info(f"添加连接: {connection_id} from {client_ip}")
        return connection_info
    
    def update_connection_status(self, connection_id: str, status: ConnectionStatus, 
                               error_message: Optional[str] = None):
        """更新连接状态"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        old_status = connection.status
        connection.status = status
        connection.last_activity = datetime.now()
        
        if error_message:
            connection.last_error = error_message
            connection.error_count += 1
            self.connection_stats["total_errors"] += 1
        
        # 更新活动连接数
        if old_status != ConnectionStatus.CONNECTED and status == ConnectionStatus.CONNECTED:
            self.connection_stats["active_connections"] += 1
        elif old_status == ConnectionStatus.CONNECTED and status != ConnectionStatus.CONNECTED:
            self.connection_stats["active_connections"] = max(0, self.connection_stats["active_connections"] - 1)
        
        self.logger.info(f"连接状态更新: {connection_id} {old_status.value} -> {status.value}")
    
    def remove_connection(self, connection_id: str):
        """移除连接"""
        if connection_id not in self.connections:
            return
        
        connection = self.connections[connection_id]
        if connection.status == ConnectionStatus.CONNECTED:
            self.connection_stats["active_connections"] = max(0, self.connection_stats["active_connections"] - 1)
        
        del self.connections[connection_id]
        self.logger.info(f"移除连接: {connection_id}")
    
    def update_message_count(self, connection_id: str):
        """更新消息计数"""
        if connection_id in self.connections:
            self.connections[connection_id].message_count += 1
            self.connections[connection_id].last_activity = datetime.now()
            self.connection_stats["total_messages"] += 1
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """获取连接信息"""
        return self.connections.get(connection_id)
    
    def get_all_connections(self) -> List[ConnectionInfo]:
        """获取所有连接信息"""
        return list(self.connections.values())
    
    def get_active_connections(self) -> List[ConnectionInfo]:
        """获取活动连接"""
        return [conn for conn in self.connections.values() 
                if conn.status == ConnectionStatus.CONNECTED]
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        active_connections = self.get_active_connections()
        
        stats = self.connection_stats.copy()
        stats.update({
            "current_active": len(active_connections),
            "connection_details": []
        })
        
        for conn in active_connections:
            uptime = datetime.now() - conn.connected_at
            stats["connection_details"].append({
                "connection_id": conn.connection_id,
                "client_ip": conn.client_ip,
                "uptime_seconds": uptime.total_seconds(),
                "message_count": conn.message_count,
                "error_count": conn.error_count,
                "last_activity": conn.last_activity.isoformat()
            })
        
        return stats
    
    def get_connection_by_client_ip(self, client_ip: str) -> List[ConnectionInfo]:
        """根据客户端IP获取连接"""
        return [conn for conn in self.connections.values() 
                if conn.client_ip == client_ip]
    
    def is_connection_healthy(self, connection_id: str, 
                            max_idle_minutes: int = 30) -> bool:
        """检查连接是否健康"""
        connection = self.get_connection_info(connection_id)
        if not connection:
            return False
        
        if connection.status != ConnectionStatus.CONNECTED:
            return False
        
        # 检查空闲时间
        idle_time = datetime.now() - connection.last_activity
        if idle_time > timedelta(minutes=max_idle_minutes):
            return False
        
        return True
    
    async def _cleanup_task(self):
        """清理任务"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self._cleanup_stale_connections()
            except Exception as e:
                self.logger.error(f"连接清理任务错误: {e}")
    
    async def _cleanup_stale_connections(self):
        """清理过期连接"""
        current_time = datetime.now()
        stale_connections = []
        
        for connection_id, connection in self.connections.items():
            # 清理超过1小时未活动的非活动连接
            if (connection.status != ConnectionStatus.CONNECTED and 
                current_time - connection.last_activity > timedelta(hours=1)):
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            self.remove_connection(connection_id)
            self.logger.info(f"清理过期连接: {connection_id}")
    
    def get_connection_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取连接历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        history = []
        for connection in self.connections.values():
            if connection.connected_at >= cutoff_time:
                history.append({
                    "connection_id": connection.connection_id,
                    "client_ip": connection.client_ip,
                    "connected_at": connection.connected_at.isoformat(),
                    "status": connection.status.value,
                    "message_count": connection.message_count,
                    "error_count": connection.error_count,
                    "uptime": (datetime.now() - connection.connected_at).total_seconds()
                })
        
        # 按连接时间排序
        history.sort(key=lambda x: x["connected_at"], reverse=True)
        return history
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        error_connections = [conn for conn in self.connections.values() 
                           if conn.error_count > 0]
        
        total_errors = sum(conn.error_count for conn in error_connections)
        
        error_summary = {
            "total_errors": total_errors,
            "error_connections": len(error_connections),
            "recent_errors": []
        }
        
        # 获取最近的错误
        for connection in error_connections:
            if connection.last_error:
                error_summary["recent_errors"].append({
                    "connection_id": connection.connection_id,
                    "client_ip": connection.client_ip,
                    "error_message": connection.last_error,
                    "error_count": connection.error_count,
                    "last_activity": connection.last_activity.isoformat()
                })
        
        # 按最后活动时间排序
        error_summary["recent_errors"].sort(
            key=lambda x: x["last_activity"], reverse=True
        )
        
        return error_summary
    
    def set_connection_metadata(self, connection_id: str, key: str, value: Any):
        """设置连接元数据"""
        if connection_id in self.connections:
            self.connections[connection_id].metadata[key] = value
    
    def get_connection_metadata(self, connection_id: str, key: str) -> Any:
        """获取连接元数据"""
        connection = self.get_connection_info(connection_id)
        if connection:
            return connection.metadata.get(key)
        return None
    
    def export_connection_data(self) -> Dict[str, Any]:
        """导出连接数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "stats": self.get_connection_stats(),
            "connections": [
                {
                    "connection_id": conn.connection_id,
                    "client_ip": conn.client_ip,
                    "client_endpoint": conn.client_endpoint,
                    "target_endpoints": conn.target_endpoints,
                    "status": conn.status.value,
                    "connected_at": conn.connected_at.isoformat(),
                    "last_activity": conn.last_activity.isoformat(),
                    "message_count": conn.message_count,
                    "error_count": conn.error_count,
                    "last_error": conn.last_error,
                    "metadata": conn.metadata
                }
                for conn in self.connections.values()
            ]
        }
