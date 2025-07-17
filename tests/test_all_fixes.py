#!/usr/bin/env python3
"""
BotShepherd 修复验证测试脚本
验证所有修复的问题是否正常工作
"""

import asyncio
import websockets
import json
import requests
import time
import subprocess
import signal
import os
import sys

def test_webui_apis():
    """测试WebUI API"""
    print("🌐 测试WebUI API...")
    
    try:
        # 测试登录
        login_data = {"username": "admin", "password": "admin"}
        session = requests.Session()
        
        # 登录
        response = session.post("http://localhost:5000/login", data=login_data)
        if response.status_code == 200:
            print("  ✅ 登录成功")
        else:
            print(f"  ❌ 登录失败: {response.status_code}")
            return False
        
        # 测试状态API
        response = session.get("http://localhost:5000/api/status")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 状态API正常: {data}")
        else:
            print(f"  ❌ 状态API失败: {response.status_code}")
            return False
        
        # 测试连接API
        response = session.get("http://localhost:5000/api/connections")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 连接API正常: 找到 {len(data)} 个连接配置")
        else:
            print(f"  ❌ 连接API失败: {response.status_code}")
            return False
        
        # 测试统计API
        response = session.get("http://localhost:5000/api/statistics")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 统计API正常: {data.get('total_messages', 0)} 条消息")
        else:
            print(f"  ❌ 统计API失败: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ WebUI API测试失败: {e}")
        return False

async def test_websocket_proxy():
    """测试WebSocket代理功能"""
    print("🔌 测试WebSocket代理...")
    
    try:
        uri = "ws://localhost:2538/OneBotv11"
        async with websockets.connect(uri) as websocket:
            print("  ✅ WebSocket连接成功")
            
            # 发送测试消息
            test_message = {
                "action": "get_version_info",
                "params": {},
                "echo": "test_proxy_123"
            }
            
            await websocket.send(json.dumps(test_message))
            print("  ✅ 消息发送成功")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                if data.get("echo") == "test_proxy_123":
                    print(f"  ✅ 代理响应正常: {data.get('data', {}).get('app_name', 'Unknown')}")
                    return True
                else:
                    print(f"  ❌ 响应echo不匹配: {data}")
                    return False
            except asyncio.TimeoutError:
                print("  ❌ 响应超时")
                return False
                
    except Exception as e:
        print(f"  ❌ WebSocket代理测试失败: {e}")
        return False

def test_signal_handling():
    """测试信号处理"""
    print("📡 测试信号处理...")
    
    try:
        # 启动BotShepherd进程
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待启动
        time.sleep(3)
        
        if process.poll() is not None:
            print("  ❌ 进程启动失败")
            return False
        
        print("  ✅ 进程启动成功")
        
        # 发送SIGINT信号
        process.send_signal(signal.SIGINT)
        
        # 等待进程结束
        try:
            process.wait(timeout=10)
            print("  ✅ 信号处理正常，进程已关闭")
            return True
        except subprocess.TimeoutExpired:
            print("  ❌ 进程未能在10秒内关闭")
            process.kill()
            return False
            
    except Exception as e:
        print(f"  ❌ 信号处理测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🧪 BotShepherd 修复验证测试")
    print("=" * 50)
    
    results = {
        "webui": False,
        "websocket": False,
        "signal": False
    }
    
    # 确保BotShepherd和模拟服务器正在运行
    print("🚀 请确保以下服务正在运行:")
    print("   1. python main.py")
    print("   2. python mock_target_server.py")
    print()
    
    input("按Enter键开始测试...")
    
    # 测试WebUI API
    results["webui"] = test_webui_apis()
    print()
    
    # 测试WebSocket代理
    results["websocket"] = await test_websocket_proxy()
    print()
    
    # 测试信号处理（这会重启服务）
    print("⚠️  信号处理测试会重启服务，请稍后...")
    results["signal"] = test_signal_handling()
    print()
    
    # 输出结果
    print("📊 测试结果汇总:")
    print("=" * 30)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name.upper()}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有修复验证通过！BotShepherd运行正常。")
    else:
        print("⚠️  部分测试失败，请检查相关功能。")

if __name__ == "__main__":
    asyncio.run(main())
