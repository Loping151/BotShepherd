"""
WebSocket代理服务器
实现一对多WebSocket代理功能
"""

import asyncio
import websockets
import json
from datetime import datetime
from typing import Dict, Any, Optional

from .proxy_connection import ProxyConnection

class ProxyServer:
    """WebSocket代理服务器"""

    def __init__(self, config_manager, database_manager, logger, backup_manager=None):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.logger = logger
        self.backup_manager = backup_manager

        # 连接管理
        self.active_connections = {}  # connection_id -> ProxyConnection
        self.connection_locks = {}     # connection_id -> asyncio.Lock (防止竞态条件)
        self.running = False

        # 连接状态跟踪
        self.connection_statuses = {}  # connection_id -> status info
        self.connection_tasks = {}     # connection_id -> asyncio.Task (跟踪每个连接的服务器任务)

        # API响应等待（用于在线状态检查等）
        self.pending_api_requests = {}  # echo -> asyncio.Future
        
    async def start(self):
        """启动代理服务器"""
        self.running = True
        self.logger.ws.info("启动WebSocket代理服务器...")

        # 获取连接配置
        connections_config = self.config_manager.get_connections_config()

        # 初始化所有连接的状态
        for connection_id, config in connections_config.items():
            if config.get("enabled", False):
                self.connection_statuses[connection_id] = {
                    'enabled': True,
                    'client_status': 'starting',
                    'client_endpoint': config.get('client_endpoint', ''),
                    'target_statuses': {},
                    'error': None,
                    'self_id': None
                }
            else:
                self.connection_statuses[connection_id] = {
                    'enabled': False,
                    'client_status': 'disabled',
                    'client_endpoint': config.get('client_endpoint', ''),
                    'target_statuses': {},
                    'error': None,
                    'self_id': None
                }

        # 为每个连接配置启动代理
        tasks = []
        for connection_id, config in connections_config.items():
            if config.get("enabled", False):
                task = asyncio.create_task(
                    self._start_connection_proxy(connection_id, config)
                )
                self.connection_tasks[connection_id] = task
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

            # 检查是否所有启用的连接都失败了
            all_failed = True
            failed_connections = []  # 记录失败的连接信息

            for connection_id, config in connections_config.items():
                if config.get("enabled", False):
                    status = self.connection_statuses.get(connection_id, {})
                    client_status = status.get('client_status')

                    # 只有 listening 或 connected 状态才算成功
                    if client_status in ['listening', 'connected']:
                        all_failed = False
                    else:
                        # 记录失败信息
                        error_msg = status.get('error', '未知错误')
                        endpoint = config.get('client_endpoint', '未知端点')
                        failed_connections.append({
                            'id': connection_id,
                            'endpoint': endpoint,
                            'status': client_status,
                            'error': error_msg
                        })

            if all_failed:
                self.logger.ws.error("=" * 60)
                self.logger.ws.error("所有启用的连接配置都启动失败，WebSocket代理服务器将退出")
                self.logger.ws.error("=" * 60)

                # 详细记录每个失败连接的原因
                for fail_info in failed_connections:
                    self.logger.ws.error(f"连接 [{fail_info['id']}] 启动失败:")
                    self.logger.ws.error(f"  - 端点: {fail_info['endpoint']}")
                    self.logger.ws.error(f"  - 状态: {fail_info['status']}")
                    self.logger.ws.error(f"  - 原因: {fail_info['error']}")

                self.logger.ws.error("=" * 60)
                self.logger.ws.error("请修复上述问题后重启系统")
                return

            # 至少有一个连接成功，记录成功和失败的情况
            success_count = len([c for c in connections_config.values() if c.get("enabled", False)]) - len(failed_connections)
            self.logger.ws.info(f"WebSocket代理服务器启动完成: {success_count} 个连接成功")

            # 如果有部分失败，也记录警告
            if failed_connections:
                self.logger.ws.warning(f"有 {len(failed_connections)} 个连接启动失败:")
                for fail_info in failed_connections:
                    self.logger.ws.warning(f"  - [{fail_info['id']}] {fail_info['endpoint']}: {fail_info['error']}")

            # 保持运行
            while self.running:
                await asyncio.sleep(1)
        else:
            self.logger.ws.warning("没有启用的连接配置")
            # 保持运行状态
            while self.running:
                await asyncio.sleep(1)
    
    async def _start_connection_proxy(self, connection_id: str, config: Dict[str, Any]):
        """启动单个连接的代理"""
        try:
            # 解析客户端监听地址
            client_endpoint = config["client_endpoint"]
            # 提取主机和端口
            if client_endpoint.startswith("ws://"):
                url_part = client_endpoint[5:]  # 移除 "ws://"
                if "/" in url_part:
                    host_port, path = url_part.split("/", 1)
                else:
                    host_port = url_part
                    path = ""

                if ":" in host_port:
                    host, port = host_port.split(":", 1)
                    port = int(port)
                else:
                    host = host_port
                    port = 80
            else:
                raise ValueError(f"不支持的客户端端点格式: {client_endpoint}")

            self.logger.ws.info(f"启动连接代理 {connection_id}: {host}:{port}")

            # 更新状态为正在启动
            if connection_id in self.connection_statuses:
                self.connection_statuses[connection_id]['client_status'] = 'starting'
                self.connection_statuses[connection_id]['error'] = None

            # 创建处理器函数
            async def connection_handler(ws):
                # 记录 WebSocket 连接详细信息
                ws_info = {
                    "remote_address": getattr(ws, 'remote_address', None),
                    "path": getattr(ws, 'path', '/'),
                    "host": getattr(ws, 'host', None),
                    "port": getattr(ws, 'port', None),
                    "id": id(ws),  # Python 对象 ID
                }
                self.logger.ws.info(f"[{connection_id}] 收到新的WebSocket连接: {ws_info}")

                # 更新状态为已连接
                if connection_id in self.connection_statuses:
                    self.connection_statuses[connection_id]['client_status'] = 'connected'
                    self.connection_statuses[connection_id]['client_address'] = str(ws_info.get('remote_address', 'unknown'))

                # 从WebSocket连接中获取路径
                path = ws.path if hasattr(ws, 'path') else "/"

                # 获取或创建该 connection_id 的锁（防止竞态条件）
                if connection_id not in self.connection_locks:
                    self.connection_locks[connection_id] = asyncio.Lock()

                async with self.connection_locks[connection_id]:
                    if connection_id in self.active_connections:
                        old_conn = self.active_connections[connection_id]
                        old_ws = old_conn.client_ws

                        # 检查旧连接是否真的还活着 - 使用 state 属性
                        old_state = getattr(old_ws, 'state', None) if old_ws else None
                        is_old_alive = old_ws and old_state == 1  # 1 = OPEN 状态

                        if is_old_alive:
                            # 旧连接还活着，拒绝新连接（防止频繁重连）
                            old_ip = getattr(old_ws, 'remote_address', 'unknown')
                            new_ip = getattr(ws, 'remote_address', 'unknown')
                            self.logger.ws.warning(
                                f"[{connection_id}] 已存在活跃连接 (旧:{old_ip} vs 新:{new_ip})，拒绝新连接"
                            )
                            await ws.close(1008, "Connection already exists")
                            return
                        else:
                            # 旧连接已死但还在字典中，清理它
                            self.logger.ws.info(f"[{connection_id}] 清理已断开的旧连接")
                            del self.active_connections[connection_id]

                    return await self._handle_client_connection(ws, path, connection_id, config)

            # 启动WebSocket服务器，移除大小和队列限制
            try:
                async with websockets.serve(
                    connection_handler,
                    host,
                    port,
                    max_size=None,  # 移除消息大小限制
                    max_queue=None,  # 移除队列大小限制
                    ping_interval=300,  # 心跳间隔
                    ping_timeout=60,   # 心跳超时
                    close_timeout=None,   # 关闭超时
                    compression='deflate'  # 启用压缩
                ):
                    self.logger.ws.info(f"连接代理 {connection_id} 已启动在 {client_endpoint}")
                    # 更新状态为监听中
                    if connection_id in self.connection_statuses:
                        self.connection_statuses[connection_id]['client_status'] = 'listening'

                    # 保持运行
                    while self.running:
                        await asyncio.sleep(1)
            except OSError as e:
                # 处理端口被占用的情况，不抛出异常，只记录状态
                error_msg = f"端口 {port} 已被占用"
                if "Address already in use" in str(e) or e.errno == 98 or e.errno == 10048:
                    self.logger.ws.warning(f"连接代理 {connection_id} 端口 {port} 已被占用，跳过启动")
                    if connection_id in self.connection_statuses:
                        self.connection_statuses[connection_id]['client_status'] = 'error'
                        self.connection_statuses[connection_id]['error'] = error_msg
                else:
                    error_msg = str(e)
                    self.logger.ws.error(f"连接代理 {connection_id} 启动失败: {error_msg}")
                    if connection_id in self.connection_statuses:
                        self.connection_statuses[connection_id]['client_status'] = 'error'
                        self.connection_statuses[connection_id]['error'] = error_msg

        except Exception as e:
            error_msg = str(e)
            self.logger.ws.error(f"启动连接代理失败 {connection_id}: {error_msg}")
            if connection_id in self.connection_statuses:
                self.connection_statuses[connection_id]['client_status'] = 'error'
                self.connection_statuses[connection_id]['error'] = error_msg
    
    def _update_connection_status(self, connection_id: str, key: str, value: Any):
        """更新连接状态的某个字段"""
        if connection_id in self.connection_statuses:
            self.connection_statuses[connection_id][key] = value

    def _handle_api_response(self, echo: str, response_data: dict) -> bool:
        """处理API响应，检查是否有待处理的请求"""
        if echo in self.pending_api_requests:
            future = self.pending_api_requests[echo]
            if not future.done():
                future.set_result(response_data)
            # 注意：不在这里删除，让请求方法自己清理，以防超时等异常情况
            return True  # 表示这是待处理的请求，应该停止处理
        return False  # 不是待处理的请求，继续处理

    async def check_account_online_status(self, account_id: int) -> bool:
        """通过向连接发送get_status API检查账号是否在线"""
        echo = None
        try:
            matched_connection = None
            for conn_id, conn in self.active_connections.items():
                if conn.self_id == account_id:
                    matched_connection = conn
                    break

            if not matched_connection:
                self.logger.ws.debug(f"账号{account_id}没有匹配的连接，返回离线")
                return False

            echo = f"status_check_{account_id}_{int(datetime.now().timestamp())}"

            future = asyncio.Future()
            self.pending_api_requests[echo] = future

            get_status_request = {
                "action": "get_status",
                "params": {},
                "echo": echo
            }

            request_json = json.dumps(get_status_request, ensure_ascii=False)
            await matched_connection.client_ws.send(request_json)

            try:
                response = await asyncio.wait_for(future, timeout=5.0)
                self.logger.ws.debug(f"账号{account_id}收到get_status响应: {json.dumps(response, ensure_ascii=False)}")
                if isinstance(response, dict):
                    online = response.get("data", {}).get("online")
                    # 根据OneBot v11文档，get_status返回的data.online字段为true表示在线
                    return online == True
                return False
            except asyncio.TimeoutError:
                self.logger.ws.warning(f"检查账号{account_id}在线状态超时")
                return False

        except Exception as e:
            self.logger.ws.error(f"检查账号{account_id}在线状态失败: {e}")
            return False
        finally:
            if echo and echo in self.pending_api_requests:
                del self.pending_api_requests[echo]

    async def _handle_client_connection(self, client_ws, path, connection_id: str, config: Dict[str, Any]):
        """处理客户端连接"""
        client_ip = client_ws.remote_address
        self.logger.ws.info(f"[{connection_id}] 新的客户端连接: {client_ip}")
        
        try:
            # 创建代理连接对象
            proxy_connection = ProxyConnection(
                connection_id=connection_id,
                config=config,
                client_ws=client_ws,
                config_manager=self.config_manager,
                database_manager=self.database_manager,
                logger=self.logger,
                backup_manager=self.backup_manager,
                status_callback=lambda key, value: self._update_connection_status(connection_id, key, value),
                api_response_callback=self._handle_api_response
            )
            
            # 保存活动连接
            self.active_connections[connection_id] = proxy_connection

            # 启动代理
            await proxy_connection.start_proxy()

            # 代理结束后，保存账号ID到状态中
            if proxy_connection.self_id and connection_id in self.connection_statuses:
                self.connection_statuses[connection_id]['self_id'] = proxy_connection.self_id
            
        except Exception as e:
            self.logger.ws.error(f"[{connection_id}] 处理客户端连接失败: {e}")
        finally:
            # 清理连接
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            self.logger.ws.info(f"[{connection_id}] 客户端连接已关闭: {client_ip}")


    def get_connection_statuses(self):
        """获取所有连接的状态"""
        return self.connection_statuses.copy()

    async def restart_connection(self, connection_id: str):
        """重启指定的连接配置

        Args:
            connection_id: 要重启的连接ID
        """
        self.logger.ws.info(f"重启连接配置: {connection_id}")

        # 取消旧的服务器任务（如果有）
        if connection_id in self.connection_tasks:
            old_task = self.connection_tasks[connection_id]
            if not old_task.done():
                old_task.cancel()
                try:
                    await old_task
                except asyncio.CancelledError:
                    self.logger.ws.info(f"[{connection_id}] 旧连接任务已取消")
                except Exception as e:
                    self.logger.ws.warning(f"[{connection_id}] 取消任务时出错: {e}")
            del self.connection_tasks[connection_id]

        # 停止该连接的所有活动连接
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            try:
                await connection.stop()
                self.logger.ws.info(f"[{connection_id}] 已停止旧连接")
            except Exception as e:
                self.logger.ws.error(f"[{connection_id}] 停止连接时出错: {e}")

        # 重新加载配置
        await self.config_manager._load_connections_config()
        config = self.config_manager.get_connections_config().get(connection_id)

        if not config:
            self.logger.ws.warning(f"[{connection_id}] 连接配置不存在")
            # 更新状态为禁用
            self.connection_statuses[connection_id] = {
                'enabled': False,
                'client_status': 'disabled',
                'client_endpoint': '',
                'target_statuses': {},
                'error': '连接配置不存在',
                'self_id': None
            }
            return

        # 启动新连接
        if config.get("enabled", False):
            # 更新状态为启动中
            self.connection_statuses[connection_id] = {
                'enabled': True,
                'client_status': 'starting',
                'client_endpoint': config.get('client_endpoint', ''),
                'target_statuses': {},
                'error': None,
                'self_id': None
            }

            # 创建并保存新的启动任务
            task = asyncio.create_task(
                self._start_connection_proxy(connection_id, config)
            )
            self.connection_tasks[connection_id] = task
            self.logger.ws.info(f"[{connection_id}] 启动新连接任务")
        else:
            # 更新状态为禁用
            self.connection_statuses[connection_id] = {
                'enabled': False,
                'client_status': 'disabled',
                'client_endpoint': config.get('client_endpoint', ''),
                'target_statuses': {},
                'error': None,
                'self_id': None
            }
            self.logger.ws.info(f"[{connection_id}] 连接已禁用，不启动")

    async def stop(self):
        """停止代理服务器"""
        self.running = False
        self.logger.ws.info("正在停止WebSocket代理服务器...")

        # 取消所有连接服务器任务
        for connection_id, task in list(self.connection_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.ws.info(f"[{connection_id}] 连接任务已取消")
                except Exception as e:
                    self.logger.ws.warning(f"[{connection_id}] 取消任务时出错: {e}")
        self.connection_tasks.clear()

        # 关闭所有活动连接
        stop_tasks = []
        for connection in list(self.active_connections.values()):
            try:
                if getattr(connection, "running", True):
                    stop_tasks.append(asyncio.create_task(connection.stop()))
            except Exception as e:
                self.logger.ws.error(f"关闭连接时出错: {e}")

        if stop_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*stop_tasks, return_exceptions=True),
                    timeout=5.0  # 5秒超时
                )
            except asyncio.TimeoutError:
                self.logger.ws.warning("部分连接关闭超时")
            except Exception as e:
                self.logger.ws.error(f"关闭连接任务时出错: {e}")

        self.active_connections.clear()
        self.logger.ws.info("WebSocket代理服务器已停止")