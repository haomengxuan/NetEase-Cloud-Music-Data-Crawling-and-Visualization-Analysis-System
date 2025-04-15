# 任务完成后显示结果页面
@app.route('/task_result/<task_id>')
@login_required
def task_result(task_id):
    # 获取任务信息
    conn = get_db_connection()
    task_data = None
    if conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute('''
            SELECT id, task_type, status, result_file, params, created_at
            FROM crawler_tasks 
            WHERE id = %s AND user_id = %s
            ''', (task_id, session['user_id']))
            task_data = cursor.fetchone()
        except Exception as e:
            flash(f'获取任务信息失败: {e}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    if not task_data:
        flash('没有找到任务信息', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('crawler_task_result.html', task=task_data) 