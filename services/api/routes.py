"""API路由配置"""
import traceback
from flask import request, jsonify
from database.manager import DatabaseManager
from utils.logger import log

# 创建数据库管理器实例
db_manager = DatabaseManager()

def register_routes(app, db_manager=None, tcp_server=None):
    """注册API路由"""
    
    @app.route('/api/stats/by-barcode', methods=['GET'])
    def get_stats_by_barcode():
        """按条码获取统计数据"""
        try:
            year = request.args.get('year')
            month = request.args.get('month')
            day = request.args.get('day')
            barcode = request.args.get('barcode')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 20))
            
            # 构建条件和参数
            conditions = ["r.data_type = 'text'"]
            params = []
            
            if year and month:
                if day:
                    conditions.append("DATE(r.receive_time) = %s")
                    params.append(f"{year}-{month:>02}-{day:>02}")
                else:
                    conditions.append("YEAR(r.receive_time) = %s AND MONTH(r.receive_time) = %s")
                    params.extend([year, month])
            
            if barcode:
                conditions.append("r.data_content LIKE %s")
                params.append(f"%{barcode}%")
            
            # 查询总数
            count_sql = f"""
                SELECT COUNT(DISTINCT r.data_content) as total
                FROM received_data r
                WHERE {' AND '.join(conditions)}
            """
            
            count_result = db_manager.query(count_sql, params)
            total = count_result[0]['total'] if count_result else 0
            
            # 查询分页数据
            offset = (page - 1) * page_size
            
            # 为分页查询添加LIMIT和OFFSET参数
            data_params = params.copy()
            data_params.extend([page_size, offset])
            
            data_sql = f"""
                SELECT 
                    r.data_content as barcode,
                    COUNT(*) as scan_count,
                    MIN(r.receive_time) as first_scan,
                    MAX(r.receive_time) as last_scan,
                    COUNT(DISTINCT c.client_ip) as device_count,
                    GROUP_CONCAT(DISTINCT c.client_ip) as devices,
                    r.issue_reason_id,
                    ir.reason_name as issue_reason,
                    r.custom_reason,
                    r.issue_status,
                    r.issue_updated_time
                FROM received_data r
                JOIN clients c ON r.client_id = c.id
                LEFT JOIN issue_reasons ir ON r.issue_reason_id = ir.id
                WHERE {' AND '.join(conditions)}
                GROUP BY r.data_content, r.issue_reason_id, ir.reason_name, r.custom_reason, r.issue_status, r.issue_updated_time
                ORDER BY scan_count DESC
                LIMIT %s OFFSET %s
            """
            
            data_results = db_manager.query(data_sql, data_params)
            
            # 格式化时间
            for row in data_results:
                if row['first_scan']:
                    row['first_scan'] = row['first_scan'].strftime('%Y-%m-%d %H:%M:%S')
                if row['last_scan']:
                    row['last_scan'] = row['last_scan'].strftime('%Y-%m-%d %H:%M:%S')
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
            log.error(f"[API] 获取条码统计失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/stats/by-date', methods=['GET'])
    def get_stats_by_date():
        """按日期获取统计数据"""
        try:
            year = request.args.get('year')
            month = request.args.get('month')
            
            if not year or not month:
                return jsonify({'success': False, 'message': '年份和月份不能为空'}), 400
            
            sql = """
                SELECT 
                    DATE(r.receive_time) as date,
                    COUNT(*) as total_scans,
                    COUNT(DISTINCT r.data_content) as unique_barcodes,
                    COUNT(DISTINCT c.client_ip) as unique_devices
                FROM received_data r
                JOIN clients c ON r.client_id = c.id
                WHERE YEAR(r.receive_time) = %s 
                AND MONTH(r.receive_time) = %s
                GROUP BY DATE(r.receive_time)
                ORDER BY date DESC
            """
            
            results = db_manager.query(sql, [year, month])
            
            # 格式化日期
            for row in results:
                if row['date']:
                    row['date'] = row['date'].strftime('%Y-%m-%d')
            
            return jsonify({
                'success': True,
                'data': results
            })
            
        except Exception as e:
            log.error(f"[API] 获取日期统计失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/stats/top-barcodes', methods=['GET'])
    def get_top_barcodes():
        """获取热门条码"""
        try:
            limit = int(request.args.get('limit', 10))
            
            sql = """
                SELECT 
                    r.data_content as barcode,
                    COUNT(*) as scan_count
                FROM received_data r
                WHERE r.data_type = 'text'
                GROUP BY r.data_content
                ORDER BY scan_count DESC
                LIMIT %s
            """
            
            results = db_manager.query(sql, [limit])
            
            return jsonify({
                'success': True,
                'data': results
            })
            
        except Exception as e:
            log.error(f"[API] 获取热门条码失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/issue/update', methods=['POST'])
    def update_issue_reason():
        """更新条码问题原因"""
        try:
            data = request.get_json()
            barcode = data.get('barcode')
            issue_reason_id = data.get('issue_reason_id')
            custom_reason = data.get('custom_reason', '')
            issue_status = data.get('issue_status', 'normal')
            
            if not barcode:
                return jsonify({'success': False, 'message': '条码不能为空'}), 400
            
            # 获取问题原因名称
            issue_reason_text = ''
            if issue_reason_id:
                reason_sql = "SELECT reason_name FROM issue_reasons WHERE id = %s"
                reason_result = db_manager.query(reason_sql, [issue_reason_id])
                if reason_result:
                    issue_reason_text = reason_result[0]['reason_name']
            
            if custom_reason:
                issue_reason_text = custom_reason
            
            # 更新所有该条码记录的问题原因
            sql = """
                UPDATE received_data 
                SET issue_reason_id = %s,
                    issue_reason = %s,
                    custom_reason = %s,
                    issue_status = %s,
                    issue_updated_time = NOW()
                WHERE data_content = %s 
                AND data_type = 'text'
            """
            
            result = db_manager.execute(sql, [issue_reason_id, issue_reason_text, custom_reason, issue_status, barcode])
            
            if result is not None:
                log.info(f"[问题原因] 条码 {barcode} 的问题原因已更新：ID={issue_reason_id}, 原因={issue_reason_text}, 状态={issue_status}")
                return jsonify({
                    'success': True, 
                    'message': '问题原因更新成功',
                    'data': {
                        'barcode': barcode,
                        'issue_reason_id': issue_reason_id,
                        'issue_reason': issue_reason_text,
                        'custom_reason': custom_reason,
                        'issue_status': issue_status
                    }
                })
            else:
                return jsonify({'success': False, 'message': '更新失败'}), 500
                
        except Exception as e:
            log.error(f"[API] 更新问题原因失败：{e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '更新失败'}), 500

    @app.route('/api/issue/info', methods=['GET'])
    def get_issue_info():
        """获取条码问题信息"""
        try:
            barcode = request.args.get('barcode')
            
            if not barcode:
                return jsonify({'success': False, 'message': '条码不能为空'}), 400
            
            # 获取最新的问题信息
            sql = """
                SELECT 
                    r.data_content as barcode,
                    r.issue_reason,
                    r.issue_status,
                    r.issue_updated_time
                FROM received_data r
                WHERE r.data_content = %s 
                AND r.data_type = 'text'
                ORDER BY r.receive_time DESC
                LIMIT 1
            """
            
            result = db_manager.query(sql, [barcode])
            
            if result:
                issue_info = result[0]
                if issue_info['issue_updated_time']:
                    issue_info['issue_updated_time'] = issue_info['issue_updated_time'].strftime('%Y-%m-%d %H:%M:%S')
                return jsonify({
                    'success': True, 
                    'data': issue_info
                })
            else:
                return jsonify({'success': False, 'message': '未找到条码信息'}), 404
                
        except Exception as e:
            log.error(f"[API] 获取问题信息失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500



    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查"""
        return jsonify({
            'success': True,
            'message': '服务正常运行',
            'timestamp': '2026-03-09 17:45:00'
        })
    
    return app