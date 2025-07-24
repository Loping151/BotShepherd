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
import subprocess
import venv
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.config.config_manager import ConfigManager
from app.database.database_manager import DatabaseManager
from app.server.proxy_server import ProxyServer
from app.web_api.web_server import WebServer
from app.utils.logger import BSLogger
from app.commands import initialize_builtin_commands, load_plugins
from app import __version__, __github__, __description__


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
            self.logger = BSLogger(self.config_manager.get_global_config())
            self.config_manager.set_logger(self.logger)
            self.logger.info(f"BotShepherd v{__version__} 正在启动...")
            self.logger.info(f"仓库：{__github__}")
            self.logger.info(f"{__description__}")

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
                logger=self.logger,
                port=self.config_manager.get_global_config().get("web_port", 5100)
            )

            self.logger.info("系统组件初始化完成")
            return True

        except Exception as e:
            import traceback
            traceback.print_exc()
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

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print(f"当前版本: {sys.version}")
        return False

    print(f"✅ Python版本检查通过: {sys.version}")
    return True

def create_venv_and_install():
    """创建虚拟环境并安装依赖"""
    venv_path = Path("./venv")

    if not venv_path.exists():
        print("📦 创建虚拟环境...")
        try:
            import venv
            venv.create(venv_path, with_pip=True)
            print("✅ 虚拟环境创建完成")
        except Exception as e:
            print(f"❌ 创建虚拟环境失败: {e}")
            return False
    else:
        print("✅ 虚拟环境已存在")

    # 确定pip路径
    if sys.platform == "win32":
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        pip_path = venv_path / "bin" / "pip"

    # 安装依赖
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print("📥 安装项目依赖...")
        try:
            subprocess.check_call([str(pip_path), "install", "--upgrade", "pip"])
            subprocess.check_call([str(pip_path), "install", "-r", str(requirements_file)])
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装依赖失败: {e}")
            return False
    else:
        print("❌ requirements.txt 文件不存在")
        return False

def create_directories():
    """创建必要的目录"""
    print("📁 创建项目目录...")

    directories = [
        "config",
        "config/connections",
        "config/account",
        "config/group",
        "data",
        "logs",
        "templates",
        "static"
    ]

    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")

    print("✅ 目录创建完成")

async def setup_initial_config():
    """初始化配置和环境"""
    print("🤖 BotShepherd 初始化程序")
    print("=" * 50)

    # 检查Python版本
    if not check_python_version():
        sys.exit(1)

    # 创建虚拟环境并安装依赖
    if not create_venv_and_install():
        print("\n❌ 环境设置失败，请检查错误信息")
        sys.exit(1)

    # 创建目录
    create_directories()

    # 初始化配置
    print("\n⚙️ 初始化配置文件...")
    try:
        config_manager = ConfigManager()
        await config_manager.initialize()

        if not config_manager.config_exists():
            print("📝 创建初始配置...")
            await config_manager.setup_initial_config()
        else:
            print("✅ 配置文件已存在")

        # 初始化数据库
        print("🗄️ 初始化数据库...")
        db_manager = DatabaseManager(config_manager)
        await db_manager.initialize()
        await db_manager.close()

        print("\n🎉 初始化完成！")
        print("\n📋 后续步骤:")
        print("1. 编辑配置文件:")
        print("   - config/global_config.json (全局配置)")
        print("   - config/connections/default.json (连接配置)")
        print("\n2. 启动系统:")
        if Path("./venv").exists():
            if sys.platform == "win32":
                print("   .\\venv\\Scripts\\python.exe main.py")
            else:
                print("   ./venv/bin/python main.py")
        else:
            print("   python main.py")
        print("\n3. 访问Web管理界面:")
        print("   http://localhost:5100")
        print("   默认用户名/密码: admin/admin")
        print("\n📖 更多信息请查看 README.md")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def check_config_exists():
    """检查配置文件是否存在"""
    config_file = Path("config/global_config.json")
    return config_file.exists()

# 全局应用实例
app_instance = None
    
async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BotShepherd - 星星花与牧羊人')
    parser.add_argument('--setup', action='store_true', help='初始化配置和环境')

    args = parser.parse_args()

    if args.setup:
        await setup_initial_config()
        return

    # 检查配置文件是否存在
    if not check_config_exists():
        print("❌ 错误: 配置文件不存在")
        print("请先运行初始化命令: python main.py --setup")
        print("或者如果使用虚拟环境: ./venv/bin/python main.py --setup")
        sys.exit(1)

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
