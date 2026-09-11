# main.py
import time
import threading
import traceback
from config import Config
from database.manager import DatabaseManager
from tcp.server import TCPServer
from api.app import create_app
from utils.logger import log

class IntegratedServer:
    """集成服务器"""
    
    def __init__(self):
        log.info("="*70)
        log.info("集成服务启动中...")
        log.info("="*70)
        
        # 初始化数据库管理器
        self.db = DatabaseManager()
        
        # 初始化TCP服务器
        self.tcp_server = TCPServer(self.db)
        
        # 创建Flask应用
        self.app = create_app(self.db, self.tcp_server)
        
        self.running = True
    
    def start_tcp_server(self):
        """启动TCP服务器（后台线程）"""
        tcp_thread = threading.Thread(target=self.tcp_server.start, daemon=True)
        tcp_thread.start()
        log.info(f"[系统] TCP服务器线程已启动")
    
    def start_api_server(self):
        """启动HTTP API服务器（主线程）"""
        log.info(f"[系统] HTTP API服务器启动在 {Config.HTTP_HOST}:{Config.HTTP_PORT}")
        self.app.run(
            host=Config.HTTP_HOST,
            port=Config.HTTP_PORT,
            debug=Config.DEBUG,
            threaded=True
        )
    
    def start(self):
        """启动所有服务"""
        # 启动TCP服务器
        self.start_tcp_server()
        
        # 给TCP服务器一点启动时间
        time.sleep(1)
        
        # 启动API服务器
        self.start_api_server()
    
    def stop(self):
        """停止所有服务"""
        log.info("\n[系统] 正在停止所有服务...")
        self.tcp_server.stop()
        self.db.close()
        log.info("[系统] 所有服务已停止")

def main():
    """主函数"""
    server = IntegratedServer()
    try:
        server.start()
    except KeyboardInterrupt:
        log.info("\n[系统] 收到中断信号")
        server.stop()
    except Exception as e:
        log.error(f"[系统] 错误: {e}")
        traceback.print_exc()
        server.stop()

if __name__ == "__main__":
    main()