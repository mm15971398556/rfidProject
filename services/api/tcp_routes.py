"""TCP数据相关API路由"""
import traceback
from flask import request, jsonify
from utils.logger import log

def register_tcp_routes(app, db_manager, tcp_server):
    """注册TCP数据相关路由"""
    
    @app.route('/api/tcp/clients', methods=['GET'])
    def get_tcp_clients():
        """获取TCP客户端列表"""
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 20))
            
            # 查询总数
            count_sql = """
                SELECT COUNT(*) as total
                FROM clients
            """
            
            count_result = db_manager.query(count_sql)
            total = count_result[0]['total'] if count_result else 0
            
            # 查询分页数据
            offset = (page - 1) * page_size
            
            data_sql = """
                SELECT 
                    id,
                    client_ip,
                    first_seen as connect_time,
                    last_seen as disconnect_time,
                    CASE WHEN last_seen > DATE_SUB(NOW(), INTERVAL 5 MINUTE) THEN 1 ELSE 0 END as is_connected
                FROM clients
                ORDER BY first_seen DESC
                LIMIT %s OFFSET %s
            """
            
            data_results = db_manager.query(data_sql, [page_size, offset])
            
            # 格式化时间
            for row in data_results:
                if row['connect_time']:
                    row['connect_time'] = row['connect_time'].strftime('%Y-%m-%d %H:%M:%S')
                if row['disconnect_time']:
                    row['disconnect_time'] = row['disconnect_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'success': True,
                'data': data_results,
                'pagination': {
                    'currentPage': page,
                    'pageSize': page_size,
                    'total': total,
                    'totalPages': (total + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            log.error(f"[API] 获取TCP客户端失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/tcp/data', methods=['GET'])
    def get_tcp_data():
        """获取TCP接收数据"""
        try:
            client_id = request.args.get('client_id')
            data_type = request.args.get('data_type')
            start_time = request.args.get('start_time')
            end_time = request.args.get('end_time')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 20))
            
            # 构建查询条件
            conditions = []
            params = []
            
            if client_id:
                conditions.append("client_id = %s")
                params.append(client_id)
            
            if data_type:
                conditions.append("data_type = %s")
                params.append(data_type)
            
            if start_time:
                conditions.append("receive_time >= %s")
                params.append(start_time)
            
            if end_time:
                conditions.append("receive_time <= %s")
                params.append(end_time)
            
            # 查询总数
            count_sql = f"""
                SELECT COUNT(*) as total
                FROM received_data
                {'WHERE ' + ' AND '.join(conditions) if conditions else ''}
            """
            
            count_result = db_manager.query(count_sql, params)
            total = count_result[0]['total'] if count_result else 0
            
            # 查询分页数据
            offset = (page - 1) * page_size
            
            data_params = params.copy()
            data_params.extend([page_size, offset])
            
            data_sql = f"""
                SELECT 
                    id,
                    client_id,
                    receive_time,
                    data_type,
                    data_content,
                    data_length,
                    issue_reason_id,
                    issue_reason,
                    custom_reason,
                    issue_status,
                    issue_updated_time
                FROM received_data
                {'WHERE ' + ' AND '.join(conditions) if conditions else ''}
                ORDER BY receive_time DESC
                LIMIT %s OFFSET %s
            """
            
            data_results = db_manager.query(data_sql, data_params)
            
            # 格式化时间
            for row in data_results:
                if row['receive_time']:
                    row['receive_time'] = row['receive_time'].strftime('%Y-%m-%d %H:%M:%S')
                if row['issue_updated_time']:
                    row['issue_updated_time'] = row['issue_updated_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'success': True,
                'data': data_results,
                'pagination': {
                    'currentPage': page,
                    'pageSize': page_size,
                    'total': total,
                    'totalPages': (total + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            log.error(f"[API] 获取TCP数据失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/tcp/status', methods=['GET'])
    def get_tcp_status():
        """获取TCP服务器状态"""
        try:
            if tcp_server:
                with tcp_server.clients_lock:
                    status = {
                        'is_running': tcp_server.running,
                        'connected_clients': len(tcp_server.clients),
                        'total_received': tcp_server.stats.get('total_bytes', 0)
                    }
                return jsonify({
                    'success': True,
                    'data': status
                })
            else:
                return jsonify({
                    'success': True,
                    'data': {
                        'is_running': False,
                        'connected_clients': 0,
                        'total_received': 0
                    }
                })
                
        except Exception as e:
            log.error(f"[API] 获取TCP状态失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    return app