#!/usr/bin/env python3
"""
BotShepherd - Bot牧羊人
一个强大的OneBot v11协议WebSocket代理和管理系统

主程序入口文件
"""

import asyncio
import argparse
import sys
import os
import signal
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.config.config_manager import ConfigManager
from app.database.database_manager import DatabaseManager
from app.websocket_proxy.proxy_server import ProxyServer
from app.web_api.web_server import WebServer
from app.utils.logger import setup_logger
from app.commands import initialize_builtin_commands, load_plugins


class BotShepherd:
    """BotShepherd主应用类"""

    def __init__(self):
        self.config_manager = None
        self.database_manager = None
        self.proxy_server = None
        self.web_server = None
        self.logger = None
        self.running = False
        self.shutdown_event = None
        self._shutdown_in_progress = False
        
    async def initialize(self):
        """初始化系统组件"""
        try:
            # 初始化shutdown事件
            self.shutdown_event = asyncio.Event()

            # 初始化配置管理器
            self.config_manager = ConfigManager()
            await self.config_manager.initialize()

            # 设置日志系统
            self.logger = setup_logger(self.config_manager.get_global_config())
            self.logger.info("BotShepherd正在启动...")

            # 初始化数据库
            self.database_manager = DatabaseManager(self.config_manager)
            await self.database_manager.initialize()

            # 初始化WebSocket代理服务器
            self.proxy_server = ProxyServer(
                config_manager=self.config_manager,
                database_manager=self.database_manager,
                logger=self.logger
            )
            
            # 初始化指令系统
            initialize_builtin_commands(self.logger)
            load_plugins(self.logger)

            # 初始化Web服务器
            self.web_server = WebServer(
                config_manager=self.config_manager,
                database_manager=self.database_manager,
                proxy_server=self.proxy_server,
                logger=self.logger
            )

            self.logger.info("系统组件初始化完成")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"系统初始化失败: {e}")
            else:
                print(f"系统初始化失败: {e}")
            return False
    
    async def start(self):
        """启动所有服务"""
        if not await self.initialize():
            return False

        try:
            self.running = True
            self.logger.info("启动BotShepherd服务...")

            # 启动Web服务器
            web_task = asyncio.create_task(self.web_server.start())

            # 启动WebSocket代理服务器
            proxy_task = asyncio.create_task(self.proxy_server.start())

            self.logger.info("BotShepherd启动完成")
            self.logger.info("Web管理界面: http://localhost:5000")
            self.logger.info("WebSocket代理服务已就绪")

            # 等待关闭信号或服务异常
            done, pending = await asyncio.wait(
                [web_task, proxy_task, asyncio.create_task(self.shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )

            # 取消未完成的任务
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            self.logger.error(f"服务启动失败: {e}")
            return False

    def shutdown(self):
        """触发关闭"""
        if self.shutdown_event and not self.shutdown_event.is_set():
            # 在当前事件循环中设置关闭事件
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(self.shutdown_event.set)
                else:
                    self.shutdown_event.set()
            except RuntimeError:
                # 如果没有事件循环，直接设置
                self.shutdown_event.set()

    async def stop(self):
        """停止所有服务"""
        if not self.running or self._shutdown_in_progress:
            return

        self._shutdown_in_progress = True
        self.running = False

        if self.logger:
            self.logger.info("正在停止BotShepherd服务...")
        else:
            print("正在停止BotShepherd服务...")

        try:
            # 触发shutdown事件
            if self.shutdown_event:
                self.shutdown_event.set()

            # 停止各个服务
            if self.proxy_server:
                await self.proxy_server.stop()
            print("WebSocket代理服务器已停止")

            if self.web_server:
                await self.web_server.stop()
            print("Web服务器已停止")

            if self.database_manager:
                await self.database_manager.close()
            print("数据库连接已关闭")

            if self.logger:
                self.logger.info("BotShepherd已停止")
            else:
                print("BotShepherd已停止")

        except Exception as e:
            if self.logger:
                self.logger.error(f"停止服务时出错: {e}")
            else:
                print(f"停止服务时出错: {e}")
        finally:
            self._shutdown_in_progress = False

async def setup_initial_config():
    """初始化配置文件"""
    print("正在初始化BotShepherd配置...")
    
    config_manager = ConfigManager()
    await config_manager.setup_initial_config()
    
    print("配置初始化完成！")
    print("请编辑config/目录下的配置文件，然后运行: python main.py")

async def run_system_tests():
    """运行系统测试"""
    print("🧪 开始运行系统测试...")

    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }

    # 测试1: 配置系统
    print("\n1️⃣ 测试配置系统...")
    try:
        from app.config.config_manager import ConfigManager
        config_manager = ConfigManager()

        if config_manager.config_exists():
            global_config = config_manager.get_global_config()
            if global_config and "superusers" in global_config:
                print("  ✅ 配置系统正常")
                test_results["passed"] += 1
            else:
                print("  ❌ 配置格式错误")
                test_results["failed"] += 1
                test_results["errors"].append("配置格式错误")
        else:
            print("  ⚠️ 配置文件不存在，请先运行 --setup")
            test_results["failed"] += 1
            test_results["errors"].append("配置文件不存在")
    except Exception as e:
        print(f"  ❌ 配置系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        test_results["failed"] += 1
        test_results["errors"].append(f"配置系统错误: {e}")

    # 测试2: 数据库系统
    print("\n2️⃣ 测试数据库系统...")
    try:
        from app.database.database_manager import DatabaseManager
        db_manager = DatabaseManager(config_manager)
        await db_manager.initialize()

        # 测试数据库连接
        db_info = await db_manager.get_database_info()
        if db_info and "database_path" in db_info:
            print("  ✅ 数据库系统正常")
            test_results["passed"] += 1
        else:
            print("  ❌ 数据库初始化失败")
            test_results["failed"] += 1
            test_results["errors"].append("数据库初始化失败")

        await db_manager.close()
    except Exception as e:
        print(f"  ❌ 数据库系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        test_results["failed"] += 1
        test_results["errors"].append(f"数据库系统错误: {e}")

    # 测试3: OneBot v11协议解析
    print("\n3️⃣ 测试OneBot v11协议解析...")
    try:
        from app.onebotv11 import EventParser
        from app.onebotv11.models import PrivateMessageEvent

        # 测试消息解析
        test_message = {
            "time": 1234567890,
            "self_id": 123456,
            "post_type": "message",
            "message_type": "private",
            "sub_type": "friend",
            "message_id": 1,
            "user_id": 789012,
            "message": [{"type": "text", "data": {"text": "测试消息"}}],
            "raw_message": "测试消息",
            "font": 0,
            "sender": {"user_id": 789012, "nickname": "测试用户"}
        }

        event = EventParser.parse_event_data(test_message)
        if isinstance(event, PrivateMessageEvent):
            print("  ✅ OneBot v11协议解析正常")
            test_results["passed"] += 1
        else:
            print("  ❌ 消息解析失败")
            test_results["failed"] += 1
            test_results["errors"].append("消息解析失败")
    except Exception as e:
        print(f"  ❌ OneBot v11协议测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"OneBot v11协议错误: {e}")

    # 测试4: 指令系统
    print("\n4️⃣ 测试指令系统...")
    try:
        from app.commands import command_registry

        if len(command_registry.commands) > 0:
            help_command = command_registry.get_command("帮助")
            if help_command:
                print("  ✅ 指令系统正常")
                test_results["passed"] += 1
            else:
                print("  ❌ 基础指令缺失")
                test_results["failed"] += 1
                test_results["errors"].append("基础指令缺失")
        else:
            print("  ❌ 指令注册失败")
            test_results["failed"] += 1
            test_results["errors"].append("指令注册失败")
    except Exception as e:
        print(f"  ❌ 指令系统测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"指令系统错误: {e}")

    # 测试5: Web服务器
    print("\n5️⃣ 测试Web服务器...")
    try:
        from app.web_api.web_server import WebServer
        import logging

        # 创建简单的logger用于测试
        logger = logging.getLogger("test")

        # 简单测试Web服务器初始化
        web_server = WebServer(None, None, None, logger)
        if web_server.app:
            print("  ✅ Web服务器初始化正常")
            test_results["passed"] += 1
        else:
            print("  ❌ Web服务器初始化失败")
            test_results["failed"] += 1
            test_results["errors"].append("Web服务器初始化失败")
    except Exception as e:
        print(f"  ❌ Web服务器测试失败: {e}")
        test_results["failed"] += 1
        test_results["errors"].append(f"Web服务器错误: {e}")

    # 输出测试结果
    print("\n" + "="*50)
    print("📊 测试结果汇总:")
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")

    if test_results["errors"]:
        print("\n🔍 错误详情:")
        for i, error in enumerate(test_results["errors"], 1):
            print(f"  {i}. {error}")

    if test_results["failed"] == 0:
        print("\n🎉 所有测试通过！系统运行正常。")
    else:
        print(f"\n⚠️ 有 {test_results['failed']} 个测试失败，请检查系统配置。")

    print("\n💡 提示:")
    print("- 如果配置文件不存在，请运行: python main.py --setup")
    print("- 如果数据库有问题，请检查 ./data 目录权限")
    print("- 更多帮助请查看 README.md")

# 全局应用实例
app_instance = None
    
async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BotShepherd - 星星花与牧羊人')
    parser.add_argument('--setup', action='store_true', help='初始化配置文件')
    parser.add_argument('--test', action='store_true', help='运行系统测试')
    
    args = parser.parse_args()
    
    if args.setup:
        await setup_initial_config()
        return
    
    if args.test:
        await run_system_tests()
        return

    # 创建并启动BotShepherd
    global app_instance
    app_instance = BotShepherd()

    try:
        await app_instance.start()
    except KeyboardInterrupt:
        print("\n收到中断信号")
    except Exception as e:
        print(f"运行时错误: {e}")
    finally:
        await app_instance.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBotShepherd已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)
