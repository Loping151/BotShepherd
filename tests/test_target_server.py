#!/usr/bin/env python3
"""
测试目标服务器
模拟OneBot框架接收连接
"""

import asyncio
import websockets
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_client(websocket, path=None):
    """处理客户端连接"""
    client_address = websocket.remote_address
    logger.info(f"新的客户端连接: {client_address} 路径: {path}")

    # 打印请求头
    try:
        if hasattr(websocket, 'request_headers'):
            headers = websocket.request_headers
            logger.info(f"请求头: {dict(headers)}")
        elif hasattr(websocket, 'headers'):
            headers = websocket.headers
            logger.info(f"请求头: {dict(headers)}")
        else:
            logger.info("无法获取请求头")
    except Exception as e:
        logger.warning(f"获取请求头失败: {e}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"收到消息: {data}")
                
                # 如果是API调用，返回响应
                if "action" in data:
                    response = {
                        "status": "ok",
                        "retcode": 0,
                        "data": {"online": True, "good": True},
                        "echo": data.get("echo")
                    }
                    await websocket.send(json.dumps(response))
                    logger.info(f"发送响应: {response}")
                
            except json.JSONDecodeError:
                logger.warning(f"收到非JSON消息: {message}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端连接已关闭: {client_address}")
    except Exception as e:
        logger.error(f"处理客户端连接错误: {e}")

async def main():
    """启动测试服务器"""
    logger.info("启动测试目标服务器...")
    
    # 启动服务器
    server = await websockets.serve(handle_client, "localhost", 2540)
    logger.info("测试目标服务器已启动在 ws://localhost:2540")
    
    # 保持运行
    await server.wait_closed()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务器已停止")
