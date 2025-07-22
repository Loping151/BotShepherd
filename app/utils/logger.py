import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

class BSLogger:

    def __init__(self, global_config=None):
        # 1. 设置和解析配置
        self._setup_config(global_config)

        # 2. 创建根日志目录
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # 3. 配置主日志记录器 ("BotShepherd")
        self._setup_main_logger()

        # 4. 配置专用的子日志记录器
        self.ws = self._setup_special_logger("WebSocket", "websocket", use_timed_rotation=True)
        self.message = self._setup_special_logger("Message", "message", use_timed_rotation=True, formatter=logging.Formatter('%(message)s'))
        self.web = self._setup_special_logger("Web", "web", use_timed_rotation=True)
        self.command = self._setup_special_logger("Command", "command", use_timed_rotation=True)
        self.op = self._setup_special_logger("Operation", "operation", rotate=False) # 操作日志不轮转

    def __getattr__(self, name):
        if hasattr(self.main_logger, name):
            return getattr(self.main_logger, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _setup_config(self, global_config):
        self.config = {
            "level": "INFO",
            "file_rotation": True,
            "keep_days": 7,
            "max_file_size": "10MB"
        }
        if global_config and "logging" in global_config:
            self.config.update(global_config["logging"])
        
        self.log_level = getattr(logging, self.config["level"].upper())
        self.keep_days = int(self.config["keep_days"])

    def _setup_main_logger(self):
        self.main_logger = logging.getLogger("BotShepherd")
        self.main_logger.setLevel(self.log_level)
        self.main_logger.handlers.clear()
        self.main_logger.propagate = False

        # 控制台处理器
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.main_logger.addHandler(self.console_handler)

        # 主日志文件处理器（带轮转）
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s')
        
        if self.config["file_rotation"]:
            # 按时间轮转
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=self.log_dir / "botshepherd.log",
                when="midnight",
                interval=1,
                backupCount=self.keep_days,
                encoding="utf-8"
            )
        else:
            # 按大小轮转
            max_bytes = self._parse_size(self.config["max_file_size"])
            handler = logging.handlers.RotatingFileHandler(
                filename=self.log_dir / "botshepherd.log",
                maxBytes=max_bytes,
                backupCount=self.keep_days, # 使用 keep_days 作为备份数量
                encoding="utf-8"
            )
        
        handler.setFormatter(file_formatter)
        self.main_logger.addHandler(handler)

    def _setup_special_logger(self, name, sub_dir, rotate=True, use_timed_rotation=True, formatter=None, console_formatter=None):
        """
        创建一个专用的子日志记录器。
        
        :param name: 日志记录器名称 (e.g., "WebSocket")
        :param sub_dir: 日志存放的子目录 (e.g., "websocket")
        :param rotate: 是否需要轮转。如果为 False，则使用 FileHandler。
        :param use_timed_rotation: 如果 rotate=True，此参数决定是按时间还是大小轮转。
        :param formatter: 自定义日志格式。如果为 None，使用默认格式。
        :return: 配置好的 logging.Logger 实例。
        """
        logger_name = f"BotShepherd.{name}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.log_level)
        logger.handlers.clear()
        logger.propagate = False  # 防止日志向上传播到主日志记录器
        
        if console_formatter:
            # 复制一份，避免修改共享的 handler
            console_handler_copy = logging.StreamHandler()
            console_handler_copy.setFormatter(console_formatter)
            logger.addHandler(console_handler_copy)
        else:
            logger.addHandler(self.console_handler)

        # 创建专用日志目录
        special_log_dir = self.log_dir / sub_dir
        special_log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = special_log_dir / f"{sub_dir}.log"

        # 设置处理器
        if not rotate:
            # 不轮转的日志
            handler = logging.FileHandler(log_file_path, encoding="utf-8")
        elif use_timed_rotation:
            # 按时间轮转 (每日)
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=log_file_path,
                when="midnight",
                interval=1,
                backupCount=self.keep_days,
                encoding="utf-8"
            )
        else:
            # 按大小轮转
            max_bytes = self._parse_size(self.config["max_file_size"])
            handler = logging.handlers.RotatingFileHandler(
                filename=log_file_path,
                maxBytes=max_bytes,
                backupCount=self.keep_days,
                encoding="utf-8"
            )
        
        # 设置格式化器
        if formatter:
            handler.setFormatter(formatter)
        else:
            default_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(default_formatter)
        
        logger.addHandler(handler)
        return logger

    def log_message(self, direction, message_type, content_summary, extra_info=None):
        """
        记录一条格式化的、扁平的消息日志。
        这是一个便捷方法，底层调用 self.message.info()。
        
        :param direction: 消息方向 (e.g., "SENT", "RECV")
        :param message_type: 消息类型 (e.g., "TEXT", "IMAGE")
        :param content_summary: 内容摘要
        :param extra_info: 额外信息 (e.g., user_id, chat_id)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_line = f"{timestamp} {direction} {message_type} {content_summary}"
        if extra_info:
            log_line += f" | {extra_info}"
        
        # 使用配置好的 message 日志记录器
        self.message.info(log_line)

    @staticmethod
    def _parse_size(size_str):
        """解析大小字符串，如 '10MB' -> 10485760"""
        size_str = str(size_str).upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)

# --- 使用示例 ---

if __name__ == '__main__':
    # 模拟一个全局配置文件
    mock_global_config = {
        "some_other_setting": "value",
        "logging": {
            "level": "DEBUG",         # 设置日志级别为 DEBUG
            "file_rotation": True,    # True: 按时间(midnight)轮转, False: 按大小轮转
            "keep_days": 3,           # 日志文件保留3天
            "max_file_size": "1MB"    # 如果按大小轮转，每个文件最大1MB
        }
    }

    print("--- 初始化日志系统 ---")
    logger = BSLogger(mock_global_config)
    print("日志系统初始化完成。日志将输出到控制台和 'logs/' 目录中。\n")

    # 1. 使用主日志记录器 (通过 __getattr__ 代理)
    print("--- 测试主日志 ---")
    logger.debug("这是一条 DEBUG 信息，用于详细诊断。")
    logger.info("程序启动成功。")
    logger.warning("一个非关键配置项缺失，使用默认值。")
    logger.error("无法连接到数据库。")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("发生了一个预期之外的错误！")
    print("主日志测试完成。请检查 logs/botshepherd.log 文件。\n")

    # 2. 使用 WebSocket 日志记录器
    print("--- 测试 WebSocket 日志 ---")
    logger.ws.info("WebSocket 客户端 192.168.1.100 连接。")
    logger.ws.warning("来自 192.168.1.100 的消息格式不正确。")
    print("WebSocket 日志测试完成。请检查 logs/websocket/websocket.log 文件.\n")

    # 3. 使用消息日志记录器 (通过便捷方法)
    print("--- 测试消息日志 ---")
    logger.log_message(direction="RECV", message_type="TEXT", content_summary="你好，在吗？", extra_info="from_user:1001, to_user:2002")
    logger.log_message(direction="SENT", message_type="TEXT", content_summary="在的，有什么事吗？", extra_info="from_user:2002, to_user:1001")
    # 也可以直接调用
    # logger.message.info("原始消息日志条目")
    print("消息日志测试完成。请检查 logs/message/message.log 文件。\n")

    # 4. 使用操作日志记录器
    print("--- 测试操作日志 ---")
    logger.op.info("管理员 'admin' 登录系统。")
    logger.op.info("管理员 'admin' 重启了服务 'service_A'。")
    logger.op.warning("管理员 'admin' 尝试删除受保护的用户 'root'。")
    print("操作日志测试完成。请检查 logs/operation/operation.log 文件。\n")