import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config.config import get_log_config

class SingletonLogger:
    _instance = None # 用于存储单例实例
    _initialized = False # 标记是否已初始化配置

    def __new__(cls, *args, **kwargs):
        # 第一次创建实例时，_instance 为 None，创建并存储实例
        if cls._instance is None:
            cls._instance = super(SingletonLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, name='my_app', level=logging.INFO, log_dir='logs',
                 console_level=logging.INFO, file_level=logging.DEBUG,
                 max_bytes=None, backup_count=None):
        # 确保初始化配置只执行一次
        if not self._initialized:
            # 从配置文件读取配置项
            log_config = get_log_config()
            
            # 使用配置文件中的值，如果参数未提供的话
            if max_bytes is None:
                max_bytes = log_config.LOG_FILE_MAX_SIZE
            if backup_count is None:
                backup_count = log_config.LOG_FILE_BACKUP_COUNT
            
            self.logger = logging.getLogger(name)
            self.logger.setLevel(level)

            formatter = logging.Formatter(
                log_config.LOG_FORMAT,
                datefmt=log_config.LOG_DATE_FORMAT
            )

            if not self.logger.handlers: # 同样避免重复添加处理器
                console_handler = logging.StreamHandler()
                console_handler.setLevel(console_level)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)

                current_date = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                log_file_name = os.path.join(log_dir, f"{name}_{current_date}.log")

                file_handler = RotatingFileHandler(
                    log_file_name,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setLevel(file_level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

            self._initialized = True # 标记为已初始化

    def get_logger(self):
        return self.logger

# 在模块加载时就创建一个全局的单例日志器实例
# 外部导入时直接拿到这个对象
global_logger_instance = SingletonLogger(
    name='trade',
    log_dir='logs' # 不同的日志目录
)
logger = global_logger_instance.get_logger()
