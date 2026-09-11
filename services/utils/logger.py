# utils/logger.py
import logging
import datetime
import sys
from config import Config

class Logger:
    """日志工具类"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    def _init_logger(self):
        """初始化日志器"""
        self.logger = logging.getLogger('TCPDataServer')
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        try:
            file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
        except:
            pass
    
    def info(self, msg):
        self.logger.info(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)
    
    def debug(self, msg):
        self.logger.debug(msg)
    
    def get_time(self):
        """获取当前时间字符串"""
        return datetime.datetime.now().strftime("%H:%M:%S")

# 全局日志实例
log = Logger()