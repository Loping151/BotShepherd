#!/usr/bin/env python3
"""
BotShepherd - WebSocket代理管理系统
主程序入口
"""

import asyncio
import threading
import signal
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config_manager import ConfigManager
from app.websocket_proxy import SuperWebSocketProxy
from app.web_api import WebAPI
from app.global_config import GlobalConfigManager
from app.bot_config import BotConfigManager
from app.database import DatabaseManager


class BotShepherd:
    """BotShepherd主应用类"""

    def __init__(self):
        # 配置管理器
        self.connection_config_manager = ConfigManager()  # 连接配置
        self.global_config_manager = GlobalConfigManager()  # 全局配置
        self.bot_config_manager = BotConfigManager()  # Bot配置

        # 数据库管理器
        self.database_manager = DatabaseManager(self.global_config_manager.get_config().database)

        # WebSocket代理
        self.websocket_proxy = SuperWebSocketProxy(
            self.connection_config_manager,
            self.global_config_manager,
            self.bot_config_manager,
            self.database_manager
        )

        # Web API
        self.web_api = WebAPI(self.connection_config_manager, self.websocket_proxy)

        self.running = False
        self.web_thread = None

    def start_web_server(self):
        """在单独线程中启动Web服务器"""
        def run_web():
            self.web_api.run(host='0.0.0.0', port=5000, debug=False)

        self.web_thread = threading.Thread(target=run_web, daemon=True)
        self.web_thread.start()
        print("[*] Web UI started on http://localhost:5000")

    async def start_proxy_servers(self):
        """启动所有启用的代理服务器"""
        settings = self.config_manager.get_settings()
        if settings.get("auto_start", True):
            print("[*] Starting enabled proxy servers...")
            await self.websocket_proxy.start_all_enabled_servers()
        else:
            print("[*] Auto-start disabled, proxy servers not started")

    async def run(self):
        """运行主程序"""
        self.running = True

        print("="*50)
        print("BotShepherd - WebSocket代理管理系统")
        print("="*50)

        # 启动Web服务器
        self.start_web_server()

        # 启动代理服务器
        await self.start_proxy_servers()

        print("[*] System started successfully!")
        print("[*] Web UI: http://localhost:5000")
        print("[*] Press Ctrl+C to stop")

        # 保持程序运行
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await self.shutdown()

    async def shutdown(self):
        """关闭系统"""
        print("\n[*] Shutting down BotShepherd...")
        self.running = False

        # 停止所有代理服务器
        await self.websocket_proxy.stop_all_servers()

        print("[*] BotShepherd stopped.")

    def signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n[*] Received signal {signum}")
        asyncio.create_task(self.shutdown())


def main():
    """主函数"""
    app = BotShepherd()

    # 设置信号处理器
    signal.signal(signal.SIGINT, app.signal_handler)
    signal.signal(signal.SIGTERM, app.signal_handler)

    try:
        # 运行主程序
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\n[*] Program interrupted by user")
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()