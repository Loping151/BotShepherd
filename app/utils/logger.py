"""
日志系统工具
"""

import logging
import logging.handlers
import os
from datetime import datetime, timedelta
from pathlib import Path
import json

def setup_logger(global_config=None):
    """设置日志系统"""
    
    # 默认配置
    log_config = {
        "level": "INFO",
        "file_rotation": True,
        "keep_days": 7,
        "max_file_size": "10MB"
    }
    
    # 从全局配置中获取日志配置
    if global_config and "logging" in global_config:
        log_config.update(global_config["logging"])
    
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建主日志器
    logger = logging.getLogger("BotShepherd")
    logger.setLevel(getattr(logging, log_config["level"].upper()))
    
    # 清除现有处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    if log_config["file_rotation"]:
        # 使用时间轮转的文件处理器
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_dir / "botshepherd.log",
            when="midnight",
            interval=1,
            backupCount=log_config["keep_days"],
            encoding="utf-8"
        )
    else:
        # 使用大小轮转的文件处理器
        max_bytes = parse_size(log_config["max_file_size"])
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / "botshepherd.log",
            maxBytes=max_bytes,
            backupCount=5,
            encoding="utf-8"
        )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger

def parse_size(size_str):
    """解析大小字符串，如 '10MB' -> 10485760"""
    size_str = size_str.upper()
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        return int(size_str)

def get_websocket_logger():
    """获取WebSocket专用日志器"""
    logger = logging.getLogger("BotShepherd.WebSocket")
    
    # 创建WebSocket日志目录
    log_dir = Path("logs/websocket")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 如果还没有处理器，添加文件处理器
    if not logger.handlers:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_dir / "websocket.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    return logger

def get_message_logger():
    """获取消息专用日志器（扁平化格式）"""
    logger = logging.getLogger("BotShepherd.Message")
    
    # 创建消息日志目录
    log_dir = Path("logs/message")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 每日轮转的文件处理器
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.log"
    
    # 创建新的处理器（每次调用都创建新的，确保文件名正确）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    
    # 扁平化格式：时间戳 方向 消息类型 内容摘要
    formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(formatter)
    
    # 清除旧处理器并添加新处理器
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    
    return logger

def get_operation_logger():
    """获取操作日志器"""
    logger = logging.getLogger("BotShepherd.Operation")
    
    # 创建操作日志目录
    log_dir = Path("logs/operation")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 如果还没有处理器，添加文件处理器
    if not logger.handlers:
        file_handler = logging.FileHandler(
            log_dir / "operation.log",
            encoding="utf-8"
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    return logger

def cleanup_old_logs():
    """清理旧日志文件"""
    log_dir = Path("logs/message")
    if not log_dir.exists():
        return
    
    # 删除7天前的消息日志
    cutoff_date = datetime.now() - timedelta(days=7)
    
    for log_file in log_dir.glob("*.log"):
        try:
            # 从文件名解析日期
            date_str = log_file.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if file_date < cutoff_date:
                log_file.unlink()
                print(f"删除旧日志文件: {log_file}")
        except (ValueError, OSError) as e:
            print(f"清理日志文件失败 {log_file}: {e}")

def log_message_flat(direction, message_type, content_summary, extra_info=None):
    """记录扁平化消息日志"""
    logger = get_message_logger()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    log_line = f"{timestamp} {direction} {message_type} {content_summary}"
    
    if extra_info:
        log_line += f" | {extra_info}"
    
    logger.debug(log_line)
