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

    def log_message(self, direction, message_type, content_summary, extra_info=None, level="info"):
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
        if level == "info":
            self.message.info(log_line)
        elif level == "debug":
            self.message.debug(log_line)
        elif level == "warning":
            self.message.warning(log_line)
        elif level == "error":
            self.message.error(log_line)
        else:
            raise ValueError(f"Invalid log level: {level}")

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
