#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网易云音乐爬虫系统 - 集成数据可视化功能
"""
import os
import sys

# 将当前目录添加到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入原有的爬虫模块
try:
    import crawler_module
    print("成功导入爬虫模块")
except ImportError as e:
    print(f"无法导入爬虫模块: {e}")
    sys.exit(1)

# 导入Flask相关库
from flask import Flask, redirect, url_for, flash, render_template, session, request
import webbrowser

# 声明应用
app = crawler_module.app

# 任务完成后显示结果页面
@app.route('/task_result/<task_id>')
@crawler_module.login_required
def task_result(task_id):
    # 获取任务信息
    conn = crawler_module.get_db_connection()
    task_data = None
    if conn:
        cursor = conn.cursor(crawler_module.pymysql.cursors.DictCursor)
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

# 修改爬取歌单的后处理逻辑
original_crawl_playlist = crawler_module.crawl_playlist

# 重写路由，使用不同的路由名称避免冲突
@app.route('/integrated/crawl/playlist', methods=['GET', 'POST'])
@crawler_module.login_required
def integrated_crawl_playlist():
    if request.method == 'GET':
        # 使用原有的GET请求处理
        return original_crawl_playlist()
    
    # 处理POST请求
    playlist_type = request.form.get('playlist_type', '')
    limit = int(request.form.get('limit', 10))
    
    # 参数验证
    if limit <= 0 or limit > 100:
        flash('爬取数量必须在1-100之间', 'error')
        return redirect(url_for('crawl_playlist'))
    
    # 创建任务记录
    conn = crawler_module.get_db_connection()
    task_id = None
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO crawler_tasks (user_id, task_type, status, params) 
            VALUES (%s, %s, %s, %s)
            ''', (
                session['user_id'], 
                '歌单爬取', 
                '进行中',
                crawler_module.json.dumps({'playlist_type': playlist_type, 'limit': limit})
            ))
            conn.commit()
            task_id = cursor.lastrowid
        except Exception as e:
            conn.rollback()
            flash(f'创建任务失败: {e}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    if task_id:
        # 执行爬取任务
        try:
            result_file = crawler_module.crawl_playlist_data(playlist_type, limit, task_id)
            
            # 更新任务状态
            conn = crawler_module.get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                    UPDATE crawler_tasks 
                    SET status = %s, result_file = %s 
                    WHERE id = %s
                    ''', ('完成', result_file, task_id))
                    conn.commit()
                    flash('爬取任务完成', 'success')
                except Exception as e:
                    conn.rollback()
                    flash(f'更新任务状态失败: {e}', 'error')
                finally:
                    cursor.close()
                    conn.close()
            # 重定向到任务结果页面
            return redirect(url_for('task_result', task_id=task_id))
        except Exception as e:
            # 更新任务状态为失败
            conn = crawler_module.get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                    UPDATE crawler_tasks 
                    SET status = %s 
                    WHERE id = %s
                    ''', ('失败', task_id))
                    conn.commit()
                except:
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()
            
            flash(f'爬取失败: {e}', 'error')
    
    return redirect(url_for('dashboard'))

# 修改爬取歌曲的后处理逻辑
original_crawl_songs = crawler_module.crawl_songs

# 重写路由，使用不同的路由名称避免冲突
@app.route('/integrated/crawl/songs', methods=['GET', 'POST'])
@crawler_module.login_required
def integrated_crawl_songs():
    if request.method == 'GET':
        # 使用原有的GET请求处理
        return original_crawl_songs()
    
    # 处理POST请求
    artist_id = request.form.get('artist_id', '')
    
    # 参数验证
    if not artist_id.isdigit():
        flash('歌手ID必须是数字', 'error')
        return redirect(url_for('crawl_songs'))
    
    # 创建任务记录
    conn = crawler_module.get_db_connection()
    task_id = None
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO crawler_tasks (user_id, task_type, status, params) 
            VALUES (%s, %s, %s, %s)
            ''', (
                session['user_id'], 
                '歌曲爬取', 
                '进行中',
                crawler_module.json.dumps({'artist_id': artist_id})
            ))
            conn.commit()
            task_id = cursor.lastrowid
        except Exception as e:
            conn.rollback()
            flash(f'创建任务失败: {e}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    if task_id:
        # 执行爬取任务
        try:
            result_file = crawler_module.crawl_songs_data(artist_id, task_id)
            
            # 更新任务状态
            conn = crawler_module.get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                    UPDATE crawler_tasks 
                    SET status = %s, result_file = %s 
                    WHERE id = %s
                    ''', ('完成', result_file, task_id))
                    conn.commit()
                    flash('爬取任务完成', 'success')
                except Exception as e:
                    conn.rollback()
                    flash(f'更新任务状态失败: {e}', 'error')
                finally:
                    cursor.close()
                    conn.close()
            # 重定向到任务结果页面
            return redirect(url_for('task_result', task_id=task_id))
        except Exception as e:
            # 更新任务状态为失败
            conn = crawler_module.get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                    UPDATE crawler_tasks 
                    SET status = %s 
                    WHERE id = %s
                    ''', ('失败', task_id))
                    conn.commit()
                except:
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()
            
            flash(f'爬取失败: {e}', 'error')
    
    return redirect(url_for('dashboard'))

# 数据可视化路由
@app.route('/visualization/<task_id>')
@crawler_module.login_required
def data_visualization(task_id):
    # 获取任务信息
    conn = crawler_module.get_db_connection()
    task_data = None
    if conn:
        cursor = conn.cursor(crawler_module.pymysql.cursors.DictCursor)
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
    file_path = os.path.join(crawler_module.DATA_DIR, task_data['result_file'])
    if not os.path.exists(file_path):
        flash('数据文件不存在', 'error')
        return redirect(url_for('dashboard'))
    
    # 根据任务类型处理不同格式的数据
    visualization_data = {}
    task_type = task_data['task_type']
    
    try:
        df = crawler_module.pd.read_csv(file_path, encoding='utf-8-sig')
        
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
                df['播放量区间'] = crawler_module.pd.cut(df['播放量'], bins, labels=labels)
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
                df['创建年份'] = crawler_module.pd.to_datetime(df['创建时间'], errors='coerce').dt.year
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

# 运行应用
if __name__ == "__main__":
    # 初始化数据库
    crawler_module.init_db()
    
    # 自动打开浏览器访问应用
    webbrowser.open('http://localhost:5001')
    
    # 启动Flask应用
    app.run(debug=True, port=5001)  # 使用不同的端口，避免与主应用冲突 