from flask import Flask, render_template, url_for, request, jsonify
import json
import pandas as pd
import pymysql
import re
import traceback

# 设置全局变量，方便错误处理
df = None
conn = None
cursor = None

try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='123456',
        db='wymusic',
        charset='utf8'
    )
    cursor = conn.cursor()
    print("MySQL连接成功")
except Exception as e:
    print(f"MySQL连接失败: {e}")

app = Flask(__name__)

try:
    from sqlalchemy import create_engine
    engine = create_engine("mysql+pymysql://root:123456@localhost/wymusic")
    print("SQLAlchemy引擎创建成功")
    
    # 尝试加载数据
    try:
        df = pd.read_sql('select * from music', engine)
        print(f"成功从数据库加载了 {len(df)} 条记录")
    except Exception as e:
        print(f"无法从数据库加载数据: {e}")
        df = pd.DataFrame()  # 创建空DataFrame避免后续错误
except Exception as e:
    print(f"SQLAlchemy引擎创建失败: {e}")
    df = pd.DataFrame()  # 创建空DataFrame避免后续错误

"""最受欢迎的歌单类型"""


@app.route('/get_hot_type')
def get_hot_type():
    try:
        # 检查必要的列是否存在
        if 'type' not in df.columns or 'play_count' not in df.columns:
            return json.dumps({'error': '数据缺少必要的列'}, ensure_ascii=False)
        
        # 安全地执行分组操作
        hot_type_df = df[['type', 'play_count']].groupby('type').sum().reset_index()
        
        # 如果没有足够的数据，返回空结果
        if hot_type_df.empty:
            return json.dumps({'playlist_type': [], 'play_count': []}, ensure_ascii=False)
        
        # 按播放量排序
        hot_type_df = hot_type_df.sort_values('play_count', ascending=False)
        
        # 获取前7个（如果有的话）
        limit = min(7, len(hot_type_df))
        hot_type_top7 = hot_type_df.head(limit)
        
        playlist_type = hot_type_top7['type'].tolist()
        play_count = hot_type_top7['play_count'].tolist()

        return json.dumps({'playlist_type': playlist_type, 'play_count': play_count}, ensure_ascii=False)
    except Exception as e:
        print(f"get_hot_type错误: {e}")
        return json.dumps({'error': str(e)}, ensure_ascii=False)


"""歌单数据随月份变化"""


@app.route('/get_month_data')
def get_month_data():
    yearList = []
    month_list = []

    for year in ['2018', '2019']:
        df_filtered = df[df['create_time'].str[:4] == year]
        reset_df = df_filtered.groupby(df_filtered['create_time'].str[5:7]).sum().reset_index(
            drop=True)  # drop=True 删除重复插入列的行
        reset_df = reset_df.drop('create_time', axis=1)
        share_count = reset_df['share_count'].tolist()
        comment_count = reset_df['comment_count'].tolist()
        month = reset_df.index.tolist()  # 使用索引号作为月份

        yearList.append({
            "year": year,
            "data": [
                share_count,
                comment_count
            ]
        })

    df_temp = df[df['create_time'].str[:4] == '2019']
    print(df_temp)
    month = df_temp.groupby(df_temp['create_time'].str[5:7])
    month = month.sum()
    month['create_time'] = month.index
    month = month.rename(columns={'create_time': 'month', 'share_count': 'total_share_count',
                                  'comment_count': 'total_comment_count'})
    month_list = [str(int(x)) + '月' for x in month['month']]

    yearData = {
        "yearData": yearList,
        "monthList": month_list
    }

    return json.dumps(yearData, ensure_ascii=False)


"""歌单数据随天数变化"""


@app.route('/get_day_data')
def get_day_data():
    non_vip_df = df[df['vip_type'] == 0].groupby(df['create_time'].str[8:10]).sum().reset_index(drop=True)[
        ['subscribed_count']]
    vip_df = df[(df['vip_type'] == 10) | (df['vip_type'] == 11)].groupby(df['create_time'].str[8:10]).sum().reset_index(
        drop=True)[['subscribed_count']]
    vip_type_df = pd.merge(non_vip_df, vip_df, left_index=True, right_index=True, how='inner')

    sub_data = {
        "day": vip_type_df.index.astype(str).tolist(),
        "vip": vip_type_df["subscribed_count_y"].tolist(),
        "nonvip": vip_type_df["subscribed_count_x"].tolist()
    }

    return json.dumps(sub_data, ensure_ascii=False)


"""歌单歌曲数量分布"""


@app.route('/get_track_data')
def get_track_data():
    bins = [0, 50, 150, 500, 100000]
    cuts = pd.cut(df['tracks_num'], bins=bins, right=False, include_lowest=True)
    data_count = cuts.value_counts()
    data = dict(zip([str(x) for x in data_count.index.tolist()], data_count.tolist()))
    map_data = [{'name': name, 'value': value} for name, value in data.items()]
    track_value = {'t_v': map_data}

    return json.dumps(track_value, ensure_ascii=False)


"""语种类型歌单播放量"""


