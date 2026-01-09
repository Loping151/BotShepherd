"""
WebSocket代理服务器
实现一对多WebSocket代理功能
"""

import asyncio
import websockets
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from app.onebotv11.message_segment import MessageSegmentParser

from ..onebotv11.models import ApiResponse, Event
from ..commands import CommandHandler
from .message_processor import MessageProcessor
from ..utils.reboot import construct_reboot_message

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


class ProxyConnection:
    """单个代理连接"""

    def __init__(self, connection_id, config, client_ws, config_manager, database_manager, logger, backup_manager=None, status_callback=None, api_response_callback=None):
        self.connection_id = connection_id
        self.config = config
        self.client_ws = client_ws
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.logger = logger
        self.backup_manager = backup_manager
        self.status_callback = status_callback
        self.api_response_callback = api_response_callback

        self.target_connections = []
        self.echo_cache = {}
        self.running = False
        self.client_headers = None
        self.first_message = None
        self.self_id: int | None = None

        self.reconnect_locks = []  # 每个 target_index 一个 Lock
        for _ in self.config.get("target_endpoints", []):
            self.reconnect_locks.append(asyncio.Lock())

        # 初始化消息处理器
        self.message_processor = MessageProcessor(config_manager, database_manager, logger)

        # 自身指令处理
        self.command_handler = CommandHandler(config_manager, database_manager, logger, backup_manager)
        
    async def start_proxy(self):
        """启动代理"""
        self.running = True
        
        try:
            # 等待客户端第一个消息以获取请求头
            self.first_message = await self.client_ws.recv()

            try:
                # 尝试不同的方式获取请求头
                if hasattr(self.client_ws, 'request_headers'):
                    self.client_headers = self.client_ws.request_headers
                elif hasattr(self.client_ws, 'headers'):
                    self.client_headers = self.client_ws.headers
                elif hasattr(self.client_ws, 'request') and hasattr(self.client_ws.request, 'headers'):
                    self.client_headers = self.client_ws.request.headers
                else:
                    self.client_headers = {}
                    self.logger.ws.warning(f"[{self.connection_id}] 无法获取客户端请求头")
            except Exception as e:
                self.logger.ws.warning(f"[{self.connection_id}] 获取客户端请求头失败: {e}")
                self.client_headers = {}
            
            
            # 连接到目标端点
            await self._connect_to_targets()
            
            # 处理第一个消息，其中yunzai需要这个lifecycle消息来注册
            await self._process_client_message(self.first_message)
            
            await self.send_reboot_message()

            # 启动消息转发任务
            tasks = []

            # 客户端到目标的转发任务
            tasks.append(asyncio.create_task(self._forward_client_to_targets()))

            # 目标到客户端的转发任务
            for idx, target_ws in enumerate(self.target_connections):
                if target_ws:
                    tasks.append(asyncio.create_task(
                        self._forward_target_to_client(target_ws, self.list_index2target_index(idx))
                    ))

            if tasks:
                # 等待任务，当任意任务结束时（如客户端断开）立即取消其他任务
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                # 取消所有未完成的任务
                for task in pending:
                    task.cancel()

                # 等待所有任务真正结束
                if pending:
                    await asyncio.wait(pending, timeout=3.0)

                # 检查是否是客户端断开导致的
                for task in done:
                    if task.exception():
                        self.logger.ws.info(f"[{self.connection_id}] 任务异常退出: {task.exception()}")
            else:
                self.logger.ws.warning(f"[{self.connection_id}] 没有转发任务，连接将关闭")
            
        except Exception as e:
            self.logger.ws.error(f"[{self.connection_id}] 代理运行错误: {e}")
        finally:
            await self.stop()


    async def _connect_to_target(self, endpoint: str, target_index: int):
         try:
            
            if target_index > len(self.target_connections) + 1 or target_index == 0:
                raise Exception(f"[{self.connection_id}] 目标ID {target_index} 超出范围!")
            
            # 使用客户端请求头连接目标
            extra_headers = {}
            if self.client_headers:
                # 更新相关请求头，其中Nonebot必须x-self-id
                for header_name in ["authorization", "x-self-id", "x-client-role", "user-agent"]:
                    if header_name in self.client_headers:
                        extra_headers[header_name] = self.client_headers[header_name]
            
            # 尝试使用不同的参数名连接，同时配置连接参数
            target_ws = None
            connection_params = {
                'max_size': None,  # 移除消息大小限制
                'max_queue': None,  # 移除队列大小限制
                'ping_interval': 300,  # 心跳间隔
                'ping_timeout': 60,   # 心跳超时
                'close_timeout': None,   # 关闭超时
                'compression': 'deflate'
            }

            connection_attempts = [
                # 尝试 extra_headers 参数
                lambda: websockets.connect(endpoint, extra_headers=extra_headers, **connection_params),
                # 尝试 additional_headers 参数
                lambda: websockets.connect(endpoint, additional_headers=extra_headers, **connection_params),
                # 不使用额外头部，无法连接Nonebot2
                lambda: websockets.connect(endpoint, **connection_params)
            ]

            for attempt in connection_attempts:
                try:
                    target_ws = await attempt()
                    break
                except TypeError:
                    # 参数不支持，尝试下一种方式
                    continue
                except Exception as e:
                    # 其他错误，直接抛出
                    raise e
            
            if target_index == len(self.target_connections) + 1: # next one to append
                self.target_connections.append(target_ws) # 保证index正确，即使是None也添加
            else:
                self.target_connections[self.target_index2list_index(target_index)] = target_ws
            if target_ws is None:
                raise Exception(f"[{self.connection_id}] 所有连接方式都失败")
            
            self.logger.ws.info(f"[{self.connection_id}] 已连接到目标: {endpoint}")
            return target_ws
            
         except Exception as e:
            if target_index == len(self.target_connections) + 1:
                self.target_connections.append(None)
            else:
                self.target_connections[self.target_index2list_index(target_index)] = None
            self.logger.ws.error(f"[{self.connection_id}] 连接目标失败 {endpoint}: {e}")
            return None


    async def _connect_to_targets(self):
        """连接到目标端点"""
        target_endpoints = self.config.get("target_endpoints", [])

        # 先标记哪些目标需要启动重连（避免在循环中启动任务）
        failed_targets = []
        for idx, endpoint in enumerate(target_endpoints):
            target_ws = await self._connect_to_target(endpoint, self.list_index2target_index(idx))
            # 如果连接失败（返回 None），记录下来稍后启动重连
            if target_ws is None:
                failed_targets.append(self.list_index2target_index(idx))

        # 在所有连接尝试完成后，启动失败目标的重连任务
        for target_index in failed_targets:
            self.logger.ws.warning(f"[{self.connection_id}] 目标 {target_index} 初始连接失败，启动后台重连")
            asyncio.create_task(self._start_reconnect_with_delay(target_index))
    
    async def _forward_client_to_targets(self):
        """转发客户端消息到目标"""
        try:
            async for message in self.client_ws:
                try:
                    await self._process_client_message(message)
                except websockets.exceptions.ConnectionClosed:
                    continue
        except Exception as e:
            self.logger.ws.error(f"[{self.connection_id}] 客户端消息转发错误: {e}")
    
    async def _forward_target_to_client(self, target_ws, target_index):
        """转发目标消息到客户端"""
        try:
            async for message in target_ws:
                await self._process_target_message(message, target_index)
        except websockets.exceptions.ConnectionClosed:
            await self._reconnect_target(target_index)
        except TypeError as e:
            await self._reconnect_target(target_index) # 如果是None，也挂一个后台重连
        except Exception as e:
            self.logger.ws.error(f"[{self.connection_id}] 目标消息转发错误 {target_index}: {e}")

    async def _start_reconnect_with_delay(self, target_index: int):
        """延迟启动重连任务，等待客户端完全初始化"""
        await asyncio.sleep(5)
        await self._reconnect_target(target_index)

    async def _reconnect_target(self, target_index: int):
        self.logger.ws.info(f"[{self.connection_id}] 目标连接 {target_index} 已关闭。将在120秒内持续尝试重新连接。")

        lock = self.reconnect_locks[self.target_index2list_index(target_index)]
        if not lock.locked():
            async with lock:
                for _ in range(40):
                    # 检查客户端连接是否还活着 - 使用 state 属性
                    client_state = getattr(self.client_ws, 'state', None)
                    if not self.running or client_state != 1:  # 1 = OPEN 状态
                        self.logger.ws.info(f"[{self.connection_id}] 客户端已断开 (running={self.running}, state={client_state})，停止重连目标 {target_index}")
                        return

                    await asyncio.sleep(3)
                    try:
                        target_ws = await self._connect_to_target(self.config.get("target_endpoints", [])[self.target_index2list_index(target_index)], target_index)
                        if target_ws is None:
                            continue
                        await self._process_client_message(self.first_message) # 比如yunzai需要使用first Message重新注册
                        self.logger.ws.info(f"[{self.connection_id}] 目标连接 {target_index} 恢复成功，5秒后重新开始转发。")
                        await asyncio.sleep(5)
                        await self._forward_target_to_client(target_ws, target_index)
                    except Exception as e:
                        self.logger.ws.warning(f"[{self.connection_id}] 尝试重连目标 {target_index} 失败: {e}")

                # 长期重连循环
                while self.running:
                    # 检查客户端状态
                    client_state = getattr(self.client_ws, 'state', None)
                    if client_state != 1:  # 1 = OPEN 状态
                        break

                    await asyncio.sleep(600) # 10分钟后再试
                    try:
                        target_ws = await self._connect_to_target(self.config.get("target_endpoints", [])[self.target_index2list_index(target_index)], target_index)
                        if target_ws:
                            await self._process_client_message(self.first_message)
                            self.logger.ws.info(f"[{self.connection_id}] 目标连接 {target_index} 恢复成功，5秒后重新开始转发。")
                            await asyncio.sleep(5)
                            await self._forward_target_to_client(target_ws, target_index)
                    except Exception as e:
                        pass

                self.logger.ws.info(f"[{self.connection_id}] 客户端已断开，终止目标 {target_index} 的重连循环")
                        
    async def _process_client_message(self, message: str):
        """处理客户端消息"""
        try:
            # 解析JSON消息
            message_data = json.loads(message)
            if message_data.get("self_id"): # 每次更新，客户端可能会换账号
                if self.self_id and self.self_id != message_data["self_id"]:
                    # 但是，不论是通过头注册还是yunzai的方式都不能支持账号的热切换
                    self.logger.ws.warning("[{}] 客户端账号已切换到 {}，请重启该连接！".format(self.connection_id, message_data['self_id']))
                self.self_id = message_data["self_id"]
                # 通过回调更新状态中的self_id
                if self.status_callback:
                    self.status_callback('self_id', self.self_id)
            
            # 检查是否是API响应（有echo字段）
            if message_data.get("echo"):
                echo_val = str(message_data["echo"])
                # 调用API响应回调（用于处理待处理的API请求，如在线状态检查）
                if self.api_response_callback:
                    if self.api_response_callback(echo_val, message_data):
                        return

            # 消息预处理
            message_data = await self.command_handler.preprocesser(message_data)
            processed_message, parsed_event = await self._preprocess_message(message_data)
            
            if processed_message:
                if self._check_api_call_succ(parsed_event):
                    # 如果是发送成功
                    data_in_api = parsed_event.data
                    if isinstance(data_in_api, dict): # get list api 不可能是发送
                        message_id = message_data.get("data", {}).get("message_id")
                        await self.database_manager.save_message(
                            await self._construct_msg_from_echo(message_data["echo"], message_id=message_id), "SEND", self.connection_id
                        )
                else:
                    # 记录消息到数据库，注意记录的是处理后的消息，所以统计功能是无视别名的，只需要按key搜索即可
                    # 收到裸消息不会是api response
                    self._log_api_call_fail(parsed_event)
                    await self.database_manager.save_message(
                        processed_message, "RECV", self.connection_id
                    )
                
                # 本体指令集
                resp_api = await self.command_handler.handle_message(parsed_event)
                if resp_api:
                    processed_message = None # 自身返回时，阻止事件传递给框架 Preprocesser不受影响
                    await self._process_target_message(resp_api, 0) # 自身的index为0，其实并不是连接
            
                # 转发到所有目标
                processed_json = json.dumps(processed_message, ensure_ascii=False)

                if message_data.get("echo"):
                    # api请求内容，尽可能保证各框架的发送api都使用了echo。
                    # 尝试从各个 target_index 的缓存中查找
                    echo_val = str(message_data["echo"])
                    matched_target_index = None
                    for idx in range(1, len(self.target_connections) + 1):
                        echo_key = f"{idx}_{echo_val}"
                        if echo_key in self.echo_cache:
                            matched_target_index = self.echo_cache.pop(echo_key, {}).get("target_index")
                            break

                    if matched_target_index is not None and matched_target_index > 0 and self.target_connections[self.target_index2list_index(matched_target_index)]:
                        self.logger.ws.debug(f"[{self.connection_id}] 发送API请求到目标 {matched_target_index}: {processed_json[:1000]}")
                        try:
                            await self.target_connections[self.target_index2list_index(matched_target_index)].send(processed_json)
                        except websockets.exceptions.ConnectionClosed:
                            return
                        except Exception as e:
                            self.logger.ws.error(f"[{self.connection_id}] 发送到目标失败: {e}")
                            raise
                else:
                    for target_index, target_ws in enumerate(self.target_connections):
                        if target_ws:
                            try:
                                await target_ws.send(processed_json)
                            except websockets.exceptions.ConnectionClosed:
                                continue # 发送时不再捕捉
                            except Exception as e:
                                self.logger.ws.error(f"[{self.connection_id}] 发送到目标失败: {e}")
                                raise
            
        except json.JSONDecodeError:
            self.logger.ws.warning(f"[{self.connection_id}] 收到非JSON消息: {message[:1000]}")
        except websockets.exceptions.ConnectionClosed:
            raise
        except Exception as e:
            self.logger.ws.error(f"[{self.connection_id}] 处理客户端消息失败: {e}")
    
    async def _process_target_message(self, message: str | dict, target_index: int):
        """处理目标消息"""
        try:
            # 解析JSON消息
            if isinstance(message, str):
                message_data = json.loads(message)
            else:
                message_data = message
            
            self.logger.ws.debug(f"[{self.connection_id}] 来自连接 {target_index} 的API响应: {str(message_data)[:1000]}")
            
            if not self._construct_echo_info(message_data, target_index):
                # 兼容不使用echo回报的框架，不清楚有没有
                message_data_as_recv = await self._construct_data_as_msg(message_data)
                await self.database_manager.save_message(
                    message_data_as_recv, "SEND", self.connection_id
                )
            
            # 消息后处理
            processed_message = await self._postprocess_message(message_data, str(self.self_id))
            
            if processed_message:
                # 发送到客户端
                processed_json = json.dumps(processed_message, ensure_ascii=False)
                await self.client_ws.send(processed_json)
            
        except json.JSONDecodeError:
            self.logger.ws.warning(f"[{self.connection_id}] 目标 {target_index} 发送非JSON消息: {message[:1000]}")
        except websockets.exceptions.ConnectionClosed:
            raise
        except Exception as e:
            self.logger.ws.error(f"[{self.connection_id}] 处理目标消息 {message} 失败: {e}")
    
    async def _preprocess_message(self, message_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Event]]:
        """消息预处理"""
        return await self.message_processor.preprocess_client_message(message_data)

    async def _postprocess_message(self, message_data: Dict[str, Any], self_id: str) -> Optional[Dict[str, Any]]:
        """消息后处理"""
        return await self.message_processor.postprocess_target_message(message_data, self_id)
    
    async def send_reboot_message(self):
        api_resp = await construct_reboot_message(str(self.self_id))
        if api_resp:
            await self._process_target_message(api_resp, 0)
    
    def _construct_echo_info(self, message_data, target_index) -> str | None:
        echo = str(message_data.get("echo"))
        if not echo:
            return None

        # 将 target_index 加入键值，防止不同连接的 echo 混淆
        echo_key = f"{target_index}_{echo}"

        echo_info = {
            "data": message_data,
            "create_timestamp": int(datetime.now().timestamp()),
            "target_index": target_index,
            "original_echo": echo
        }

        if echo_key in self.echo_cache:
            self.logger.ws.warning(f"[{self.connection_id}] echo {echo_key} 已存在，将被覆盖")
        self.echo_cache[echo_key] = echo_info
        self.logger.ws.debug(f"[{self.connection_id}] 收到echo {echo_key}，缓存大小 {len(self.echo_cache)}")

        # 当缓存首次达到100个的时候。该函数阻塞。如网络正常不应该有这么多cache。
        if len(self.echo_cache) % 100 == 0:
            self.logger.ws.warning(f"[{self.connection_id}] echo 缓存达到 {len(self.echo_cache)} 个，强制清理过期的echo!")
            now_ts = int(datetime.now().timestamp())
            old_keys = [k for k, v in self.echo_cache.items() if now_ts - v.get("create_timestamp", 0) > 120]
            for k in old_keys:
                del self.echo_cache[k]

        return echo
    
    @staticmethod
    def _check_api_call_succ(event: Event):
        if isinstance(event, ApiResponse):
            return event.status == "ok" and event.retcode == 0
        return False
    
    def _log_api_call_fail(self, event: Event):
        if isinstance(event, ApiResponse):
            if event.status != "ok" or event.retcode != 0:
                # echo 现在包含 target_index 前缀，需要查找匹配的键
                echo_val = str(event.echo)
                echo_info = None
                for idx in range(1, len(self.target_connections) + 1):
                    echo_key = f"{idx}_{echo_val}"
                    if echo_key in self.echo_cache:
                        echo_info = self.echo_cache.get(echo_key, None)
                        break

                if echo_info:
                    # 截断过长的数据（如base64）避免日志爆炸
                    data_str = str(echo_info['data'])
                    if len(data_str) > 200:
                        data_str = data_str[:200] + f"...[total length: {len(data_str)}]"
                    self.logger.ws.warning("[{}] API调用失败: {} -> {}".format(self.connection_id, data_str, event))
                    
    async def _construct_msg_from_echo(self, echo, **kwargs):
        """从api结果中构造模拟收到消息"""
        # echo 现在包含 target_index 前缀，需要查找匹配的键
        echo_val = str(echo)
        echo_info = None
        for idx in range(1, len(self.target_connections) + 1):
            echo_key = f"{idx}_{echo_val}"
            if echo_key in self.echo_cache:
                echo_info = self.echo_cache.get(echo_key, None)
                break

        if echo_info:
            return await self._construct_data_as_msg(echo_info["data"], **kwargs)
        return {}
    
    async def _construct_data_as_msg(self, message_data, **kwargs):
        """将发送api请求转换为消息事件"""
        
        if 'send' not in message_data.get('action'):
            return {}
        params = message_data.get("params", {})
        params.update({"self_id": self.self_id})
        if "sender" not in params:
            params.update({"sender": {"user_id": self.self_id, "nickname": "BS Bot Send"}})
        # 这个 message_sent 不是 napcat 那种修改的 Onebot，而是本框架数据库中的标识
        params.update({"post_type": "message_sent"})
        raw_message = MessageSegmentParser.message2raw_message(params.get("message", []))
        params.update({"raw_message": raw_message})
        
        params.update(kwargs)
        return params
    
    @staticmethod
    def target_index2list_index(target_index):
        return target_index - 1
    
    @staticmethod
    def list_index2target_index(list_index):
        return list_index + 1
    
    async def stop(self):
        """停止代理连接"""
        self.running = False

        # 关闭目标连接
        close_tasks = []
        for target_ws in self.target_connections:
            close_tasks.append(asyncio.create_task(self._close_websocket(target_ws)))

        # 关闭客户端连接
        if self.client_ws:
            close_tasks.append(asyncio.create_task(self._close_websocket(self.client_ws)))

        if close_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*close_tasks, return_exceptions=True),
                    timeout=3.0  # 3秒超时
                )
            except asyncio.TimeoutError:
                self.logger.ws.warning(f"[{self.connection_id}] 关闭连接超时")
            except Exception as e:
                self.logger.ws.error(f"[{self.connection_id}] 关闭连接时出错: {e}")

        self.target_connections.clear()

    async def _close_websocket(self, ws):
        """安全关闭WebSocket连接"""
        try:
            if ws:
                await ws.close()
        except Exception as e:
            self.logger.ws.error(f"[{self.connection_id}] 关闭WebSocket连接时出错: {e}")
            