#!/usr/bin/env python3
"""
WebSocket客户端测试脚本
用于测试BotShepherd的WebSocket代理功能
"""

import asyncio
import websockets
import json
import sys

async def test_client():
    """测试客户端连接"""
    uri = "ws://localhost:2538/OneBotv11"
    
    try:
        print(f"连接到 {uri}...")
        async with websockets.connect(uri) as websocket:
            print("连接成功！")
            
            # 发送测试消息
            test_message = {
                "action": "get_status",
                "params": {},
                "echo": "test_echo_123"
            }
            
            print(f"发送消息: {json.dumps(test_message, ensure_ascii=False)}")
            await websocket.send(json.dumps(test_message))
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"收到响应: {response}")
            except asyncio.TimeoutError:
                print("等待响应超时")
            
            # 发送另一个测试消息
            test_message2 = {
                "action": "get_version_info",
                "params": {},
                "echo": "test_echo_456"
            }
            
            print(f"发送消息: {json.dumps(test_message2, ensure_ascii=False)}")
            await websocket.send(json.dumps(test_message2))
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"收到响应: {response}")
            except asyncio.TimeoutError:
                print("等待响应超时")
                
    except Exception as e:
        print(f"连接失败: {e}")

if __name__ == "__main__":
    print("BotShepherd WebSocket客户端测试")
    print("=" * 40)
    asyncio.run(test_client())
