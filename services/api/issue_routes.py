"""问题原因相关API路由"""
import traceback
from flask import request, jsonify
from utils.logger import log

def register_issue_routes(app, db_manager):
    """注册问题原因相关路由"""
    
    @app.route('/api/issue-reasons', methods=['GET'])
    def get_issue_reasons():
        """获取问题原因列表"""
        try:
            category = request.args.get('category')
            is_active = request.args.get('is_active', 'all')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 20))
            
            sql = """
                SELECT 
                    id,
                    reason_code,
                    reason_name,
                    description,
                    category,
                    is_active,
                    sort_order,
                    created_time,
                    updated_time
                FROM issue_reasons
                WHERE 1=1
            """
            
            params = []
            
            if category:
                sql += " AND category = %s"
                params.append(category)
                
            if is_active and is_active.lower() != 'all':
                is_active_bool = is_active.lower() in ('true', '1', 'yes')
                sql += " AND is_active = %s"
                params.append(1 if is_active_bool else 0)
            
            sql += " ORDER BY sort_order ASC, id ASC"
            
            # 添加分页
            sql += " LIMIT %s OFFSET %s"
            params.extend([page_size, (page - 1) * page_size])
            
            results = db_manager.query(sql, params)
            
            # 获取总数用于分页
            count_sql = "SELECT COUNT(*) as total FROM issue_reasons WHERE 1=1"
            count_params = []
            
            # 使用与主查询相同的过滤条件
            if category:
                count_sql += " AND category = %s"
                count_params.append(category)
                
            if is_active and is_active.lower() != 'all':
                is_active_bool = is_active.lower() in ('true', '1', 'yes')
                count_sql += " AND is_active = %s"
                count_params.append(1 if is_active_bool else 0)
            
            count_result = db_manager.query(count_sql, count_params)
            total_count = count_result[0]['total'] if count_result else 0
            
            # 格式化时间
            for row in results:
                if row['created_time']:
                    row['created_time'] = row['created_time'].strftime('%Y-%m-%d %H:%M:%S')
                if row['updated_time']:
                    row['updated_time'] = row['updated_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'success': True,
                'data': results,
                'pagination': {
                    'currentPage': page,
                    'pageSize': page_size,
                    'total': total_count,
                    'totalPages': (total_count + page_size - 1) // page_size
                }
            })
            
        except Exception as e:
            log.error(f"[API] 获取问题原因列表失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/issue/update', methods=['POST'])
    def update_issue_reason():
        """更新条码问题原因（优先按 record_id 改单条，否则按 barcode 改全部）"""
        try:
            data = request.get_json()
            record_id = data.get('record_id')
            barcode = data.get('barcode')
            issue_reason_id = data.get('issue_reason_id')
            custom_reason = data.get('custom_reason', '')
            issue_status = data.get('issue_status', 'normal')
            
            if not record_id and not barcode:
                return jsonify({'success': False, 'message': 'record_id 或 barcode 不能为空'}), 400
            
            # 获取问题原因名称
            issue_reason_text = ''
            if issue_reason_id:
                reason_sql = "SELECT reason_name FROM issue_reasons WHERE id = %s"
                reason_result = db_manager.query(reason_sql, [issue_reason_id])
                if reason_result:
                    issue_reason_text = reason_result[0]['reason_name']
            
            if custom_reason:
                issue_reason_text = custom_reason
            
            # 更新问题原因
            if record_id:
                # 优先：按 record_id 只改这一条记录
                sql = """
                    UPDATE received_data 
                    SET issue_reason_id = %s,
                        issue_reason = %s,
                        custom_reason = %s,
                        issue_status = %s,
                        issue_updated_time = NOW()
                    WHERE id = %s
                """
                result = db_manager.execute(sql, [issue_reason_id, issue_reason_text, custom_reason, issue_status, record_id])
                scope_desc = f"record_id={record_id}"
            else:
                # fallback：按 barcode 改所有同条码记录
                sql = """
                    UPDATE received_data 
                    SET issue_reason_id = %s,
                        issue_reason = %s,
                        custom_reason = %s,
                        issue_status = %s,
                        issue_updated_time = NOW()
                    WHERE data_content = %s
                """
                result = db_manager.execute(sql, [issue_reason_id, issue_reason_text, custom_reason, issue_status, barcode])
                scope_desc = f"barcode={barcode} (共 {result or 0} 条)"
            
            if result and result > 0:
                log.info(f"[问题原因] {scope_desc} 更新：原因ID={issue_reason_id}, 状态={issue_status}")
                return jsonify({
                    'success': True, 
                    'message': '问题原因更新成功',
                    'data': {
                        'record_id': record_id,
                        'barcode': barcode,
                        'issue_reason_id': issue_reason_id,
                        'issue_reason': issue_reason_text,
                        'custom_reason': custom_reason,
                        'issue_status': issue_status,
                        'updated_rows': result
                    }
                })
            else:
                return jsonify({'success': False, 'message': f'更新失败：未找到匹配的记录'}), 400
                
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
                ORDER BY r.issue_updated_time DESC
                LIMIT 1
            """
            
            result = db_manager.query(sql, [barcode])
            
            if result:
                row = result[0]
                if row['issue_updated_time']:
                    row['issue_updated_time'] = row['issue_updated_time'].strftime('%Y-%m-%d %H:%M:%S')
                
                return jsonify({
                    'success': True,
                    'data': row
                })
            else:
                return jsonify({
                    'success': True,
                    'data': {
                        'barcode': barcode,
                        'issue_reason': '',
                        'issue_status': 'normal',
                        'issue_updated_time': ''
                    }
                })
                
        except Exception as e:
            log.error(f"[API] 获取问题信息失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/issue-reasons', methods=['POST'])
    def create_issue_reason():
        """创建问题原因"""
        try:
            data = request.get_json()
            
            required_fields = ['reason_code', 'reason_name']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'success': False, 'message': f'{field}不能为空'}), 400
            
            sql = """
                INSERT INTO issue_reasons 
                (reason_code, reason_name, description, category, sort_order, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            params = [
                data['reason_code'],
                data['reason_name'],
                data.get('description', ''),
                data.get('category', ''),
                data.get('sort_order', 0),
                data.get('is_active', True)
            ]
            
            result = db_manager.execute(sql, params, return_lastrowid=True)
            
            if result:
                return jsonify({
                    'success': True,
                    'message': '创建成功',
                    'data': {'id': result}
                })
            else:
                return jsonify({'success': False, 'message': '创建失败'}), 500
                
        except Exception as e:
            log.error(f"[API] 创建问题原因失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '创建失败'}), 500

    @app.route('/api/issue-reasons/<int:reason_id>', methods=['PUT'])
    def update_issue_reason_management(reason_id):
        """更新问题原因"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'message': '无效的请求数据'}), 400
            
            # 动态构建更新语句
            updates = []
            params = []
            
            if 'reason_code' in data:
                updates.append('reason_code = %s')
                params.append(data.get('reason_code'))
            
            if 'reason_name' in data:
                updates.append('reason_name = %s')
                params.append(data.get('reason_name'))
            
            if 'description' in data:
                updates.append('description = %s')
                params.append(data.get('description', ''))
            
            if 'category' in data:
                updates.append('category = %s')
                params.append(data.get('category', ''))
            
            if 'sort_order' in data:
                updates.append('sort_order = %s')
                params.append(data.get('sort_order', 0))
            
            if 'is_active' in data:
                is_active = data.get('is_active')
                # 简化处理逻辑，直接转换为布尔值
                if isinstance(is_active, str):
                    is_active = is_active.lower() in ('true', '1', 'yes')
                else:
                    is_active = bool(is_active)
                updates.append('is_active = %s')
                params.append(1 if is_active else 0)
            
            if not updates:
                return jsonify({'success': False, 'message': '没有可更新的字段'}), 400
            
            updates.append('updated_time = NOW()')
            params.append(reason_id)
            
            sql = f"""
                UPDATE issue_reasons 
                SET {', '.join(updates)}
                WHERE id = %s
            """
            
            result = db_manager.execute(sql, params)
            
            return jsonify({
                'success': True,
                'message': '更新成功'
            })
                
        except Exception as e:
            log.error(f"[API] 更新问题原因失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '更新失败'}), 500

    @app.route('/api/issue-reasons/<int:reason_id>', methods=['GET'])
    def get_issue_reason_by_id(reason_id):
        """获取单个问题原因"""
        try:
            sql = """
                SELECT 
                    id,
                    reason_code,
                    reason_name,
                    description,
                    category,
                    is_active,
                    sort_order,
                    created_time,
                    updated_time
                FROM issue_reasons
                WHERE id = %s
            """
            
            result = db_manager.query(sql, [reason_id])
            
            if result:
                row = result[0]
                # 格式化时间
                if row['created_time']:
                    row['created_time'] = row['created_time'].strftime('%Y-%m-%d %H:%M:%S')
                if row['updated_time']:
                    row['updated_time'] = row['updated_time'].strftime('%Y-%m-%d %H:%M:%S')
                
                return jsonify({
                    'success': True,
                    'data': row
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '问题原因不存在'
                }), 404
                
        except Exception as e:
            log.error(f"[API] 获取问题原因失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/issue-reasons/<int:reason_id>', methods=['DELETE'])
    def delete_issue_reason(reason_id):
        """删除问题原因"""
        try:
            sql = "DELETE FROM issue_reasons WHERE id = %s"
            result = db_manager.execute(sql, [reason_id])
            
            # 删除操作总是成功，即使记录不存在
            return jsonify({
                'success': True,
                'message': '删除成功'
            })
                
        except Exception as e:
            log.error(f"[API] 删除问题原因失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '删除失败'}), 500

    return app