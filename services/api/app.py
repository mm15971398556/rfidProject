# api/app.py
from flask import Flask, request
from flask_cors import CORS
from config import Config
from api.stats_routes import register_stats_routes
from api.issue_routes import register_issue_routes
from api.tcp_routes import register_tcp_routes
from utils.logger import log

def create_app(db_manager, tcp_server):
    """创建Flask应用"""
    app = Flask(__name__)
    CORS(app)
    
    # 添加请求日志中间件
    @app.before_request
    def log_request_info():
        log.info(f"[API] 收到 {request.method} 请求: {request.url}")
        if request.is_json:
            log.info(f"[API] 请求JSON数据: {request.get_json()}")
    
    # 注册模块化路由
    app = register_stats_routes(app, db_manager)
    app = register_issue_routes(app, db_manager)
    app = register_tcp_routes(app, db_manager, tcp_server)
    
    return app