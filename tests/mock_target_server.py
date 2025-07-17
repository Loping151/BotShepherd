#!/usr/bin/env python3
"""
模拟目标服务器
用于测试BotShepherd的WebSocket代理功能
"""

import asyncio
import websockets
import json
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_client(websocket):
    """处理客户端连接"""
    client_ip = websocket.remote_address
    path = getattr(websocket, 'path', '/')
    logger.info(f"新的客户端连接: {client_ip} 路径: {path}")
    
    try:
        async for message in websocket:
            logger.info(f"收到消息: {message}")
            
            try:
                # 解析JSON消息
                data = json.loads(message)
                action = data.get("action", "")
                echo = data.get("echo", "")
                
                # 模拟响应
                if action == "get_status":
                    response = {
                        "status": "ok",
                        "retcode": 0,
                        "data": {
                            "online": True,
                            "good": True
                        },
                        "echo": echo
                    }
                elif action == "get_version_info":
                    response = {
                        "status": "ok", 
                        "retcode": 0,
                        "data": {
                            "app_name": "MockBot",
                            "app_version": "1.0.0",
                            "protocol_version": "v11"
                        },
                        "echo": echo
                    }
                else:
                    response = {
                        "status": "failed",
                        "retcode": -1,
                        "data": None,
                        "echo": echo
                    }
                
                response_json = json.dumps(response, ensure_ascii=False)
                logger.info(f"发送响应: {response_json}")
                await websocket.send(response_json)
                
            except json.JSONDecodeError:
                logger.warning(f"收到非JSON消息: {message}")
            except Exception as e:
                logger.error(f"处理消息失败: {e}")
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端连接已关闭: {client_ip}")
    except Exception as e:
        logger.error(f"连接处理错误: {e}")

async def main():
    """主函数"""
    host = "localhost"
    port = 2539
    
    logger.info(f"启动模拟目标服务器在 ws://{host}:{port}/OneBotv11")
    
    async with websockets.serve(handle_client, host, port):
        logger.info("模拟目标服务器已启动")
        # 保持运行
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("模拟目标服务器已停止")
