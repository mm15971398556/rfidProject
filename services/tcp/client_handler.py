# tcp/client_handler.py
import datetime
import socket
from utils.logger import log

class ClientHandler:
    """TCP客户端连接处理器"""
    
    def __init__(self, client_socket, client_address, server):
        self.socket = client_socket
        self.address = client_address
        self.server = server
        self.db = server.db
        self.received_data = []
        self.connected_time = datetime.datetime.now()
        self.last_activity = self.connected_time
        self.client_id = None
        self.total_bytes = 0
        self.total_packets = 0
        
        # 获取或创建客户端ID
        self.client_id = self.db.get_or_create_client(
            self.address[0], 
            self.address[1], 
            self.connected_time
        )
        
        if self.client_id:
            log.info(f"[TCP] 客户端 {self.address[0]}:{self.address[1]} ID: {self.client_id}")
    
    def handle(self):
        """处理客户端连接"""
        client_id = f"{self.address[0]}:{self.address[1]}"
        log.info(f"[TCP] 新客户端 {client_id} 已连接")
        
        try:
            self.socket.settimeout(60)
            
            while True:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                self.last_activity = datetime.datetime.now()
                self.total_bytes += len(data)
                self.total_packets += 1
                
                self._process_data(data)
                
                # 发送确认
                ack_msg = f"ACK: 已收到 {len(data)} 字节".encode('utf-8')
                self.socket.send(ack_msg)
                
        except socket.timeout:
            log.info(f"[TCP] 客户端 {client_id} 连接超时")
        except ConnectionResetError:
            log.info(f"[TCP] 客户端 {client_id} 强制断开")
        except Exception as e:
            log.error(f"[TCP] 客户端 {client_id} 错误: {e}")
        finally:
            self._update_final_stats()
            self.socket.close()
            self.server.remove_client(self)
    
    def _process_data(self, data):
        """处理数据"""
        current_time = datetime.datetime.now()
        
        # 确定数据类型
        try:
            text_data = data.decode('utf-8')
            data_type = "text"
            data_content = text_data
        except UnicodeDecodeError:
            data_type = "binary"
            data_content = data.hex()
        
        data_length = str(len(data))
        
        # 内存记录
        data_info = {
            'time': current_time,
            'type': data_type,
            'length': data_length,
            'content': data_content[:50] + ('...' if len(data_content) > 50 else '')
        }
        self.received_data.append(data_info)
        
        if len(self.received_data) > 100:
            self.received_data.pop(0)
        
        log.info(f"[TCP] 收到 {self.address[0]}:{self.address[1]} - {data_type} {data_length}字节")
        
        # 写入数据库
        if self.client_id:
            # 数据记录
            db_data = {
                'type': 'data_record',
                'client_id': self.client_id,
                'receive_time': current_time,
                'data_type': data_type,
                'data_length': data_length,
                'data_content': data_content
            }
            self.db.queue_write(db_data)
            
            # 统计更新
            stat_data = {
                'type': 'stats_update',
                'stat_date': current_time.date(),
                'client_ip': self.address[0],
                'packets': 1,
                'bytes': len(data)
            }
            self.db.queue_write(stat_data)
        
        # 更新服务器统计
        self.server.stats['total_bytes'] += len(data)
        self.server.stats['total_packets'] += 1
    
    def _update_final_stats(self):
        """更新最终统计"""
        if self.client_id:
            data = {
                'type': 'client_update',
                'client_ip': self.address[0],
                'client_port': self.address[1],
                'first_seen': self.connected_time,
                'last_seen': datetime.datetime.now(),
                'bytes': self.total_bytes,
                'packets': self.total_packets
            }
            self.db.queue_write(data)
    
    def get_recent_data(self, limit=10):
        """获取最近的数据"""
        return self.received_data[-limit:]