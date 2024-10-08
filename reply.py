from flask import Flask, request
import requests
import json
import lineconfig
import openaiconfig
from openai import OpenAI
import schedule
import time
import datetime
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, select, func
import sqlite3


time_short = 7
time_long = 15

messages=[]
client = OpenAI()

# システムのプロンプト
system_content = """
あなたは私の習慣化サポーターです。標準語で会話し応援します．
"""

# 初期メッセージリスト
messages=[{"role":"system", "content":system_content}]

def get_reply(user_message):

    user_message = user_message
    messages.append({"role":"user","content":user_message})

    # OpenAI APIの呼び出し
    response = client.chat.completions.create(
        model=openaiconfig.model,
        messages=messages
    )
    messages.append(response.choices[0].message)

    return response.choices[0].message.content

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

# ユーザーモデル
class User(db.Model):
    user_id = db.Column(db.String(200), primary_key=True, unique=True, nullable=False)

#タスクモデル
class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    time = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.String(200), nullable=False)

# モデル
class Message(db.Model):
    __tablename__ = 'Massages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String(200), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    #ユーザーかそれ以外かを0か1で表す
    #user = db.Column(db.Integer, nullable=False, default=0)
    number = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.String(200), nullable=False)
    task_id = db.Column(db.Integer, autoincrement=True)

    def __str__(self):
        return f'順番:{self.id} 內容:{self.number}'

# DB作成
def init_db():
    with app.app_context():
        db.create_all()


@app.route('/callback', methods=['POST'])
def response():
    posted_data=request.data
    posted_object=json.loads(posted_data.decode('utf8'))
    # ユーザーIDの取得
    user_id_from_line = posted_object['events'][0]['source']['userId']
    # ユーザーIDがデータベースに存在するか確認
    user = User.query.filter_by(user_id=user_id_from_line).first()
    # ユーザーが存在しない場合は新しく作成
    if not user:
        user = User(user_id=user_id_from_line)
        db.session.add(user)
        db.session.commit()
        print(f"新しいユーザーを登録しました: {user_id_from_line}")
    response_to_line=''
    print("=request from LINE Messaging API")
    print(request.data) ## or request.get_data()
    print("---")
    print(posted_object['events'][0]['message']['text'])
    # CRUD操作
    with app.app_context():
        print('=========1件登録=========')
        if posted_object['events'][0]['message']['text'] == '7分':
            #timeが7分以内のもののnumberの合計を取得
            seven_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=time_short)
            total = db.session.query(func.sum(Message.number)).filter(Message.time >= seven_minutes_ago, Message.user_id == posted_object['events'][0]['source']['userId']).scalar()
            text = '7分以内の合計は、' + str(total) + 'です。'
            Message04 = Message(content=posted_object['events'][0]['message']['text'], time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
        elif posted_object['events'][0]['message']['text'] == '15分':
            #timeが30分以内のもののnumberの合計を取得
            thirty_days_ago = datetime.datetime.now() - datetime.timedelta(minutes=time_long)
            total = db.session.query(func.sum(Message.number)).filter(Message.time >= thirty_days_ago, Message.user_id == posted_object['events'][0]['source']['userId']).scalar()
            text = '15分以内の合計は、' + str(total) + 'です。'
            Message04 = Message(content=posted_object['events'][0]['message']['text'], time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
        elif posted_object['events'][0]['message']['text'] == '合計':
            #numberの合計を取得ただし、userが1のものだけ
            total = db.session.query(func.sum(Message.number)).filter(Message.user_id == posted_object['events'][0]['source']['userId']).scalar()
            text = '合計は、' + str(total) + 'です。'
            Message04 = Message(content=posted_object['events'][0]['message']['text'], time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
        else:
            #posted_object['events'][0]['message']['text']が数字かどうかを判定
            try:
                int(posted_object['events'][0]['message']['text'])
            except ValueError:
                text = get_reply(posted_object['events'][0]['message']['text'])
                Message04 = Message(content=posted_object['events'][0]['message']['text'], time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
            else:
                text = posted_object['events'][0]['message']['text']+'を記録しました'
                Message04 = Message(content=posted_object['events'][0]['message']['text'], time=datetime.datetime.now(), number = posted_object['events'][0]['message']['text'], user_id = posted_object['events'][0]['source']['userId'])
        db.session.add(Message04)
        db.session.commit()
        print('登録 =>', Message04)
        # テーブルのレコード数を取得
        cursor.execute("SELECT COUNT(*) FROM talks")
        count = cursor.fetchone()[0]
        print(count)
        print('=========１件取得==========')

        """
        if count > 1:
            target = Message.query.filter_by(id=count-2).first()
            print('取得 =>', target.content)
            text = '前回の会話は、' + target.content
        else:
            text = '初めての会話です'
        """

    # 本当に LINE Messaging API からの POST か?
    # 本当はイベントタイプがmessageであることもヘッダーから確認する必要 https://developers.line.biz/ja/docs/messaging-api/receiving-messages/
    if not lineconfig.validate_signature(request.get_data(as_text=True),request.headers['x-line-signature']):
        print("signature mismatch")
        # do nothing
        return response_to_line
    
    headers={
       'Content-Type': 'application/json',
       'Authorization': "Bearer "+lineconfig.CHANNELACCESSTOKEN
    }

    payload={
        'replyToken':posted_object['events'][0]['replyToken'],
        'messages':[{
            'type':'text',
            'text': text
            }
        ]
    }
    print("=request to LINE Messaging API")
    print(payload)
    #LINEからの返信をデータベースに登録
    Message05 = Message(content=text, time=datetime.datetime.now(), number = 1, user_id = 'line')
    db.session.add(Message05)
    db.session.commit()
    if Message05.number == posted_object['events'][0]['message']['text']:
            Message05.user = 1
    response = requests.post(lineconfig.REPLYAPIURL, data=json.dumps(payload),headers=headers)
    print("=response from LINE Messaging API")
    print(response)

    response_to_line=''
    return response_to_line
    #    print(response.status_code) 
    #    print(response.text) 


"""
def job_1():
    headers={
    'Content-Type': 'application/json',
    'Authorization': "Bearer "+lineconfig.CHANNELACCESSTOKEN
    }

    payload={
        'messages':[
            {
            'type':'text',
            'text':'Hello, World y210023'
            }
        ]
    }
    dt_now = datetime.datetime.now()
    print(dt_now.strftime('%Y年%m月%d日 %H:%M:%S'))
     # payload に text を含める場合、ここで更新する
    payload["messages"][0]["text"] = dt_now.strftime('%Y年%m月%d日 %H:%M:%S')+'です。'
    response = requests.post(lineconfig.BROADCASTAPIURL, data=json.dumps(payload),headers=headers)
    print(response.status_code) 
    print(response.text)

#AM11:00に実行
schedule.every().day.at("11:02").do(job_1)
"""

# お約束
if __name__ == '__main__':
    print("afo")
    allowed_host='0.0.0.0'
    server_port=3000
    app.debug=True
    init_db()           # DB初期化
    app.run(host=allowed_host,port=server_port)

"""
    schedule.run_pending()
    time.sleep(1)
"""