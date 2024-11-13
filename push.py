import requests
import json
import lineconfig
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, select, func
import sqlite3
import os
import datetime
import lineconfig


# インスタンス生成
app = Flask(__name__)

# Flaskに対する設定
app.config['SECRET_KEY'] = os.urandom(24)
base_dir = os.path.dirname(__file__)
database = 'sqlite:///' + os.path.join(base_dir, 'line_data.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# db変数を使用してSQLAlchemyを操作できる
db = SQLAlchemy(app)

# データベースに接続
connection = sqlite3.connect("line_data.sqlite", check_same_thread=False)
cursor = connection.cursor()


# モデル
class Message(db.Model):
    __tablename__ = 'Messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String(200), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    number = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.String(200), nullable=False)
    task_id = db.Column(db.Integer, autoincrement=True)
    status = db.Column(db.String(200), nullable=False, default='idle')

#タスクモデル
class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    user_id = db.Column(db.String(200), nullable=False)
    task_name = db.Column(db.String(200), nullable=False, default='未定')
    daily_goal = db.Column(db.Integer, nullable=False, default=0)
    is_done = db.Column(db.Boolean, nullable=False, default=0) #タスク実行したかどうか
    enable = db.Column(db.Boolean, nullable=False, default=True)
    report = db.Column(db.Integer, nullable=False, default=0)

# DB作成
def init_db():
    with app.app_context():
        db.create_all()

headers={
   'Content-Type': 'application/json',
   'Authorization': "Bearer "+lineconfig.CHANNELACCESSTOKEN
}
#rows = cursor.execute('SELECT DISTINCT user_id FROM tasks').fetchall()
#user_ids = [row[0] for row in rows]

# メイン処理
with app.app_context():
    #タスクテーブルのuser_idを被り無しで取得
    user_ids = db.session.query(Task.user_id).distinct().all()
    user_ids = [user_id[0] for user_id in user_ids]     #タプルを解除してリストに
    if len(user_ids) == 0:
        print('ユーザーがいません')
        exit()
    else:
        for user_id_from_line in user_ids:
            #task.do_taskが0のものを取得
            tasks = Task.query.filter(Task.user_id == user_id_from_line, Task.enable == True ,Task.is_done == 0).all()
            print(user_id_from_line)
            if tasks == []:
                text = '未実行タスクはありません\n明日も頑張りましょう！'
            else:
                text = '未実行タスクがあります\n\n未実行タスク一覧\n'
                for task in tasks:
                    text += f'{task.task_name}: {task.daily_goal}\n'
                text += 'タスクを実行しましょう！'
                print(text)
            payload={
                    'to':user_id_from_line,
                    'messages':[
                        {
                        'type':'text',
                        'text':text
                        }
                    ]
                }
            Message05 = Message(content=text, time=datetime.datetime.now(), number = 0, user_id = 'line')            
            db.session.add(Message05)
            db.session.commit()
            response = requests.post(lineconfig.PUSHAPIURL, data=json.dumps(payload),headers=headers)
            print(response.status_code) 
            print(response.text) 