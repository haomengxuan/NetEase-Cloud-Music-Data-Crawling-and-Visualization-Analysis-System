import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# 目标歌手的 ID 和 URL
artist_id = "6462"
url = f"https://music.163.com/artist?id={artist_id}"

# 请求头，模拟浏览器行为
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36 Edg/84.0.522.63",
    "Referer": "https://music.163.com/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

# 使用代理（如果需要）
# proxies = {
#     "http": "http://your_proxy_ip:port",
#     "https": "http://your_proxy_ip:port"
# }

# 发送请求
def fetch_page(url, headers):
    try:
        response = requests.get(url, headers=headers)  # proxies=proxies 如果需要使用代理
        response.raise_for_status()  # 检查请求是否成功
        return response.text
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return None

# 解析歌曲信息
def parse_songs(html):
    soup = BeautifulSoup(html, 'html.parser')
    targets = soup.find('ul', {'class': 'f-hide'})
    if not targets:
        print("未找到歌曲列表，请检查页面结构是否发生变化。")
        return []

    message = targets.find_all('a')
    song_data = []

    for i in message:
        song_name = i.text
        song_id = i["href"].split("=")[-1]
        song_address = f"https://music.163.com/song?id={song_id}"

        # 请求歌曲详情页
        song_html = fetch_page(song_address, headers)
        if not song_html:
            continue

        song_soup = BeautifulSoup(song_html, 'html.parser')
        targets1 = song_soup.find_all('a', {'class': 's-fc7'})

        try:
            singer = targets1[1].text
            album = targets1[2].text
        except IndexError:
            singer = "Unknown"
            album = "Unknown"

        song_data.append([song_name, song_address, singer, album])

        # 随机等待，避免被封禁
        time.sleep(random.uniform(1, 3))

    return song_data

# 主程序
if __name__ == "__main__":
    html = fetch_page(url, headers)
    if html:
        song_data = parse_songs(html)
        if song_data:
            df = pd.DataFrame(song_data, columns=['Song', 'Address', 'Singer', 'Album'])
            df.to_csv('song.csv', index=False, encoding='utf-8-sig')
            print("数据已保存到 song.csv 文件中。")
        else:
            print("未获取到有效数据。")