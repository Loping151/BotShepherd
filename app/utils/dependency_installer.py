"""
依赖安装工具
处理运行时依赖缺失的自动安装
"""

import subprocess
import sys
import json
from pathlib import Path


def install_requirements(proxy: str = "") -> bool:
    """
    安装requirements.txt中的依赖

    Args:
        proxy: 代理地址（可选）

    Returns:
        安装是否成功
    """
    venv_path = Path("./venv")
    requirements_file = Path("./requirements.txt")

    if not venv_path.exists():
        print("虚拟环境不存在")
        return False

    if not requirements_file.exists():
        print("requirements.txt 文件不存在")
        return False

    try:
        # 获取pip路径
        if sys.platform == "win32":
            pip_path = venv_path / "Scripts" / "pip.exe"
        else:
            pip_path = venv_path / "bin" / "pip"

        if not pip_path.exists():
            print("pip未找到")
            return False

        # 构建安装命令
        cmd = [str(pip_path), "install", "-r", str(requirements_file)]
        if proxy:
            cmd.extend(["--proxy", proxy])

        print(f"正在{"使用代理" if proxy else ""}安装依赖包...如时间过长请尝试换源或手动安装")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("✅ 依赖包安装成功")
            return True
        else:
            print(f"❌ 依赖包安装失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 安装依赖包时出错: {e}")
        return False


def get_proxy_from_config() -> str:
    """
    从配置文件读取代理设置

    Returns:
        代理地址，如果读取失败返回空字符串
    """
    try:
        config_file = Path("./config/global_config.json")
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("proxy", "")
    except Exception:
        pass
    return ""


def try_import_with_install(import_func, max_retries: int = 3) -> tuple[bool, Exception]:
    """
    尝试导入模块，失败时自动安装依赖并重试

    Args:
        import_func: 导入函数
        max_retries: 最大重试次数

    Returns:
        (是否成功, 错误信息)
    """
    for attempt in range(max_retries):
        try:
            import_func()
            print("✅ 导入模块成功")
            return True, None
        except ImportError as e:
            print(f"❌ 导入模块失败 (尝试 {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                # 尝试安装依赖
                proxy = get_proxy_from_config()
                if install_requirements(proxy):
                    print("正在重新尝试导入...")
                    continue
                else:
                    print("依赖安装失败，停止重试")
                    return False, e
            else:
                # 最后一次尝试失败
                return False, e

    return False, None
