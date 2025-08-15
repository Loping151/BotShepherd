"""
WebSocket代理服务器
实现一对多WebSocket代理功能
"""

import asyncio
import websockets
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
from pathlib import Path

from app.onebotv11.message_segment import MessageSegmentParser

from ..onebotv11 import EventParser, MessageNormalizer, EventValidator
from ..onebotv11.models import ApiResponse, Event, PrivateMessageEvent, GroupMessageEvent
from ..commands import CommandHandler
from .message_processor import MessageProcessor
from ..utils.reboot import construct_reboot_message

class ProxyServer:
    """WebSocket代理服务器"""
    
    def __init__(self, config_manager, database_manager, logger):
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.logger = logger

        # 连接管理
        self.active_connections = {}  # connection_id -> ProxyConnection
        self.running = False
        
    async def start(self):
        """启动代理服务器"""
        self.running = True
        self.logger.ws.info("启动WebSocket代理服务器...")
        
        # 获取连接配置
        connections_config = self.config_manager.get_connections_config()
        
        # 为每个连接配置启动代理
        tasks = []
        for connection_id, config in connections_config.items():
            if config.get("enabled", False):
                task = asyncio.create_task(
                    self._start_connection_proxy(connection_id, config)
                )
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
            
            # 创建处理器函数
            async def connection_handler(ws):
                # 从WebSocket连接中获取路径
                path = ws.path if hasattr(ws, 'path') else "/"
                
                if connection_id in self.active_connections:
                    self.logger.ws.warning(f"[{connection_id}] 已存在连接，正在关闭旧连接以替换为新连接")
                    try:
                        await self.active_connections[connection_id].stop()
                        await asyncio.sleep(1) # 禁止频繁重启
                    except Exception as e:
                        self.logger.ws.error(f"[{connection_id}] 关闭旧连接失败: {e}")
        
                return await self._handle_client_connection(ws, path, connection_id, config)

            # 启动WebSocket服务器，移除大小和队列限制
            async with websockets.serve(
                connection_handler,
                host,
                port,
                max_size=None,  # 移除消息大小限制
                max_queue=None,  # 移除队列大小限制
                ping_interval=20,  # 心跳间隔
                ping_timeout=20,   # 心跳超时
                close_timeout=None,   # 关闭超时
                compression='deflate'  # 启用压缩
            ):
                self.logger.ws.info(f"连接代理 {connection_id} 已启动在 {client_endpoint}")

                # 保持运行
                while self.running:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            self.logger.ws.error(f"启动连接代理失败 {connection_id}: {e}")
    
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
                logger=self.logger
            )
            
            # 保存活动连接
            self.active_connections[connection_id] = proxy_connection
            
            # 启动代理
            await proxy_connection.start_proxy()
            
        except Exception as e:
            self.logger.ws.error(f"[{connection_id}] 处理客户端连接失败: {e}")
        finally:
            # 清理连接
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            self.logger.ws.info(f"[{connection_id}] 客户端连接已关闭: {client_ip}")
    
    
    async def stop(self):
        """停止代理服务器"""
        self.running = False
        self.logger.ws.info("正在停止WebSocket代理服务器...")

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
    
    def __init__(self, connection_id, config, client_ws, config_manager, database_manager, logger):
        self.connection_id = connection_id
        self.config = config
        self.client_ws = client_ws
        self.config_manager = config_manager
        self.database_manager = database_manager
        self.logger = logger

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
        self.command_handler = CommandHandler(config_manager, database_manager, logger)
        
    async def start_proxy(self):
        """启动代理"""
        self.running = True
        
        try:
            # 等待客户端第一个消息以获取请求头
            self.first_message = await self.client_ws.recv()

            # 获取客户端请求头
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

            self.logger.ws.info(f"[{self.connection_id}] 已连接到 {len(self.target_connections)} 个目标端点")

            # 启动消息转发任务
            tasks = []

            # 客户端到目标的转发任务
            tasks.append(asyncio.create_task(self._forward_client_to_targets()))

            # 目标到客户端的转发任务
            for idx, target_ws in enumerate(self.target_connections):
                tasks.append(asyncio.create_task(
                    self._forward_target_to_client(target_ws, self.list_index2target_index(idx))
                ))

            if tasks:
                # 等待任务完成
                await asyncio.gather(*tasks, return_exceptions=True)
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
                'ping_interval': 20,  # 心跳间隔
                'ping_timeout': 20,   # 心跳超时
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
            self.logger.ws.error(f"[{self.connection_id}] 连接目标失败 {endpoint}: {e}")
            return None


    async def _connect_to_targets(self):
        """连接到目标端点"""
        target_endpoints = self.config.get("target_endpoints", [])
        
        for idx, endpoint in enumerate(target_endpoints):
            await self._connect_to_target(endpoint, self.list_index2target_index(idx))
    
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
            
    async def _reconnect_target(self, target_index: int):
        self.logger.ws.info(f"[{self.connection_id}] 目标连接 {target_index} 已关闭。将在120秒内持续尝试重新连接。")
        lock = self.reconnect_locks[self.target_index2list_index(target_index)]
        if not lock.locked():
            async with lock:
                for _ in range(40):
                    await asyncio.sleep(3)
                    try:
                        target_ws = await self._connect_to_target(self.config.get("target_endpoints", [])[self.target_index2list_index(target_index)], target_index)
                        await self._process_client_message(self.first_message) # 比如yunzai需要使用first Message重新注册
                        self.logger.ws.info(f"[{self.connection_id}] 目标连接 {target_index} 恢复成功，5秒后重新开始转发。")
                        await asyncio.sleep(5)
                        await self._forward_target_to_client(target_ws, target_index)
                    except Exception as e:
                        self.logger.ws.warning(f"[{self.connection_id}] 尝试重连目标 {target_index} 失败: {e}")
                while True:
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
                    target_index = self.echo_cache.pop(str(message_data["echo"]), {}).get("target_index")
                    if target_index is not None and target_index > 0 and self.target_connections[self.target_index2list_index(target_index)]:
                        self.logger.ws.debug(f"[{self.connection_id}] 发送API请求到目标 {target_index}: {processed_json[:1000]}")
                        try:
                            await self.target_connections[self.target_index2list_index(target_index)].send(processed_json)
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
        
        echo_info = {
            "data": message_data,
            "create_timestamp": int(datetime.now().timestamp()),
            "target_index": target_index
        }

        if echo in self.echo_cache:
            self.logger.ws.warning(f"[{self.connection_id}] echo {echo} 已经存在，将被覆盖!可能由于单个账号连接多个相同框架！")
        self.echo_cache[echo] = echo_info
        self.logger.ws.debug(f"[{self.connection_id}] 收到echo {echo}，缓存大小 {len(self.echo_cache)}")

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
                echo_info = self.echo_cache.get(str(event.echo), None)
                if echo_info:
                    self.logger.ws.warning("[{}] API调用失败: {} -> {}".format(self.connection_id, echo_info['data'], event))
                    
    async def _construct_msg_from_echo(self, echo, **kwargs):
        """从api结果中构造模拟收到消息"""
        echo_info = self.echo_cache.get(str(echo), None)
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
            params.update({"sender": {"user_id": self.self_id, "nickname": "BS Bot"}})
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
            