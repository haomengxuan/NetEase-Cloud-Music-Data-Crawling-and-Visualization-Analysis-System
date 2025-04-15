# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
import re
import csv
import json
import time
import pymysql
import requests
import pandas as pd
import os
import hashlib
import random
from bs4 import BeautifulSoup
from datetime import datetime
from functools import wraps
import webbrowser

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'wymusic_crawler_secret_key'  # 用于session加密

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'db': 'wymusic',
    'charset': 'utf8mb4'
}

# 请求头配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'
}

# 确保必要的目录存在
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawler_data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 初始化数据库连接
def get_db_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

# 初始化数据库表
def init_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # 创建爬虫用户表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawler_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                status TINYINT DEFAULT 1
            )
            ''')
            
            # 创建爬取任务记录表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS crawler_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                task_type VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                params TEXT,
                result_file VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES crawler_users(id)
            )
            ''')
            
            conn.commit()
            print("数据库表初始化成功")
        except Exception as e:
            print(f"数据库表初始化失败: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

# 用户登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 首页路由
@app.route('/')
def index():
    return render_template('crawler_index.html')

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 密码加密
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT id, username FROM crawler_users WHERE username = %s AND password = %s', 
                              (username, hashed_password))
                user = cursor.fetchone()
                
                if user:
                    # 更新最后登录时间
                    cursor.execute('UPDATE crawler_users SET last_login = %s WHERE id = %s', 
                                  (datetime.now(), user[0]))
                    conn.commit()
                    
                    # 设置session
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    
                    flash('登录成功', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('用户名或密码错误', 'error')
            except Exception as e:
                flash(f'登录失败: {e}', 'error')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('无法连接到数据库', 'error')
            
    # 显示爬虫安全提示
    crawler_notices = [
        "请遵守网站的robots.txt规则，尊重服务器资源",
        "设置合理的爬取频率，避免对目标网站造成压力",
        "数据仅用于学习和研究，请勿用于商业用途",
        "爬取的内容可能受版权保护，请合法使用",
        "请勿爬取敏感或个人隐私信息"
    ]
    
    return render_template('crawler_login.html', notices=crawler_notices)

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        agreement = request.form.get('agreement')
        
        # 表单验证
        if not username or not password or not confirm_password:
            flash('用户名和密码不能为空', 'error')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return redirect(url_for('register'))
            
        if not agreement:
            flash('请阅读并同意爬虫使用条款', 'error')
            return redirect(url_for('register'))
        
        # 密码加密
        hashed_password = hashlib.md5(password.encode()).hexdigest()
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                # 检查用户名是否已存在
                cursor.execute('SELECT id FROM crawler_users WHERE username = %s', (username,))
                if cursor.fetchone():
                    flash('用户名已存在', 'error')
                    return redirect(url_for('register'))
                
                # 创建新用户
                cursor.execute('INSERT INTO crawler_users (username, password, email) VALUES (%s, %s, %s)',
                              (username, hashed_password, email))
                conn.commit()
                
                flash('注册成功，请登录', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                conn.rollback()
                flash(f'注册失败: {e}', 'error')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('无法连接到数据库', 'error')
    
    # 显示爬虫安全提示和使用条款
    crawler_terms = [
        "您承诺不会使用本工具进行任何违反法律法规的活动",
        "您理解并同意对爬取行为可能带来的法律风险负责",
        "您承诺合理设置爬取频率，不对目标网站造成负担",
        "您保证不会爬取他人隐私数据或敏感信息",
        "您同意仅将爬取的数据用于学习、研究等非商业用途",
        "您理解数据爬取可能受到相关法律法规的限制",
        "您承诺尊重数据来源网站的知识产权和使用条款"
    ]
    
    return render_template('crawler_register.html', terms=crawler_terms)

# 退出登录
@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

# 用户控制面板
@app.route('/dashboard')
@login_required
def dashboard():
    # 获取用户的爬取任务历史
    conn = get_db_connection()
    tasks = []
    if conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute('''
            SELECT id, task_type, status, created_at, result_file 
            FROM crawler_tasks 
            WHERE user_id = %s 
            ORDER BY created_at DESC
            ''', (session['user_id'],))
            tasks = cursor.fetchall()
        except Exception as e:
            flash(f'获取任务历史失败: {e}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    return render_template('crawler_dashboard.html', tasks=tasks)

# 爬取歌单信息
@app.route('/crawl/playlist', methods=['GET', 'POST'])
@login_required
def crawl_playlist():
    if request.method == 'POST':
        playlist_type = request.form.get('playlist_type', '')
        limit = int(request.form.get('limit', 10))
        
        # 参数验证
        if limit <= 0 or limit > 100:
            flash('爬取数量必须在1-100之间', 'error')
            return redirect(url_for('crawl_playlist'))
        
        # 创建任务记录
        conn = get_db_connection()
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
                    json.dumps({'playlist_type': playlist_type, 'limit': limit})
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
                result_file = crawl_playlist_data(playlist_type, limit, task_id)
                
                # 更新任务状态
                conn = get_db_connection()
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
            except Exception as e:
                # 更新任务状态为失败
                conn = get_db_connection()
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
    
    # 获取可用的歌单类型
    playlist_types = get_playlist_types()
    
    return render_template('crawler_playlist.html', playlist_types=playlist_types)

# 爬取歌曲信息
@app.route('/crawl/songs', methods=['GET', 'POST'])
@login_required
def crawl_songs():
    if request.method == 'POST':
        artist_id = request.form.get('artist_id', '')
        
        # 参数验证
        if not artist_id.isdigit():
            flash('歌手ID必须是数字', 'error')
            return redirect(url_for('crawl_songs'))
        
        # 创建任务记录
        conn = get_db_connection()
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
                    json.dumps({'artist_id': artist_id})
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
                result_file = crawl_songs_data(artist_id, task_id)
                
                # 更新任务状态
                conn = get_db_connection()
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
            except Exception as e:
                # 更新任务状态为失败
                conn = get_db_connection()
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
    
    return render_template('crawler_songs.html')

# 下载爬取结果
@app.route('/download/<filename>')
@login_required
def download_file(filename):
    # 验证文件属于当前用户
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
            SELECT id FROM crawler_tasks 
            WHERE user_id = %s AND result_file = %s
            ''', (session['user_id'], filename))
            if not cursor.fetchone():
                flash('没有权限下载此文件', 'error')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'验证文件权限失败: {e}', 'error')
            return redirect(url_for('dashboard'))
        finally:
            cursor.close()
            conn.close()
    
    # 文件路径修正
    file_path = os.path.join(DATA_DIR, filename)
    print(f"尝试下载文件: {file_path}")
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        # 如果找不到文件，创建一个空文件
        flash(f'文件 {filename} 不存在，已创建空文件', 'warning')
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['无数据'])
        return send_file(file_path, as_attachment=True)

# 获取歌单类型列表
def get_playlist_types():
    type_url = "https://music.163.com/discover/playlist"
    try:
        response = requests.get(url=type_url, headers=HEADERS)
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        types = [t.text for t in soup.select("a.s-fc1")][1:]
        return types
    except Exception as e:
        print(f"获取歌单类型失败: {e}")
        return ["华语", "流行", "摇滚", "民谣", "电子"]  # 默认类型

# 爬取歌单数据
def crawl_playlist_data(playlist_type, limit, task_id):
    print(f"开始爬取歌单，类型: {playlist_type}, 数量: {limit}")
    
    # 构造URL
    if playlist_type:
        url = f"https://music.163.com/discover/playlist/?order=hot&cat={playlist_type}&limit={limit}"
    else:
        url = f"https://music.163.com/discover/playlist/?order=hot&limit={limit}"
    
    # 获取歌单ID列表
    response = requests.get(url=url, headers=HEADERS)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    playlist_ids = [re.sub(r"\D+", "", i['href']) for i in soup.select("a.msk")][:limit]
    
    # 准备数据文件
    timestamp = int(time.time())
    result_file = f"playlist_{task_id}_{timestamp}.csv"
    result_path = os.path.join(DATA_DIR, result_file)
    
    # 写入表头
    with open(result_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            '歌单ID', '歌单名称', '歌单类型', '标签', '创建时间', '最后更新时间',
            '歌曲数量', '播放量', '收藏量', '分享量', '评论数',
            '创建者', '性别', '用户类型', 'VIP类型', '省份', '城市'
        ])
    
    # 爬取每个歌单的详细信息
    # 使用网易云音乐官方API直接获取，不使用第三方API避免连接问题
    playlist_api = "https://music.163.com/api/v3/playlist/detail?id={}"
    count = 0
    
    for playlist_id in playlist_ids:
        try:
            # 添加延迟，避免请求过于频繁
            time.sleep(random.uniform(1, 2))
            
            # 请求歌单详情
            url = playlist_api.format(playlist_id)
            response = requests.get(url=url, headers=HEADERS)
            if response.status_code != 200:
                print(f"请求失败: {url}, 状态码: {response.status_code}")
                continue
                
            json_data = response.json()
            if "playlist" not in json_data:
                # 尝试另一个API格式
                url = f"https://music.163.com/api/playlist/detail?id={playlist_id}"
                response = requests.get(url=url, headers=HEADERS)
                if response.status_code != 200:
                    print(f"请求失败: {url}, 状态码: {response.status_code}")
                    continue
                json_data = response.json()
                if "result" in json_data:
                    json_playlist = json_data["result"]
                else:
                    print(f"歌单数据格式错误: {url}")
                    continue
            else:
                json_playlist = json_data["playlist"]
            
            # 提取歌单信息
            try:
                playlistID = str(json_playlist.get("id", ""))
                name = json_playlist.get("name", "未知歌单")
                playlistType = playlist_type
                tags = "、".join(json_playlist.get("tags", [])) if "tags" in json_playlist else ""
                
                # 处理创建时间和更新时间
                createTime = ""
                updateTime = ""
                if "createTime" in json_playlist:
                    try:
                        createTime = time.strftime("%Y-%m-%d", time.localtime(int(str(json_playlist["createTime"])[:-3])))
                    except:
                        createTime = time.strftime("%Y-%m-%d", time.localtime(int(time.time())))
                if "updateTime" in json_playlist:
                    try:
                        updateTime = time.strftime("%Y-%m-%d", time.localtime(int(str(json_playlist["updateTime"])[:-3])))
                    except:
                        updateTime = time.strftime("%Y-%m-%d", time.localtime(int(time.time())))
                
                # 获取其他统计信息
                tracks_num = len(json_playlist.get("trackIds", [])) if "trackIds" in json_playlist else 0
                playCount = json_playlist.get("playCount", 0)
                subscribedCount = json_playlist.get("subscribedCount", 0)
                shareCount = json_playlist.get("shareCount", 0)
                commentCount = json_playlist.get("commentCount", 0)
                
                # 创建者信息
                creator = json_playlist.get('creator', {})
                nickname = creator.get('nickname', '未知用户')
                gender = '男' if str(creator.get('gender', 0)) == '1' else '女'
                userType = str(creator.get('userType', 0))
                vipType = str(creator.get('vipType', 0))
                province = str(creator.get('province', 0))
                city = str(creator.get('city', 0))
            
                # 处理省份和城市
                # 简化处理逻辑，防止出错
                if province == '1000000' or province == '0':
                    province = '海外'
                    city = '海外'
                if city == '0':
                    city = province
                
                # 写入数据
                playlist_info = [
                    playlistID, name, playlistType, tags, createTime, updateTime,
                    tracks_num, playCount, subscribedCount, shareCount, commentCount,
                    nickname, gender, userType, vipType, province, city
                ]
                
                with open(result_path, 'a', encoding='utf-8', newline='') as f:
                    csv.writer(f).writerow(playlist_info)
                
                count += 1
                print(f"已爬取歌单 {count}/{len(playlist_ids)}: {name}")
            except Exception as e:
                print(f"处理歌单数据失败: {e}")
            
        except Exception as e:
            print(f"爬取歌单 {playlist_id} 失败: {e}")
    
    print(f"爬取完成，共 {count} 个歌单，结果保存在 {result_file}")
    return result_file

# 爬取歌曲数据
def crawl_songs_data(artist_id, task_id):
    print(f"开始爬取歌手ID为 {artist_id} 的歌曲")
    
    # 构造URL
    url = f"https://music.163.com/artist?id={artist_id}"
    
    # 发送请求
    html = None
    try:
        # 添加更多的请求头，模拟正常浏览器行为
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36 Edg/84.0.522.63",
            "Referer": "https://music.163.com/",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # 添加重试机制
        session = requests.Session()
        retry = 0
        max_retries = 3
        while retry < max_retries:
            try:
                response = session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                html = response.text
                break
            except requests.RequestException as e:
                retry += 1
                print(f"请求失败 (尝试 {retry}/{max_retries}): {e}")
                if retry >= max_retries:
                    raise Exception(f"请求失败: {e}")
                time.sleep(2)  # 等待后重试
    except Exception as e:
        raise Exception(f"请求失败: {e}")
    
    # 解析歌曲信息
    try:
        soup = BeautifulSoup(html, 'html.parser')
        targets = soup.find('ul', {'class': 'f-hide'})
        if not targets:
            # 尝试直接使用API获取歌曲列表
            api_url = f"https://music.163.com/api/artist/songs?id={artist_id}&limit=100&offset=0"
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                songs_data = response.json()
                if 'songs' in songs_data:
                    # 准备数据文件
                    timestamp = int(time.time())
                    result_file = f"songs_{task_id}_{timestamp}.csv"
                    result_path = os.path.join(DATA_DIR, result_file)
                    
                    # 保存数据
                    song_data = []
                    for song in songs_data['songs']:
                        song_data.append([
                            song.get('name', ''),
                            f"https://music.163.com/song?id={song.get('id', '')}",
                            song.get('artists', [{}])[0].get('name', 'Unknown'),
                            song.get('album', {}).get('name', 'Unknown')
                        ])
                    
                    df = pd.DataFrame(song_data, columns=['Song', 'Address', 'Singer', 'Album'])
                    df.to_csv(result_path, index=False, encoding='utf-8-sig')
                    print(f"数据已保存到 {result_file} 文件中")
                    return result_file
            raise Exception("未找到歌曲列表，请检查页面结构是否发生变化")
        
        message = targets.find_all('a')
        
        # 准备数据文件
        timestamp = int(time.time())
        result_file = f"songs_{task_id}_{timestamp}.csv"
        result_path = os.path.join(DATA_DIR, result_file)
        
        # 创建DataFrame保存数据
        song_data = []
        
        for i in message:
            try:
                song_name = i.text
                song_id = i["href"].split("=")[-1]
                song_address = f"https://music.163.com/song?id={song_id}"
                
                # 添加延迟，避免请求过于频繁
                time.sleep(random.uniform(0.5, 1.5))
                
                # 尝试直接从API获取歌曲信息
                api_url = f"https://music.163.com/api/song/detail/?id={song_id}&ids=[{song_id}]"
                try:
                    response = requests.get(api_url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        song_json = response.json()
                        if 'songs' in song_json and len(song_json['songs']) > 0:
                            song_info = song_json['songs'][0]
                            singer = song_info.get('artists', [{}])[0].get('name', 'Unknown')
                            album = song_info.get('album', {}).get('name', 'Unknown')
                            song_data.append([song_name, song_address, singer, album])
                            print(f"已爬取歌曲: {song_name}")
                            continue
                except Exception as e:
                    print(f"API获取歌曲 {song_name} 详情失败: {e}")
                
                # 如果API获取失败，尝试页面解析（备用方法）
                try:
                    song_response = requests.get(song_address, headers=headers, timeout=10)
                    song_response.raise_for_status()
                    song_html = song_response.text
                    
                    song_soup = BeautifulSoup(song_html, 'html.parser')
                    targets1 = song_soup.find_all('a', {'class': 's-fc7'})
                    
                    singer = targets1[1].text if len(targets1) > 1 else "Unknown"
                    album = targets1[2].text if len(targets1) > 2 else "Unknown"
                    
                    song_data.append([song_name, song_address, singer, album])
                    print(f"已爬取歌曲: {song_name}")
                    
                except Exception as e:
                    print(f"HTML解析歌曲 {song_name} 详情失败: {e}")
                    # 只保存基本信息
                    song_data.append([song_name, song_address, "Unknown", "Unknown"])
                
            except Exception as e:
                print(f"爬取歌曲信息失败: {e}")
        
        # 保存数据到CSV
        if song_data:
            df = pd.DataFrame(song_data, columns=['Song', 'Address', 'Singer', 'Album'])
            df.to_csv(result_path, index=False, encoding='utf-8-sig')
            print(f"数据已保存到 {result_file} 文件中")
        else:
            raise Exception("未获取到有效数据")
        
        return result_file
    except Exception as e:
        print(f"解析歌曲数据失败: {e}")
        raise e

# 从Flask导入文件发送功能
from flask import send_file

# 初始化数据库
init_db()

# 运行应用
if __name__ == "__main__":
    # 自动打开浏览器访问应用
    webbrowser.open('http://localhost:5001')
    # 启动Flask应用
    app.run(debug=True, port=5001)  # 使用不同的端口，避免与主应用冲突 