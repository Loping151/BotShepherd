#!/usr/bin/env python3
"""
BotShepherd 测试脚本
发送特定的测试消息到BotShepherd
"""

import asyncio
import websockets
import json
import time
import random
from datetime import datetime


class BotShepherdTestClient:
    """BotShepherd测试客户端"""
    
    # 固定的测试QQ号
    BOT_QQ = "3145443954"  # 机器人QQ号
    TEST_USER_QQ = "2408736708"  # 测试用户QQ号
    TEST_GROUP = "1053786482"  # 测试群号
    
    def __init__(self, server_url: str = "ws://localhost:5511"):
        self.server_url = server_url
        self.websocket = None
        
    async def connect(self):
        """连接到BotShepherd"""
        headers = {
            "User-Agent": "NapCat/1.0.0",
            "X-Self-Id": self.BOT_QQ,
            "X-Client-Role": "Universal",
            "Authorization": "Bearer test_token"
        }
        
        try:
            print(f"🔗 连接到 {self.server_url}...")
            self.websocket = await websockets.connect(
                self.server_url,
                additional_headers=headers,
                max_size=None,
                max_queue=None,
                ping_interval=30,
                ping_timeout=10
            )
            print("✅ 连接成功！")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def send_lifecycle(self):
        """发送lifecycle消息"""
        lifecycle_msg = {
            "time": int(time.time()),
            "self_id": int(self.BOT_QQ),
            "post_type": "meta_event",
            "meta_event_type": "lifecycle",
            "sub_type": "connect"
        }
        
        await self.websocket.send(json.dumps(lifecycle_msg))
        print("📡 已发送lifecycle消息")
    
    async def send_message(self, message_data: dict):
        """发送消息"""
        await self.websocket.send(json.dumps(message_data))
        print(f"📤 已发送消息: {message_data.get('raw_message', '未知消息')}")
    
    async def run_tests(self):
        """运行所有测试"""
        if not await self.connect():
            return
        
        try:
            # 发送lifecycle消息
            await self.send_lifecycle()
            await asyncio.sleep(1)
            
            print("\n🧪 开始发送测试消息...")
            
            # 测试1: 今日运势指令
            print("\n1️⃣ 测试今日运势指令")
            fortune_msg = {
                "self_id": int(self.BOT_QQ),
                "user_id": int(self.TEST_USER_QQ),
                "time": int(time.time()),
                "message_id": random.randint(100000, 999999),
                "message_seq": random.randint(100000, 999999),
                "real_id": random.randint(100000, 999999),
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "group",
                "sender": {
                    "user_id": int(self.TEST_USER_QQ),
                    "nickname": "测试用户",
                    "card": "",
                    "role": "member"
                },
                "raw_message": "今日运势",
                "font": 14,
                "sub_type": "normal",
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "今日运势"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message",
                "group_id": int(self.TEST_GROUP)
            }
            await self.send_message(fortune_msg)
            await asyncio.sleep(2)
            
            # 测试2: ww指令
            print("\n2️⃣ 测试ww指令")
            ww_msg = {
                "self_id": int(self.BOT_QQ),
                "user_id": int(self.TEST_USER_QQ),
                "time": int(time.time()),
                "message_id": random.randint(100000, 999999),
                "message_seq": random.randint(100000, 999999),
                "real_id": random.randint(100000, 999999),
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "group",
                "sender": {
                    "user_id": int(self.TEST_USER_QQ),
                    "nickname": "测试用户",
                    "card": "",
                    "role": "member"
                },
                "raw_message": "ww帮助",
                "font": 14,
                "sub_type": "normal",
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "ww帮助"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message",
                "group_id": int(self.TEST_GROUP)
            }
            await self.send_message(ww_msg)
            await asyncio.sleep(2)
            
            # 测试3: BotShepherd内置指令
            print("\n3️⃣ 测试BotShepherd内置指令")
            bs_help_msg = {
                "self_id": int(self.BOT_QQ),
                "user_id": int(self.TEST_USER_QQ),
                "time": int(time.time()),
                "message_id": random.randint(100000, 999999),
                "message_seq": random.randint(100000, 999999),
                "real_id": random.randint(100000, 999999),
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "group",
                "sender": {
                    "user_id": int(self.TEST_USER_QQ),
                    "nickname": "测试用户",
                    "card": "",
                    "role": "member"
                },
                "raw_message": "bs帮助",
                "font": 14,
                "sub_type": "normal",
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "bs帮助"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message",
                "group_id": int(self.TEST_GROUP)
            }
            await self.send_message(bs_help_msg)
            await asyncio.sleep(2)
            
            # 测试4: 私聊消息
            print("\n4️⃣ 测试私聊消息")
            private_msg = {
                "self_id": int(self.BOT_QQ),
                "user_id": int(self.TEST_USER_QQ),
                "time": int(time.time()),
                "message_id": random.randint(100000, 999999),
                "message_seq": random.randint(100000, 999999),
                "real_id": random.randint(100000, 999999),
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "private",
                "sender": {
                    "user_id": int(self.TEST_USER_QQ),
                    "nickname": "测试用户"
                },
                "raw_message": "你好，这是私聊测试",
                "font": 14,
                "sub_type": "friend",
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "你好，这是私聊测试"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message"
            }
            await self.send_message(private_msg)
            await asyncio.sleep(2)
            
            # 测试5: @机器人消息
            print("\n5️⃣ 测试@机器人消息")
            at_msg = {
                "self_id": int(self.BOT_QQ),
                "user_id": int(self.TEST_USER_QQ),
                "time": int(time.time()),
                "message_id": random.randint(100000, 999999),
                "message_seq": random.randint(100000, 999999),
                "real_id": random.randint(100000, 999999),
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "group",
                "sender": {
                    "user_id": int(self.TEST_USER_QQ),
                    "nickname": "测试用户",
                    "card": "",
                    "role": "member"
                },
                "raw_message": f"[CQ:at,qq={self.BOT_QQ}] 你好机器人",
                "font": 14,
                "sub_type": "normal",
                "message": [
                    {
                        "type": "at",
                        "data": {
                            "qq": self.BOT_QQ
                        }
                    },
                    {
                        "type": "text",
                        "data": {
                            "text": " 你好机器人"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message",
                "group_id": int(self.TEST_GROUP)
            }
            await self.send_message(at_msg)
            await asyncio.sleep(2)
            
            # 测试6: 拍一拍通知
            print("\n6️⃣ 测试拍一拍通知")
            poke_msg = {
                "time": int(time.time()),
                "self_id": int(self.BOT_QQ),
                "post_type": "notice",
                "notice_type": "notify",
                "sub_type": "poke",
                "target_id": int(self.BOT_QQ),
                "user_id": int(self.TEST_USER_QQ),
                "group_id": int(self.TEST_GROUP),
                "raw_info": [
                    {
                        "col": "1",
                        "nm": "",
                        "type": "qq",
                        "uid": "test_uid_1"
                    },
                    {
                        "txt": "戳了戳",
                        "type": "nor"
                    },
                    {
                        "col": "1",
                        "nm": "",
                        "tp": "0",
                        "type": "qq",
                        "uid": "test_uid_2"
                    },
                    {
                        "txt": "的头",
                        "type": "nor"
                    }
                ]
            }
            await self.send_message(poke_msg)
            await asyncio.sleep(2)
            
            print("\n✅ 所有测试消息发送完成！")
            
            # 保持连接一段时间以接收响应
            print("⏳ 等待响应中...")
            await asyncio.sleep(10)
            
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断测试")
        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
                print("🔌 连接已关闭")


async def main():
    """主函数"""
    print("🤖 BotShepherd 测试脚本")
    print(f"机器人QQ: {BotShepherdTestClient.BOT_QQ}")
    print(f"测试用户QQ: {BotShepherdTestClient.TEST_USER_QQ}")
    print(f"测试群号: {BotShepherdTestClient.TEST_GROUP}")
    print("-" * 50)
    
    client = BotShepherdTestClient()
    await client.run_tests()


if __name__ == "__main__":
    asyncio.run(main())
