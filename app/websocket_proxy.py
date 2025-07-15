import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import os

from .onebot.event import EventParser, MessageEvent
from .onebot.api import BotAPI, MessageProcessor
from .global_config import GlobalConfigManager
from .bot_config import BotConfigManager
from .database import DatabaseManager
from .statistics import MessageStatistics, StatisticsReporter
from .command_handler import CommandHandler


class SuperWebSocketProxy:
    """超级WebSocket代理服务器 - 支持一对多连接"""

    def __init__(self, connection_config_manager, global_config_manager: GlobalConfigManager,
                 bot_config_manager: BotConfigManager, database_manager: DatabaseManager):
        self.connection_config_manager = connection_config_manager  # 原有的连接配置管理器
        self.global_config = global_config_manager
        self.bot_config_manager = bot_config_manager
        self.database_manager = database_manager

        # 统计模块
        self.statistics = MessageStatistics(database_manager)
        self.reporter = StatisticsReporter(self.statistics)

        # 消息处理器
        self.message_processor = MessageProcessor()

        # 指令处理器
        self.command_handler = CommandHandler(
            global_config_manager, bot_config_manager, self.statistics, self.reporter
        )

        # 连接管理
        self.active_servers = {}  # client_endpoint -> server实例
        self.target_connections = {}  # client_endpoint -> {target_endpoint: websocket}
        self.client_connections = {}  # client_endpoint -> websocket
        self.bot_apis = {}  # client_endpoint -> BotAPI实例

        self.setup_logging()
    
    def setup_logging(self):
        """设置日志"""
        log_config = self.global_config.get_config().logging

        # 创建日志目录
        if log_config.log_to_file:
            os.makedirs(os.path.dirname(log_config.log_file_path), exist_ok=True)

        # 配置日志格式
        logging.basicConfig(
            level=getattr(logging, log_config.level),
            format=log_config.log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_config.log_file_path, encoding='utf-8') if log_config.log_to_file else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log_message(self, direction: str, message: str, connection_id: str = "unknown"):
        """记录并打印消息"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

        log_content = f"[{connection_id}] [{direction}]"

        # 尝试将消息格式化为 JSON 以便阅读
        try:
            data = json.loads(message)
            formatted_message = json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            formatted_message = message

        self.logger.info(f"{log_content}\n{formatted_message}")

    async def process_incoming_message(self, message: str, client_endpoint: str) -> Optional[str]:
        """处理从客户端接收到的消息"""
        try:
            # 解析消息
            data = json.loads(message)

            # 检查是否为事件消息
            if "post_type" in data:
                event = EventParser.parse_event(data)

                # 如果是消息事件，进行统计和处理
                if isinstance(event, MessageEvent):
                    await self.handle_message_event(event, client_endpoint)

            # 处理API响应
            elif "echo" in data:
                # 处理API响应
                client_endpoint_key = client_endpoint
                if client_endpoint_key in self.bot_apis:
                    self.bot_apis[client_endpoint_key].handle_api_response(data)

            # 应用消息处理
            processed_data = await self.message_processor.process_incoming_message(data)
            return json.dumps(processed_data, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Error processing incoming message: {e}")
            return message  # 返回原始消息

    async def handle_message_event(self, event: MessageEvent, client_endpoint: str):
        """处理消息事件"""
        try:
            self_id = event.self_id

            # 获取Bot配置
            bot_config = self.bot_config_manager.get_config(self_id)

            # 检查总开关
            if not bot_config.enabled:
                return

            # 检查用户权限
            if not bot_config.is_user_allowed(event.user_id):
                self.logger.info(f"User {event.user_id} is blacklisted for bot {self_id}")
                return

            # 检查群组权限（如果是群消息）
            if event.is_group_message() and not bot_config.is_group_active(event.group_id):
                self.logger.info(f"Group {event.group_id} is not active for bot {self_id}")
                return

            # 应用上行过滤
            if bot_config.filter_config.enable_upstream_filter:
                if self.apply_upstream_filter(event, bot_config.filter_config.upstream_forbidden_words):
                    self.logger.info(f"Message filtered by upstream filter for bot {self_id}")
                    return

            # 应用指令别名替换
            if bot_config.command_config.enable_aliases:
                self.apply_command_aliases(event, bot_config.command_config.command_aliases)

            # 进行统计
            if bot_config.statistics_config.enable_message_stats:
                await self.statistics.process_message_event(
                    self_id, event, bot_config.statistics_config.monitored_keywords
                )

            # 处理指令
            client_endpoint_key = client_endpoint
            if client_endpoint_key in self.bot_apis:
                bot_api = self.bot_apis[client_endpoint_key]
                await self.command_handler.process_message(event, bot_api)

        except Exception as e:
            self.logger.error(f"Error handling message event: {e}")

    def apply_upstream_filter(self, event: MessageEvent, forbidden_words: List[str]) -> bool:
        """应用上行过滤，返回True表示消息被过滤"""
        text = event.get_plain_text().lower()
        return any(word.lower() in text for word in forbidden_words)

    def apply_command_aliases(self, event: MessageEvent, aliases: Dict[str, List[str]]):
        """应用指令别名替换"""
        text = event.get_plain_text()

        for command, alias_list in aliases.items():
            for alias in alias_list:
                if text.startswith(alias):
                    # 替换消息内容
                    new_text = command + text[len(alias):]
                    # 更新消息段
                    if event.message.segments and event.message.segments[0].type == "text":
                        event.message.segments[0].data["text"] = new_text
                    event.raw_message = new_text
                    break
    
    async def proxy_handler(self, client_ws, path, connection_config):
        """处理客户端连接的代理逻辑 - 支持一对多"""
        connection_id = connection_config.get("name", "unknown")
        client_endpoint = connection_config.get("client_endpoint")
        target_endpoints = connection_config.get("target_endpoints", [])

        if not target_endpoints:
            self.logger.error(f"[{connection_id}] No target endpoints configured")
            return

        client_ip = client_ws.remote_address
        self.logger.info(f"[{connection_id}] New connection from client: {client_ip}")

        # 存储客户端连接
        self.client_connections[client_endpoint] = client_ws

        try:
            # 连接到所有目标服务器
            target_connections = {}
            connection_tasks = []

            for target_endpoint in target_endpoints:
                try:
                    target_ws = await websockets.connect(target_endpoint)
                    target_connections[target_endpoint] = target_ws
                    self.logger.info(f"[{connection_id}] Connected to target: {target_endpoint}")

                    # 创建目标到客户端的转发任务
                    task = asyncio.create_task(
                        self.forward_target_to_client(target_ws, client_ws, target_endpoint, connection_id)
                    )
                    connection_tasks.append(task)

                except Exception as e:
                    self.logger.error(f"[{connection_id}] Failed to connect to {target_endpoint}: {e}")

            # 存储目标连接
            self.target_connections[client_endpoint] = target_connections

            # 创建BotAPI实例
            self.bot_apis[client_endpoint] = BotAPI(target_connections)

            # 创建客户端到目标的转发任务
            client_to_targets_task = asyncio.create_task(
                self.forward_client_to_targets(client_ws, target_connections, client_endpoint, connection_id)
            )
            connection_tasks.append(client_to_targets_task)

            # 等待任一任务完成
            done, pending = await asyncio.wait(
                connection_tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # 取消未完成的任务
            for task in pending:
                task.cancel()

        except Exception as e:
            self.logger.error(f"[{connection_id}] Error in proxy handler: {e}")
        finally:
            # 清理连接
            await self.cleanup_connections(client_endpoint, connection_id)

    async def cleanup_connections(self, client_endpoint: str, connection_id: str):
        """清理连接"""
        try:
            # 关闭目标连接
            if client_endpoint in self.target_connections:
                for target_endpoint, target_ws in self.target_connections[client_endpoint].items():
                    try:
                        await target_ws.close()
                    except:
                        pass
                del self.target_connections[client_endpoint]

            # 清理客户端连接
            if client_endpoint in self.client_connections:
                del self.client_connections[client_endpoint]

            # 清理BotAPI
            if client_endpoint in self.bot_apis:
                del self.bot_apis[client_endpoint]

            self.logger.info(f"[{connection_id}] Connections cleaned up")

        except Exception as e:
            self.logger.error(f"Error cleaning up connections: {e}")
    
    async def forward_client_to_targets(self, client_ws, target_connections: Dict[str, Any],
                                       client_endpoint: str, connection_id: str):
        """从客户端转发消息到所有目标"""
        try:
            async for message in client_ws:
                self.log_message("Client->Targets", message, connection_id)

                # 处理消息
                processed_message = await self.process_incoming_message(message, client_endpoint)

                # 转发到所有目标
                for target_endpoint, target_ws in target_connections.items():
                    try:
                        await target_ws.send(processed_message or message)
                    except Exception as e:
                        self.logger.error(f"[{connection_id}] Error forwarding to {target_endpoint}: {e}")

        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"[{connection_id}] Client connection closed")
        except Exception as e:
            self.logger.error(f"[{connection_id}] Error in client->targets forwarding: {e}")

    async def forward_target_to_client(self, target_ws, client_ws, target_endpoint: str, connection_id: str):
        """从目标转发消息到客户端"""
        try:
            async for message in target_ws:
                self.log_message(f"Target({target_endpoint})->Client", message, connection_id)

                # 处理消息
                processed_message = await self.process_outgoing_message(message, target_endpoint)

                # 转发到客户端
                await client_ws.send(processed_message or message)

        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"[{connection_id}] Target connection closed: {target_endpoint}")
        except Exception as e:
            self.logger.error(f"[{connection_id}] Error in target->client forwarding: {e}")

    async def process_outgoing_message(self, message: str, target_endpoint: str) -> Optional[str]:
        """处理发送到客户端的消息"""
        try:
            # 解析消息
            data = json.loads(message)

            # 应用消息处理
            processed_data = await self.message_processor.process_outgoing_message(data)
            return json.dumps(processed_data, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Error processing outgoing message: {e}")
            return message  # 返回原始消息
    
    async def start_proxy_server(self, connection_id: str, connection_config: Dict[str, Any]):
        """启动单个代理服务器"""
        client_endpoint = connection_config.get("client_endpoint")
        if not client_endpoint:
            self.logger.error(f"[{connection_id}] No client endpoint configured")
            return False

        # 检查target_endpoints（新格式）或target_endpoint（旧格式兼容）
        target_endpoints = connection_config.get("target_endpoints")
        if not target_endpoints:
            # 兼容旧格式
            target_endpoint = connection_config.get("target_endpoint")
            if target_endpoint:
                target_endpoints = [target_endpoint]
            else:
                self.logger.error(f"[{connection_id}] No target endpoints configured")
                return False

        # 更新配置以包含target_endpoints
        connection_config["target_endpoints"] = target_endpoints

        try:
            # 解析客户端端点
            parsed_url = urlparse(client_endpoint)
            host = parsed_url.hostname or "localhost"
            port = parsed_url.port or 8080
            path = parsed_url.path or "/"

            # 创建处理函数
            async def handler(websocket, path_param):
                await self.proxy_handler(websocket, path_param, connection_config)

            # 启动服务器
            server = await websockets.serve(handler, host, port)
            self.active_servers[connection_id] = server

            self.logger.info(f"[{connection_id}] Proxy server started on {client_endpoint} -> {target_endpoints}")
            return True

        except Exception as e:
            self.logger.error(f"[{connection_id}] Failed to start proxy server: {e}")
            return False
    
    async def stop_proxy_server(self, connection_id: str):
        """停止单个代理服务器"""
        if connection_id in self.active_servers:
            server = self.active_servers[connection_id]
            server.close()
            await server.wait_closed()
            del self.active_servers[connection_id]
            self.logger.info(f"[{connection_id}] Proxy server stopped")
            return True
        return False
    
    async def start_all_enabled_servers(self):
        """启动所有启用的代理服务器"""
        enabled_connections = self.config_manager.get_enabled_connections()
        
        for connection_id, connection_config in enabled_connections.items():
            await self.start_proxy_server(connection_id, connection_config)
    
    async def stop_all_servers(self):
        """停止所有代理服务器"""
        for connection_id in list(self.active_servers.keys()):
            await self.stop_proxy_server(connection_id)
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        # 统计连接详情
        connection_details = {}
        for client_endpoint, target_connections in self.target_connections.items():
            connection_details[client_endpoint] = {
                "target_count": len(target_connections),
                "targets": list(target_connections.keys()),
                "has_client": client_endpoint in self.client_connections,
                "has_api": client_endpoint in self.bot_apis
            }

        return {
            "active_servers": list(self.active_servers.keys()),
            "active_client_connections": len(self.client_connections),
            "total_target_connections": sum(len(targets) for targets in self.target_connections.values()),
            "connection_details": connection_details,
            "bot_apis": len(self.bot_apis)
        }

    async def get_bot_api(self, client_endpoint: str) -> Optional[BotAPI]:
        """获取指定客户端端点的BotAPI实例"""
        return self.bot_apis.get(client_endpoint)

    async def send_message_via_api(self, client_endpoint: str, **kwargs) -> Any:
        """通过API发送消息"""
        bot_api = await self.get_bot_api(client_endpoint)
        if bot_api:
            return await bot_api.send_msg(**kwargs)
        return None

    async def get_statistics_report(self, self_id: int, report_type: str = "daily") -> str:
        """获取统计报告"""
        try:
            if report_type == "daily":
                return await self.reporter.generate_daily_report(self_id)
            elif report_type == "weekly":
                return await self.reporter.generate_weekly_report(self_id)
            else:
                return "❌ 不支持的报告类型"
        except Exception as e:
            return f"❌ 生成报告失败: {str(e)}"

    async def cleanup_expired_data(self):
        """清理过期数据"""
        try:
            # 清理过期的群组配置
            expired_groups = self.bot_config_manager.cleanup_all_expired_groups()
            if expired_groups:
                self.logger.info(f"Cleaned up expired groups: {expired_groups}")

            # 清理过期的数据库数据
            global_config = self.global_config.get_config()
            expire_days = global_config.database.auto_expire_days

            for self_id in self.bot_config_manager.get_all_configs().keys():
                await self.database_manager.cleanup_expired_data(self_id, expire_days)

            # 清理统计缓存
            await self.statistics.cleanup_old_cache()

        except Exception as e:
            self.logger.error(f"Error cleaning up expired data: {e}")
