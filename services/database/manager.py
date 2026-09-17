# database/manager.py
import pymysql
import pymysql.cursors
import threading
import queue
import time
import datetime
import traceback
from config import Config
from utils.logger import log

class DatabaseManager:
    """数据库管理器（支持连接池和异步写入）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if hasattr(self, 'initialized'):
            return
            
        self.host = Config.DB_HOST
        self.port = Config.DB_PORT
        self.user = Config.DB_USER
        self.password = Config.DB_PASSWORD
        self.database = Config.DB_NAME
        self.max_connections = Config.DB_POOL_SIZE
        
        self.connection_pool = queue.Queue(maxsize=self.max_connections)
        self.write_queue = queue.Queue(maxsize=1000)
        self.running = True
        
        # 统计信息
        self.stats = {
            'total_writes': 0,
            'successful_writes': 0,
            'failed_writes': 0,
            'queue_size': 0
        }
        
        # 客户端ID缓存
        self.client_id_cache = {}
        self.cache_lock = threading.Lock()
        
        # 初始化
        self._init_database()
        self._init_connection_pool()
        
        # 启动写入线程
        self.writer_thread = threading.Thread(target=self._async_writer, daemon=True)
        self.writer_thread.start()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_stats, daemon=True)
        self.monitor_thread.start()
        
        self.initialized = True
        log.info(f"[数据库] 初始化成功，连接池大小: {self.max_connections}")
    
    def _monitor_stats(self):
        """监控统计信息"""
        while self.running:
            time.sleep(30)
            queue_size = self.write_queue.qsize()
            if queue_size > 50:
                log.warning(f"[数据库] 警告: 队列积压 {queue_size} 条")
    
    def _init_database(self):
        """初始化数据库和表"""
        conn = None
        try:
            # 连接MySQL服务器
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                log.info(f"[数据库] 数据库 {self.database} 已就绪")
            
            conn.close()
            
            # 连接到具体数据库
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            with conn.cursor() as cursor:
                # 创建客户端信息表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS clients (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        client_ip VARCHAR(50) NOT NULL,
                        client_port INT NOT NULL,
                        first_seen DATETIME NOT NULL,
                        last_seen DATETIME NOT NULL,
                        total_bytes BIGINT DEFAULT 0,
                        total_packets INT DEFAULT 0,
                        INDEX idx_client (client_ip, client_port),
                        INDEX idx_last_seen (last_seen)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 创建数据记录表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS received_data (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        client_id INT NOT NULL,
                        receive_time DATETIME NOT NULL,
                        data_type VARCHAR(50) NOT NULL,
                        data_length VARCHAR(20) NOT NULL,
                        data_content TEXT,
                        issue_reason_id INT COMMENT '问题原因ID',
                        custom_reason TEXT COMMENT '自定义问题原因',
                        issue_status VARCHAR(20) DEFAULT 'normal' COMMENT '问题状态: normal-正常, pending-待处理, resolved-已解决',
                        issue_updated_time DATETIME COMMENT '问题更新时间',
                        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
                        FOREIGN KEY (issue_reason_id) REFERENCES issue_reasons(id) ON DELETE SET NULL,
                        INDEX idx_receive_time (receive_time),
                        INDEX idx_client_time (client_id, receive_time),
                        INDEX idx_issue_status (issue_status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 创建数据统计表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS data_stats (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        stat_date DATE NOT NULL,
                        client_ip VARCHAR(50) NOT NULL,
                        total_packets INT DEFAULT 0,
                        total_bytes BIGINT DEFAULT 0,
                        UNIQUE KEY unique_stat (stat_date, client_ip)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 创建问题原因分类表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS issue_reasons (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        reason_code VARCHAR(50) NOT NULL COMMENT '问题原因代码',
                        reason_name VARCHAR(100) NOT NULL COMMENT '问题原因名称',
                        description TEXT COMMENT '详细描述',
                        category VARCHAR(50) COMMENT '问题分类',
                        is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
                        sort_order INT DEFAULT 0 COMMENT '排序',
                        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_code (reason_code),
                        INDEX idx_category (category),
                        INDEX idx_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 创建条码维护人配置表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS barcode_maintainers (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        barcode VARCHAR(200) NOT NULL COMMENT '条码',
                        maintainer_name VARCHAR(100) NOT NULL COMMENT '维护人',
                        is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
                        created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY unique_barcode (barcode),
                        INDEX idx_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 首次建表后，从前端旧 JSON 导入初始数据
                cursor.execute("SELECT COUNT(*) as cnt FROM barcode_maintainers")
                existing = cursor.fetchone()['cnt']
                if existing == 0:
                    import os, json
                    json_path = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        '..', 'frontend', 'src', 'config', 'barcode-maintainer.json'
                    )
                    json_path = os.path.normpath(json_path)
                    if os.path.isfile(json_path):
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            items = data.get('barcode_maintainers', {})
                            for barcode, maintainer in items.items():
                                cursor.execute(
                                    "INSERT IGNORE INTO barcode_maintainers (barcode, maintainer_name) VALUES (%s, %s)",
                                    [barcode, maintainer]
                                )
                            log.info(f"[数据库] 从 JSON 导入 {len(items)} 条维护人映射")
                        except Exception as import_err:
                            log.warning(f"[数据库] 从 JSON 导入初始数据失败: {import_err}")

                conn.commit()
                log.info("[数据库] 数据表初始化完成")
            
        except Exception as e:
            log.error(f"[数据库] 初始化失败: {e}")
            traceback.print_exc()
            raise
        finally:
            if conn:
                conn.close()
    
    def _init_connection_pool(self):
        """初始化连接池"""
        for i in range(self.max_connections):
            try:
                conn = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
                self.connection_pool.put(conn)
            except Exception as e:
                log.error(f"[数据库] 创建连接池失败: {e}")
    
    def get_connection(self):
        """从连接池获取连接"""
        try:
            return self.connection_pool.get(timeout=5)
        except queue.Empty:
            return pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
    
    def return_connection(self, conn):
        """归还连接到连接池"""
        try:
            # 确保连接已提交任何未完成的事务
            conn.commit()
            self.connection_pool.put_nowait(conn)
        except queue.Full:
            conn.close()
        except Exception as e:
            log.error(f"[数据库] 归还连接失败：{e}")
            conn.close()
    
    def get_or_create_client(self, client_ip, client_port, first_seen):
        """获取或创建客户端记录，返回client_id"""
        cache_key = f"{client_ip}:{client_port}"
        
        with self.cache_lock:
            if cache_key in self.client_id_cache:
                return self.client_id_cache[cache_key]
        
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM clients 
                    WHERE client_ip = %s AND client_port = %s
                """, (client_ip, client_port))
                
                result = cursor.fetchone()
                
                if result:
                    client_id = result['id']
                    cursor.execute("""
                        UPDATE clients 
                        SET last_seen = %s
                        WHERE id = %s
                    """, (first_seen, client_id))
                else:
                    cursor.execute("""
                        INSERT INTO clients (client_ip, client_port, first_seen, last_seen, total_bytes, total_packets)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (client_ip, client_port, first_seen, first_seen, 0, 0))
                    client_id = cursor.lastrowid
                    log.info(f"[数据库] 创建新客户端: {client_ip}:{client_port} -> ID: {client_id}")
                
                conn.commit()
                
                with self.cache_lock:
                    self.client_id_cache[cache_key] = client_id
                
                return client_id
                
        except Exception as e:
            log.error(f"[数据库] 获取/创建客户端失败: {e}")
            return None
        finally:
            if conn:
                self.return_connection(conn)
    
    def _async_writer(self):
        """异步写入线程"""
        log.info("[数据库] 异步写入线程启动")
        
        batch_size = 10
        batch_timeout = 2
        max_retries = 3
        
        buffer = []
        last_write_time = time.time()
        
        while self.running:
            try:
                try:
                    data = self.write_queue.get(timeout=0.5)
                    buffer.append(data)
                    self.stats['total_writes'] += 1
                except queue.Empty:
                    if buffer and (time.time() - last_write_time > batch_timeout):
                        self._batch_write_with_retry(buffer, max_retries)
                        buffer = []
                        last_write_time = time.time()
                    continue
                
                if len(buffer) >= batch_size or (time.time() - last_write_time > batch_timeout):
                    self._batch_write_with_retry(buffer, max_retries)
                    buffer = []
                    last_write_time = time.time()
                    
            except Exception as e:
                log.error(f"[数据库] 异步写入错误: {e}")
        
        if buffer:
            self._batch_write_with_retry(buffer, max_retries)
        
        log.info("[数据库] 异步写入线程停止")
    
    def _batch_write_with_retry(self, data_list, max_retries=3):
        """带重试的批量写入"""
        if not data_list:
            return
        
        for attempt in range(max_retries):
            try:
                self._batch_write(data_list)
                self.stats['successful_writes'] += len(data_list)
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                else:
                    log.error(f"[数据库] 写入最终失败，丢弃 {len(data_list)} 条数据: {e}")
                    self.stats['failed_writes'] += len(data_list)
    
    def _batch_write(self, data_list):
        """批量写入数据"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                for data in data_list:
                    if data['type'] == 'client_update':
                        cursor.execute("""
                            INSERT INTO clients (client_ip, client_port, first_seen, last_seen, total_bytes, total_packets)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            last_seen = VALUES(last_seen),
                            total_bytes = total_bytes + VALUES(total_bytes),
                            total_packets = total_packets + VALUES(total_packets)
                        """, (
                            data['client_ip'], data['client_port'],
                            data['first_seen'], data['last_seen'],
                            data['bytes'], data['packets']
                        ))
                        
                    elif data['type'] == 'data_record':
                        cursor.execute("""
                            INSERT INTO received_data 
                            (client_id, receive_time, data_type, data_length, data_content)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            data['client_id'], 
                            data['receive_time'],
                            data['data_type'],
                            data['data_length'],
                            data['data_content']
                        ))
                        
                    elif data['type'] == 'stats_update':
                        cursor.execute("""
                            INSERT INTO data_stats (stat_date, client_ip, total_packets, total_bytes)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            total_packets = total_packets + VALUES(total_packets),
                            total_bytes = total_bytes + VALUES(total_bytes)
                        """, (
                            data['stat_date'], data['client_ip'],
                            data['packets'], data['bytes']
                        ))
                
                conn.commit()
                
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def queue_write(self, data):
        """将数据加入写入队列"""
        try:
            self.write_queue.put_nowait(data)
        except queue.Full:
            log.warning("[数据库] 写入队列已满，丢弃数据")
            self.stats['failed_writes'] += 1
    
    def query(self, sql, params=None):
        """直接查询数据库（用于API）"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except Exception as e:
            log.error(f"[数据库] 查询失败: {e}")
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def execute(self, sql, params=None, return_lastrowid=False):
        """执行 SQL 语句（用于 API 的增删改）"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                result = cursor.execute(sql, params or ())
                conn.commit()
                if return_lastrowid:
                    return cursor.lastrowid
                return result
        except Exception as e:
            log.error(f"[数据库] 执行失败：{e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_stats(self):
        """获取数据库统计信息"""
        return {
            'queue_size': self.write_queue.qsize(),
            'total_writes': self.stats['total_writes'],
            'successful_writes': self.stats['successful_writes'],
            'failed_writes': self.stats['failed_writes']
        }
    
    def close(self):
        """关闭数据库连接"""
        log.info("[数据库] 正在关闭...")
        self.running = False
        
        if self.writer_thread.is_alive():
            self.writer_thread.join(timeout=10)
        
        closed = 0
        while not self.connection_pool.empty():
            try:
                conn = self.connection_pool.get_nowait()
                conn.close()
                closed += 1
            except:
                pass
        
        log.info(f"[数据库] 已关闭 {closed} 个连接")