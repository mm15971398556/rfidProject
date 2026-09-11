"""统计相关API路由"""
import traceback
from flask import request, jsonify
from utils.logger import log

def register_stats_routes(app, db_manager):
    """注册统计相关路由"""
    
    @app.route('/api/stats/by-barcode', methods=['GET'])
    def get_stats_by_barcode():
        """按条码获取统计数据（按单条扫描记录统计）"""
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
            
            # 查询总数（按单条记录统计）
            count_sql = f"""
                SELECT COUNT(*) as total
                FROM received_data r
                WHERE {' AND '.join(conditions)}
            """
            
            count_result = db_manager.query(count_sql, params)
            total = count_result[0]['total'] if count_result else 0
            
            # 查询去重后的条码总数
            unique_barcode_sql = f"""
                SELECT COUNT(DISTINCT r.data_content) as unique_barcodes
                FROM received_data r
                WHERE {' AND '.join(conditions)}
            """
            
            unique_barcode_result = db_manager.query(unique_barcode_sql, params)
            unique_barcodes = unique_barcode_result[0]['unique_barcodes'] if unique_barcode_result else 0
            
            # 查询分页数据（按单条记录统计）
            offset = (page - 1) * page_size
            
            # 为分页查询添加LIMIT和OFFSET参数
            data_params = params.copy()
            data_params.extend([page_size, offset])
            
            data_sql = f"""
                SELECT 
                    r.data_content as barcode,
                    1 as scan_count,  -- 每条记录算作一次扫描
                    r.receive_time as scan_time,
                    r.receive_time as first_scan,
                    r.receive_time as last_scan,
                    1 as device_count,  -- 每条记录对应一个设备
                    c.client_ip as devices,
                    r.issue_reason_id,
                    ir.reason_name as issue_reason,
                    r.custom_reason,
                    r.issue_status,
                    r.issue_updated_time,
                    r.id as record_id
                FROM received_data r
                JOIN clients c ON r.client_id = c.id
                LEFT JOIN issue_reasons ir ON r.issue_reason_id = ir.id
                WHERE {' AND '.join(conditions)}
                ORDER BY r.receive_time DESC
                LIMIT %s OFFSET %s
            """
            
            data_results = db_manager.query(data_sql, data_params)
            
            # 格式化时间
            for row in data_results:
                if row['scan_time']:
                    row['scan_time'] = row['scan_time'].strftime('%Y-%m-%d %H:%M:%S')
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
                    'totalPages': (total + page_size - 1) // page_size,
                    'uniqueBarcodes': unique_barcodes  # 去重后的条码总数
                }
            })
            
        except Exception as e:
            log.error(f"[API] 获取条码统计失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/stats/by-date', methods=['GET'])
    def get_stats_by_date():
        """按日期获取统计数据（基于单条扫描记录统计）"""
        try:
            year = request.args.get('year')
            month = request.args.get('month')
            
            if not year or not month:
                return jsonify({'success': False, 'message': '年份和月份不能为空'}), 400
            
            sql = """
                SELECT 
                    DATE(r.receive_time) as date,
                    COUNT(*) as total_count,
                    COUNT(DISTINCT r.data_content) as barcode_count,
                    COUNT(DISTINCT c.client_ip) as device_count
                FROM received_data r
                JOIN clients c ON r.client_id = c.id
                WHERE r.data_type = 'text'
                    AND YEAR(r.receive_time) = %s
                    AND MONTH(r.receive_time) = %s
                GROUP BY DATE(r.receive_time)
                ORDER BY date
            """
            
            results = db_manager.query(sql, [year, month])
            
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
        """获取热门条码（基于单条扫描记录统计）"""
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

    return app