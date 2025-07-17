#!/usr/bin/env python3
"""
测试WebSocket连接和请求头传递
"""

import asyncio
import websockets
import json
import time

async def test_websocket_connection():
    """测试WebSocket连接"""
    
    # 测试用的请求头
    headers = {
        "User-Agent": "TestBot/1.0",
        "Authorization": "Bearer test_token_123",
        "X-Client-Role": "bot"
    }
    
    try:
        print("正在连接到BotShepherd代理...")

        # 连接到BotShepherd代理
        # 尝试不同的参数名
        websocket = None
        connection_attempts = [
            # 尝试 extra_headers 参数
            lambda: websockets.connect("ws://localhost:2538", extra_headers=headers),
            # 尝试 additional_headers 参数
            lambda: websockets.connect("ws://localhost:2538", additional_headers=headers),
            # 不使用额外头部
            lambda: websockets.connect("ws://localhost:2538")
        ]

        for attempt in connection_attempts:
            try:
                websocket = await attempt()
                break
            except TypeError as te:
                # 参数不支持，尝试下一种方式
                continue
            except Exception as e:
                # 其他错误，直接抛出
                raise e

        if websocket is None:
            raise Exception("所有连接方式都失败")

        async with websocket:
            print("已连接到BotShepherd代理")
            
            # 发送测试消息
            test_message = {
                "post_type": "meta_event",
                "meta_event_type": "lifecycle",
                "sub_type": "connect",
                "time": int(time.time()),
                "self_id": 3145443954
            }
            
            print(f"发送测试消息: {test_message}")
            await websocket.send(json.dumps(test_message))
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"收到响应: {response}")
            except asyncio.TimeoutError:
                print("等待响应超时")
            
            # 发送API调用测试
            api_message = {
                "action": "get_status",
                "params": {},
                "echo": "test_echo_123"
            }
            
            print(f"发送API调用: {api_message}")
            await websocket.send(json.dumps(api_message))
            
            # 等待API响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"收到API响应: {response}")
            except asyncio.TimeoutError:
                print("等待API响应超时")
            
            # 保持连接一段时间
            print("保持连接5秒...")
            await asyncio.sleep(5)
            
    except Exception as e:
        print(f"连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())
