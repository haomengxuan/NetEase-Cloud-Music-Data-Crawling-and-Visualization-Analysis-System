# 数据可视化路由
@app.route('/visualization/<task_id>')
@login_required
def data_visualization(task_id):
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
    
    if not task_data or task_data['status'] != '完成' or not task_data['result_file']:
        flash('没有找到可视化数据', 'error')
        return redirect(url_for('dashboard'))
    
    # 读取CSV数据
    file_path = os.path.join(DATA_DIR, task_data['result_file'])
    if not os.path.exists(file_path):
        flash('数据文件不存在', 'error')
        return redirect(url_for('dashboard'))
    
    # 根据任务类型处理不同格式的数据
    visualization_data = {}
    task_type = task_data['task_type']
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        
        if task_type == '歌单爬取':
            # 歌单数据可视化
            visualization_data = {
                'type': '歌单分析',
                'raw_data': df.to_dict('records')[:20],  # 限制展示20条原始数据
                'chart_data': {}
            }
            
            # 播放量分布
            play_count_data = {}
            if '播放量' in df.columns:
                bins = [0, 10000, 50000, 100000, 500000, 1000000, float('inf')]
                labels = ['<1万', '1-5万', '5-10万', '10-50万', '50-100万', '>100万']
                df['播放量区间'] = pd.cut(df['播放量'], bins, labels=labels)
                play_count_distribution = df['播放量区间'].value_counts().to_dict()
                play_count_data = {
                    'labels': list(play_count_distribution.keys()),
                    'data': list(play_count_distribution.values())
                }
                visualization_data['chart_data']['play_count'] = play_count_data
            
            # 标签词云
            tag_data = {}
            if '标签' in df.columns:
                all_tags = []
                for tags in df['标签'].dropna():
                    all_tags.extend([tag.strip() for tag in str(tags).split('、') if tag.strip()])
                
                tag_counts = {}
                for tag in all_tags:
                    if tag in tag_counts:
                        tag_counts[tag] += 1
                    else:
                        tag_counts[tag] = 1
                
                # 按出现次数排序
                sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:30]
                tag_data = {
                    'words': [{'text': tag, 'weight': count} for tag, count in sorted_tags]
                }
                visualization_data['chart_data']['tags'] = tag_data
            
            # 创建时间统计
            time_data = {}
            if '创建时间' in df.columns:
                df['创建年份'] = pd.to_datetime(df['创建时间'], errors='coerce').dt.year
                year_counts = df['创建年份'].value_counts().sort_index().to_dict()
                time_data = {
                    'labels': list(map(str, year_counts.keys())),
                    'data': list(year_counts.values())
                }
                visualization_data['chart_data']['creation_time'] = time_data
            
        elif task_type == '歌曲爬取':
            # 歌曲数据可视化
            visualization_data = {
                'type': '歌曲分析',
                'raw_data': df.to_dict('records')[:20],  # 限制展示20条原始数据
                'chart_data': {}
            }
            
            # 歌手分布
            singer_data = {}
            if 'Singer' in df.columns:
                singer_counts = df['Singer'].value_counts().head(10).to_dict()
                singer_data = {
                    'labels': list(singer_counts.keys()),
                    'data': list(singer_counts.values())
                }
                visualization_data['chart_data']['singers'] = singer_data
            
            # 专辑分布
            album_data = {}
            if 'Album' in df.columns:
                album_counts = df['Album'].value_counts().head(10).to_dict()
                album_data = {
                    'labels': list(album_counts.keys()),
                    'data': list(album_counts.values())
                }
                visualization_data['chart_data']['albums'] = album_data
    
    except Exception as e:
        flash(f'处理数据失败: {e}', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('crawler_visualization.html', task=task_data, visualization=visualization_data) 