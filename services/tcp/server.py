# tcp/server.py
import socket
import threading
import datetime
import time
from config import Config
from utils.logger import log
from tcp.client_handler import ClientHandler

class TCPServer:
    """TCP服务器"""
    
    def __init__(self, db_manager):
        self.host = Config.TCP_HOST
        self.port = Config.TCP_PORT
        self.max_clients = Config.MAX_CLIENTS
        self.db = db_manager
        self.server_socket = None
        self.running = False
        self.clients = []
        self.clients_lock = threading.Lock()
        
        self.stats = {
            'start_time': None,
            'total_clients': 0,
            'active_clients': 0,
            'total_bytes': 0,
            'total_packets': 0,
            'errors': 0
        }
    
    def start(self):
        """启动TCP服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_clients)
            
            self.running = True
            self.stats['start_time'] = datetime.datetime.now()
            
            log.info(f"[TCP] 服务器启动在 {self.host}:{self.port}")
            
            # 启动监控线程
            monitor_thread = threading.Thread(target=self._monitor_clients, daemon=True)
            monitor_thread.start()
            
            # 主循环
            while self.running:
                try:
                    self.server_socket.settimeout(1)
                    client_socket, client_address = self.server_socket.accept()
                    
                    with self.clients_lock:
                        if len(self.clients) >= self.max_clients:
                            client_socket.close()
                            continue
                        
                        client_handler = ClientHandler(client_socket, client_address, self)
                        self.clients.append(client_handler)
                        self.stats['total_clients'] += 1
                        self.stats['active_clients'] = len(self.clients)
                        
                        client_thread = threading.Thread(
                            target=client_handler.handle,
                            daemon=True
                        )
                        client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        log.error(f"[TCP] 接受连接错误: {e}")
                        self.stats['errors'] += 1
                        
        except Exception as e:
            log.error(f"[TCP] 启动失败: {e}")
        finally:
            self.stop()
    
    def remove_client(self, client_handler):
        """移除客户端"""
        with self.clients_lock:
            if client_handler in self.clients:
                self.clients.remove(client_handler)
                self.stats['active_clients'] = len(self.clients)
    
    def _monitor_clients(self):
        """监控客户端状态"""
        while self.running:
            time.sleep(5)
            with self.clients_lock:
                current_time = datetime.datetime.now()
                timeout_clients = []
                
                for client in self.clients:
                    inactive = (current_time - client.last_activity).total_seconds()
                    if inactive > 120:  # 120秒超时
                        timeout_clients.append(client)
                
                for client in timeout_clients:
                    try:
                        client.socket.close()
                    except:
                        pass
                    self.clients.remove(client)
                
                self.stats['active_clients'] = len(self.clients)
    
    def get_status(self):
        """获取服务器状态"""
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'active_clients': self.stats['active_clients'],
            'total_clients': self.stats['total_clients'],
            'total_bytes': self.stats['total_bytes'],
            'total_packets': self.stats['total_packets'],
            'errors': self.stats['errors'],
            'uptime': str(datetime.datetime.now() - self.stats['start_time']) if self.stats['start_time'] else 'N/A'
        }
    
    def get_clients_info(self):
        """获取客户端信息列表"""
        with self.clients_lock:
            clients_info = []
            for client in self.clients:
                clients_info.append({
                    'address': f"{client.address[0]}:{client.address[1]}",
                    'connected_time': client.connected_time.strftime('%H:%M:%S'),
                    'last_activity': client.last_activity.strftime('%H:%M:%S'),
                    'total_bytes': client.total_bytes,
                    'total_packets': client.total_packets,
                    'recent_data': client.get_recent_data(3)
                })
            return clients_info
    
    def stop(self):
        """停止服务器"""
        log.info("[TCP] 正在停止服务器...")
        self.running = False
        
        with self.clients_lock:
            for client in self.clients:
                try:
                    client.socket.close()
                except:
                    pass
            self.clients.clear()
        
        if self.server_socket:
            self.server_socket.close()
        
        log.info("[TCP] 服务器已停止")