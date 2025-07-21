#!/usr/bin/env python3
"""
BotShepherd 压力测试服务器
模拟napcat客户端向BotShepherd发送消息进行压力测试
"""

import asyncio
import websockets
import json
import time
import random
import argparse
from datetime import datetime
from typing import List, Dict, Any


class PressureTestServer:
    """压力测试服务器"""
    
    def __init__(self, 
                 server_url: str = "ws://localhost:5511",
                 bot_qq: str = "3145443954",
                 test_group: str = "1053786482",
                 test_user: str = "2408736708"):
        self.server_url = server_url
        self.bot_qq = bot_qq
        self.test_group = test_group
        self.test_user = test_user
        self.websocket = None
        self.running = False
        self.message_count = 0
        
    async def connect(self):
        """连接到BotShepherd服务器"""
        headers = {
            "User-Agent": "NapCat/1.0.0",
            "X-Self-Id": self.bot_qq,
            "X-Client-Role": "Universal",
            "Authorization": "Bearer test_token"
        }
        
        try:
            print(f"正在连接到 {self.server_url}...")
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
    
    async def send_lifecycle_message(self):
        """发送lifecycle消息初始化连接"""
        lifecycle_msg = {
            "time": int(time.time()),
            "self_id": int(self.bot_qq),
            "post_type": "meta_event",
            "meta_event_type": "lifecycle",
            "sub_type": "connect"
        }
        
        await self.websocket.send(json.dumps(lifecycle_msg))
        print("📡 已发送lifecycle消息")
    
    def get_test_messages(self) -> List[Dict[str, Any]]:
        """获取测试消息模板"""
        current_time = int(time.time())
        message_id = random.randint(100000, 999999)
        
        messages = [
            # 今日运势指令
            {
                "self_id": int(self.bot_qq),
                "user_id": int(self.test_user),
                "time": current_time,
                "message_id": message_id,
                "message_seq": message_id,
                "real_id": message_id,
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "group",
                "sender": {
                    "user_id": int(self.test_user),
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
                "group_id": int(self.test_group)
            },
            
            # ww指令测试
            {
                "self_id": int(self.bot_qq),
                "user_id": int(self.test_user),
                "time": current_time + 1,
                "message_id": message_id + 1,
                "message_seq": message_id + 1,
                "real_id": message_id + 1,
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "group",
                "sender": {
                    "user_id": int(self.test_user),
                    "nickname": "测试用户",
                    "card": "",
                    "role": "member"
                },
                "raw_message": "xw帮助",
                "font": 14,
                "sub_type": "normal",
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "xw帮助"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message",
                "group_id": int(self.test_group)
            },
            
            # 私聊消息测试
            {
                "self_id": int(self.bot_qq),
                "user_id": int(self.test_user),
                "time": current_time + 2,
                "message_id": message_id + 2,
                "message_seq": message_id + 2,
                "real_id": message_id + 2,
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "private",
                "sender": {
                    "user_id": int(self.test_user),
                    "nickname": "测试用户"
                },
                "raw_message": "#帮助",
                "font": 14,
                "sub_type": "friend",
                "message": [
                    {
                        "type": "text",
                        "data": {
                            "text": "#帮助"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message"
            },
            
            # @机器人的消息
            {
                "self_id": int(self.bot_qq),
                "user_id": int(self.test_user),
                "time": current_time + 3,
                "message_id": message_id + 3,
                "message_seq": message_id + 3,
                "real_id": message_id + 3,
                "real_seq": str(random.randint(10000, 99999)),
                "message_type": "group",
                "sender": {
                    "user_id": int(self.test_user),
                    "nickname": "测试用户",
                    "card": "",
                    "role": "member"
                },
                "raw_message": f"[CQ:at,qq={self.bot_qq}] 你好",
                "font": 14,
                "sub_type": "normal",
                "message": [
                    {
                        "type": "at",
                        "data": {
                            "qq": self.bot_qq
                        }
                    },
                    {
                        "type": "text",
                        "data": {
                            "text": " 你好"
                        }
                    }
                ],
                "message_format": "array",
                "post_type": "message",
                "group_id": int(self.test_group)
            },
            
            # 拍一拍通知
            {
                "time": current_time + 4,
                "self_id": int(self.bot_qq),
                "post_type": "notice",
                "notice_type": "notify",
                "sub_type": "poke",
                "target_id": int(self.bot_qq),
                "user_id": int(self.test_user),
                "group_id": int(self.test_group),
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
        ]
        
        return messages
    
    async def send_pressure_test(self, rate: float = 1.0, duration: int = 60):
        """发送压力测试消息
        
        Args:
            rate: 每秒发送消息数
            duration: 测试持续时间（秒）
        """
        print(f"🚀 开始压力测试: {rate} 消息/秒, 持续 {duration} 秒")
        
        self.running = True
        start_time = time.time()
        interval = 1.0 / rate if rate > 0 else 1.0
        
        try:
            while self.running and (time.time() - start_time) < duration:
                messages = self.get_test_messages()
                
                # 随机选择一个消息发送
                message = random.choice(messages)
                
                await self.websocket.send(json.dumps(message))
                self.message_count += 1
                
                if self.message_count % 10 == 0:
                    elapsed = time.time() - start_time
                    current_rate = self.message_count / elapsed
                    print(f"📊 已发送 {self.message_count} 条消息, 当前速率: {current_rate:.2f} 消息/秒")
                
                await asyncio.sleep(interval)
                
        except Exception as e:
            print(f"❌ 发送消息时出错: {e}")
        
        elapsed = time.time() - start_time
        avg_rate = self.message_count / elapsed if elapsed > 0 else 0
        print(f"✅ 压力测试完成! 总计发送 {self.message_count} 条消息, 平均速率: {avg_rate:.2f} 消息/秒")
    
    async def run_test(self, rate: float = 1.0, duration: int = 60):
        """运行完整的压力测试"""
        if not await self.connect():
            return
        
        try:
            # 发送lifecycle消息
            await self.send_lifecycle_message()
            
            # 等待一秒让连接稳定
            await asyncio.sleep(1)
            
            # 开始压力测试
            await self.send_pressure_test(rate, duration)
            
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断测试")
            self.running = False
        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
                print("🔌 连接已关闭")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BotShepherd 压力测试服务器')
    parser.add_argument('--url', default='ws://localhost:5666', help='BotShepherd服务器地址')
    parser.add_argument('--bot-qq', default='666666', help='机器人QQ号')
    parser.add_argument('--group', default='953590652', help='测试群号')
    parser.add_argument('--user', default='953590652', help='测试用户QQ号')
    parser.add_argument('--rate', type=float, default=1.0, help='发送速率（消息/秒）')
    parser.add_argument('--duration', type=int, default=60, help='测试持续时间（秒）')
    
    args = parser.parse_args()
    
    print("🤖 BotShepherd 压力测试服务器")
    print(f"服务器地址: {args.url}")
    print(f"机器人QQ: {args.bot_qq}")
    print(f"测试群组: {args.group}")
    print(f"测试用户: {args.user}")
    print("-" * 50)
    
    server = PressureTestServer(
        server_url=args.url,
        bot_qq=args.bot_qq,
        test_group=args.group,
        test_user=args.user
    )
    
    await server.run_test(args.rate, args.duration)


if __name__ == "__main__":
    asyncio.run(main())
