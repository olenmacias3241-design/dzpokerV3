# dzpokerV3 生产环境配置
# 生产环境专用配置，优化性能和安全性

import os
from datetime import timedelta

class ProductionConfig:
    """生产环境配置"""
    
    # 基础配置
    ENV = 'production'
    DEBUG = False
    TESTING = False
    
    # 密钥配置（从环境变量读取）
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-in-production')
    
    # 数据库配置
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'dzpoker')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'dzpoker')
    
    # 数据库连接池配置
    DB_POOL_SIZE = 10
    DB_POOL_RECYCLE = 3600
    DB_POOL_TIMEOUT = 30
    
    # 服务器配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5002))
    
    # CORS 配置
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Session 配置
    SESSION_COOKIE_SECURE = True  # 仅 HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', '/var/log/dzpoker/app.log')
    
    # 游戏配置
    PLAYER_ACTION_TIMEOUT = int(os.getenv('PLAYER_ACTION_TIMEOUT', 15))
    PLAYER_ACTION_TIMEOUT_MIN = int(os.getenv('PLAYER_ACTION_TIMEOUT_MIN', 10))
    PLAYER_ACTION_TIMEOUT_MAX = int(os.getenv('PLAYER_ACTION_TIMEOUT_MAX', 30))
    
    # Redis 配置（可选）
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # WebSocket 配置
    SOCKETIO_MESSAGE_QUEUE = None  # 可以配置 Redis
    SOCKETIO_ASYNC_MODE = 'eventlet'
    
    # 性能配置
    WORKERS = int(os.getenv('WORKERS', 4))
    THREADS = int(os.getenv('THREADS', 2))
    TIMEOUT = int(os.getenv('TIMEOUT', 120))
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 配置日志
        import logging
        from logging.handlers import RotatingFileHandler
        
        # 创建日志目录
        log_dir = os.path.dirname(ProductionConfig.LOG_FILE)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 配置文件日志
        file_handler = RotatingFileHandler(
            ProductionConfig.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(getattr(logging, ProductionConfig.LOG_LEVEL))
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, ProductionConfig.LOG_LEVEL))


class DevelopmentConfig:
    """开发环境配置"""
    
    ENV = 'development'
    DEBUG = True
    TESTING = False
    
    SECRET_KEY = 'dev-secret-key'
    
    DB_HOST = 'localhost'
    DB_PORT = 3306
    DB_USER = 'dzpoker'
    DB_PASSWORD = 'dzpoker'
    DB_NAME = 'dzpoker'
    
    HOST = '0.0.0.0'
    PORT = 5002
    
    LOG_LEVEL = 'DEBUG'
    
    PLAYER_ACTION_TIMEOUT = 15


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config():
    """获取当前环境配置"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
