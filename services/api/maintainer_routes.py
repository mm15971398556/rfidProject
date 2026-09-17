"""条码维护人配置相关API"""
import traceback
from flask import request, jsonify
from utils.logger import log

def register_maintainer_routes(app, db_manager):
    """注册条码维护人相关路由"""

    @app.route('/api/maintainers', methods=['GET'])
    def get_maintainers():
        """分页查询条码维护人列表"""
        try:
            keyword = request.args.get('keyword', '').strip()
            is_active = request.args.get('is_active', 'all')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 20))

            sql = """
                SELECT id, barcode, maintainer_name, is_active,
                       created_time, updated_time
                FROM barcode_maintainers
                WHERE 1=1
            """
            params = []

            if keyword:
                sql += " AND (barcode LIKE %s OR maintainer_name LIKE %s)"
                params.extend([f'%{keyword}%', f'%{keyword}%'])

            if is_active and is_active.lower() != 'all':
                val = is_active.lower() in ('true', '1', 'yes')
                sql += " AND is_active = %s"
                params.append(1 if val else 0)

            count_sql = "SELECT COUNT(*) as total FROM barcode_maintainers WHERE 1=1"
            count_params = []
            if keyword:
                count_sql += " AND (barcode LIKE %s OR maintainer_name LIKE %s)"
                count_params.extend([f'%{keyword}%', f'%{keyword}%'])
            if is_active and is_active.lower() != 'all':
                val = is_active.lower() in ('true', '1', 'yes')
                count_sql += " AND is_active = %s"
                count_params.append(1 if val else 0)

            count_result = db_manager.query(count_sql, count_params)
            total_count = count_result[0]['total'] if count_result else 0

            sql += " ORDER BY id ASC LIMIT %s OFFSET %s"
            params.extend([page_size, (page - 1) * page_size])

            results = db_manager.query(sql, params)

            for row in results:
                if row['created_time']:
                    row['created_time'] = row['created_time'].strftime('%Y-%m-%d %H:%M:%S')
                if row['updated_time']:
                    row['updated_time'] = row['updated_time'].strftime('%Y-%m-%d %H:%M:%S')
                row['is_active'] = bool(row['is_active'])

            return jsonify({
                'success': True,
                'data': results,
                'pagination': {
                    'currentPage': page,
                    'pageSize': page_size,
                    'total': total_count,
                    'totalPages': (total_count + page_size - 1) // page_size if total_count > 0 else 0
                }
            })

        except Exception as e:
            log.error(f"[API] 获取维护人列表失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/maintainers/all', methods=['GET'])
    def get_maintainers_all():
        """返回全量 {barcode: maintainer_name} 字典（给 Dashboard / Table 用）"""
        try:
            sql = "SELECT barcode, maintainer_name FROM barcode_maintainers WHERE is_active = 1"
            results = db_manager.query(sql, [])
            data = {row['barcode']: row['maintainer_name'] for row in results}
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            log.error(f"[API] 获取全量维护人失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '获取失败'}), 500

    @app.route('/api/maintainers', methods=['POST'])
    def create_maintainer():
        """新增条码维护人"""
        try:
            data = request.get_json()
            barcode = (data.get('barcode') or '').strip()
            maintainer_name = (data.get('maintainer_name') or '').strip()

            if not barcode or not maintainer_name:
                return jsonify({'success': False, 'message': '条码和维护人不能为空'}), 400

            # 检查是否已存在
            exist = db_manager.query(
                "SELECT id FROM barcode_maintainers WHERE barcode = %s", [barcode]
            )
            if exist:
                return jsonify({'success': False, 'message': f'条码 "{barcode}" 已存在（id={exist[0]["id"]}）'}), 400

            is_active = 1 if data.get('is_active', True) else 0

            sql = """
                INSERT INTO barcode_maintainers (barcode, maintainer_name, is_active)
                VALUES (%s, %s, %s)
            """
            new_id = db_manager.execute(sql, [barcode, maintainer_name, is_active], return_lastrowid=True)

            return jsonify({'success': True, 'message': '创建成功', 'data': {'id': new_id}})

        except Exception as e:
            log.error(f"[API] 创建维护人失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '创建失败'}), 500

    @app.route('/api/maintainers/<int:item_id>', methods=['PUT'])
    def update_maintainer(item_id):
        """更新条码维护人"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': '无效的请求数据'}), 400

            updates = []
            params = []

            if 'barcode' in data:
                new_barcode = (data['barcode'] or '').strip()
                if not new_barcode:
                    return jsonify({'success': False, 'message': '条码不能为空'}), 400
                # 检查新条码是否和其他记录冲突
                conflict = db_manager.query(
                    "SELECT id FROM barcode_maintainers WHERE barcode = %s AND id != %s",
                    [new_barcode, item_id]
                )
                if conflict:
                    return jsonify({'success': False, 'message': f'条码 "{new_barcode}" 已被 id={conflict[0]["id"]} 占用'}), 400
                updates.append('barcode = %s')
                params.append(new_barcode)

            if 'maintainer_name' in data:
                name = (data['maintainer_name'] or '').strip()
                if not name:
                    return jsonify({'success': False, 'message': '维护人不能为空'}), 400
                updates.append('maintainer_name = %s')
                params.append(name)

            if 'is_active' in data:
                val = data['is_active']
                if isinstance(val, str):
                    val = val.lower() in ('true', '1', 'yes')
                updates.append('is_active = %s')
                params.append(1 if bool(val) else 0)

            if not updates:
                return jsonify({'success': False, 'message': '没有可更新的字段'}), 400

            updates.append('updated_time = NOW()')
            params.append(item_id)

            sql = f"UPDATE barcode_maintainers SET {', '.join(updates)} WHERE id = %s"
            result = db_manager.execute(sql, params)

            if result and result > 0:
                return jsonify({'success': True, 'message': '更新成功'})
            else:
                return jsonify({'success': False, 'message': '更新失败：记录不存在'}), 404

        except Exception as e:
            log.error(f"[API] 更新维护人失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '更新失败'}), 500

    @app.route('/api/maintainers/<int:item_id>', methods=['DELETE'])
    def delete_maintainer(item_id):
        """删除条码维护人"""
        try:
            sql = "DELETE FROM barcode_maintainers WHERE id = %s"
            db_manager.execute(sql, [item_id])
            return jsonify({'success': True, 'message': '删除成功'})
        except Exception as e:
            log.error(f"[API] 删除维护人失败: {e}")
            traceback.print_exc()
            return jsonify({'success': False, 'message': '删除失败'}), 500

    return app
