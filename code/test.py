# -*- coding: utf-8 -*-

import pandas as pd

cols = ['id','name','type','tags','create_time','update_time','tracks_num','play_count','subscribed_count','share_count','comment_count','nickname','gender','user_type','vip_type','province','city']
df = pd.read_csv('wymusic.csv',sep='\t',names=cols)
print(df['name'])
from sqlalchemy import create_engine
engine = create_engine("mysql://root:123456@localhost/wymusic")
df.to_sql('music',engine,if_exists='append',index=False)
