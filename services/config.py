# config.py
import os

class Config:
    """系统配置类"""
    
    # TCP服务器配置
    TCP_HOST = '192.168.1.101'
    TCP_PORT = 8080
    MAX_CLIENTS = 100
    
    # MySQL数据库配置
    DB_HOST = '127.0.0.1'
    DB_PORT = 3306
    DB_USER = 'root'
    DB_PASSWORD = '201812'
    DB_NAME = 'tcp_data'
    DB_POOL_SIZE = 10
    
    # HTTP API配置
    HTTP_HOST = '0.0.0.0'
    HTTP_PORT = 5000
    DEBUG = True
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'server.log'
    
    @classmethod
    def get_db_uri(cls):
        """获取数据库连接URI"""
        return f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}?charset=utf8mb4"