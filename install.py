#!/usr/bin/env python3
"""
BotShepherd 安装脚本
自动安装依赖并进行基础配置
"""

import sys
import subprocess
import os
from pathlib import Path
import asyncio
            
def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    
    print(f"✅ Python版本检查通过: {sys.version}")
    return True

def install_requirements():
    """安装依赖包"""
    print("\n📦 开始安装依赖包...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print("❌ 错误: requirements.txt 文件不存在")
        return False
    
    try:
        # 升级pip
        print("⬆️ 升级pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # 安装依赖
        print("📥 安装项目依赖...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
        
        print("✅ 依赖安装完成")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装依赖失败: {e}")
        return False

def create_directories():
    """创建必要的目录"""
    print("\n📁 创建项目目录...")
    
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
    
    project_root = Path(__file__).parent
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")
    
    print("✅ 目录创建完成")

def check_dependencies():
    """检查依赖是否正确安装"""
    print("\n🔍 检查依赖安装状态...")
    
    required_packages = [
        "websockets",
        "flask", 
        "flask_cors",
        "sqlalchemy",
        "aiosqlite",
        "waitress",
        "dateutil",
        "pydantic",
        "watchdog"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少以下依赖包: {', '.join(missing_packages)}")
        return False
    
    print("✅ 所有依赖检查通过")
    return True

def run_initial_setup():
    """运行初始设置"""
    print("\n⚙️ 运行初始设置...")
    
    try:
        # 导入并运行初始化
        sys.path.insert(0, str(Path(__file__).parent))
        
        from app.config.config_manager import ConfigManager
        from app.database.database_manager import DatabaseManager
        
        # 初始化配置管理器
        config_manager = ConfigManager()
        asyncio.run(config_manager.initialize())
        
        # 检查是否需要初始化配置
        if not config_manager.config_exists():
            print("📝 创建初始配置...")
            asyncio.run(config_manager.setup_initial_config())
        else:
            print("✅ 配置文件已存在")
        
        # 初始化数据库
        print("🗄️ 初始化数据库...")
        db_manager = DatabaseManager(config_manager)
        asyncio.run(db_manager.initialize())
        
        print("✅ 初始设置完成")
        return True
        
    except Exception as e:
        print(f"❌ 初始设置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_next_steps():
    """显示后续步骤"""
    print("\n🎉 安装完成！")
    print("\n📋 后续步骤:")
    print("1. 编辑配置文件:")
    print("   - config/global_config.json (全局配置)")
    print("   - config/connections/default.json (连接配置)")
    print("\n2. 启动系统:")
    print("   python main.py")
    print("\n3. 访问Web管理界面:")
    print("   http://localhost:8080")
    print("   默认用户名/密码: admin/admin")
    print("\n4. 查看帮助:")
    print("   python main.py --help")
    print("\n📖 更多信息请查看 README.md")

def main():
    """主函数"""
    print("🤖 BotShepherd 安装程序")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        sys.exit(1)
    
    # 安装依赖
    if not install_requirements():
        print("\n❌ 安装失败，请检查错误信息")
        sys.exit(1)
    
    # 创建目录
    create_directories()
    
    # 检查依赖
    if not check_dependencies():
        print("\n⚠️ 部分依赖未正确安装，但可以尝试继续")
    
    # 运行初始设置
    if not run_initial_setup():
        print("\n⚠️ 初始设置失败，请手动配置")
    
    # 显示后续步骤
    show_next_steps()

if __name__ == "__main__":
    main()