@app.route('/get_type_data')
def get_type_data():
    try:
        # 检查gender列是否存在
        if 'gender' not in df.columns:
            return json.dumps({'error': '数据缺少gender列'}, ensure_ascii=False)
        
        # 安全统计性别数据
        gender_counts = df['gender'].value_counts()
        gender_data = []
        
        # 添加男性数据（如果存在）
        if '男' in gender_counts:
            gender_data.append({'name': '男', 'value': int(gender_counts['男'])})
        else:
            gender_data.append({'name': '男', 'value': 0})
            
        # 添加女性数据（如果存在）
        if '女' in gender_counts:
            gender_data.append({'name': '女', 'value': int(gender_counts['女'])})
        else:
            gender_data.append({'name': '女', 'value': 0})
            
        type_sum = {'t_s': gender_data}
        return json.dumps(type_sum, ensure_ascii=False)
    except Exception as e:
        print(f"get_type_data错误: {e}")
        return json.dumps({'error': str(e)}, ensure_ascii=False)


def replace_str(x):
    rep_list = ['省', '市', '维吾尔', '自治区', '壮族', '回族', '维吾尔族', '特别行政区']
    for rep in rep_list:
        x = re.sub(rep, '', x)
    return x


def add_province(df_data, province):
    # 所有年份
    years = df_data['create_time'].drop_duplicates().tolist()
    for year in years:
        # 每年的省份
        new_province = df_data.loc[df_data['create_time'] == year, :]['province'].drop_duplicates().tolist()
        # 缺失的省份 = 所有省份 - 每年的省份
        rest_province = [x for x in province if x not in new_province]
        # 对缺失的省份生成一个DataFrame，填充0值，并与原DataFrame合并
        if len(rest_province):
            rest_df = pd.DataFrame([[year, x, 0, 0] for x in rest_province], columns=df_data.columns)
            df_data = pd.concat([df_data, rest_df], ignore_index=True)

    return df_data


"""动态地图"""


@app.route('/get_map_data')
def get_map_data():
    time_df = df.groupby([df['create_time'].str[:4], df['province'].apply(replace_str)])[
        ['play_count', 'share_count']].count().reset_index()
    re_time_df = time_df[time_df['province'] != '海外']
    province = re_time_df['province'].drop_duplicates().tolist()

    re_time_df2 = add_province(re_time_df, province)

    final_time_df = re_time_df2.sort_values(by=['create_time', 'province']).reset_index(drop=True)
    final_province = final_time_df['province'].drop_duplicates().tolist()
    final_year = final_time_df['create_time'].drop_duplicates().tolist()

    playlist_num = []
    for year in final_year:
        playlist_num.append(final_time_df.loc[final_time_df['create_time'] == year, 'play_count'].tolist())

    playlist_data = {"year": final_year, "province": final_province, "playlist_num": playlist_num}

    return json.dumps(playlist_data, ensure_ascii=False)


@app.route('/')
def login():
    return render_template('login.html')


@app.route('/dologin', methods=['GET', 'POST'])
def dologin():
    username = request.form.get('username')
    password = request.form.get('password')
    select_sql = 'select password from user where username = %s'
    cursor.execute(select_sql, (username,))
    result = cursor.fetchone()
    
    if result is None:
        return 'error'  # 用户不存在
        
    select_password = result[0]

    if password == select_password:
        return 'success'  # 返回一个成功的状态码
    else:
        return 'error'  # 返回一个错误的状态码

@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/doregister',methods=['GET','POST'])
def doregister():
    username = request.form.get('username')
    password = request.form.get('password')
    print(username,password)
    select_sql = 'select username from user where username = %s'
    cursor.execute(select_sql, (username,))
    exist_username = cursor.fetchone()

    if exist_username is None and len(password) > 0:
        insert_user_sql = 'insert into user (username,password) values(%s,%s)'
        cursor.execute(insert_user_sql, (username, password))
        conn.commit()
        return 'success'
    else:
        return 'error'
@app.route('/index')
def index():
    try:
        # 检查df中是否有数据
        if df.empty:
            return "数据库中没有数据，请先导入数据。"
        
        # 检查df中是否包含gender列
        if 'gender' not in df.columns:
            return "数据缺少gender列，请检查数据库结构。"
        
        # 检查是否有男女性别数据
        gender_counts = df['gender'].value_counts()
        gender_data = {}
        
        if '男' in gender_counts:
            gender_data['男'] = int(gender_counts['男'])
        else:
            gender_data['男'] = 0
            
        if '女' in gender_counts:
            gender_data['女'] = int(gender_counts['女'])
        else:
            gender_data['女'] = 0
        
        # 安全地读取CSV文件
        try:
            df1 = pd.read_csv(r'D:\桌面\4.8-eh-ma-wangyiyun\code\code\song.csv')
            songlist = list(df1.values)[:5] if not df1.empty else []
        except Exception as e:
            print(f"读取song.csv出错: {e}")
            songlist = []
        
        return render_template('index.html', gender_data=gender_data, songlist=songlist)
    except Exception as e:
        print(f"index函数错误: {e}")
        return f"发生错误: {str(e)}"


if __name__ == "__main__":
    app.debug = True  # 启用调试模式，显示详细错误信息
    app.run()
