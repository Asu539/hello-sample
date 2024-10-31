from flask import Flask, request
import requests
import json
import lineconfig
import openaiconfig
from openai import OpenAI
#import schedule
#import time
import datetime
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, select, func
import sqlite3


time_short = 7
time_long = 30
menu_message = """
記録の確認、タスクの登録、削除などを行いたい場合は以下を入力してください。

[タスク登録]  : タスクを登録
[タスク一覧]  : タスク一覧を表示
[タスク削除]  : タスクを削除
[タスク報告]  : タスクの実行を報告
[記録確認]    : 記録を確認
"""
default_message = '習慣化サポートボットです。以下でメニューを表示します。'

messages=[]
client = OpenAI()

# システムのプロンプト
system_content = """
あなたは私の習慣化サポーターです。標準語で会話し応援します。30文字以内で返信します。
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

"""
# ユーザーモデル
class User(db.Model):
    user_id = db.Column(db.String(200), primary_key=True, unique=True, nullable=False)
"""

#タスクモデル
class Task(db.Model):
    __tablename__ = 'tasks'
    task_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    user_id = db.Column(db.String(200), nullable=False)
    task_name = db.Column(db.String(200), nullable=False, default='未定')
    daily_goal = db.Column(db.Integer, nullable=False, default=0)
    enable = db.Column(db.Integer, nullable=False, default=True)

# メッセージモデル
class Message(db.Model):
    __tablename__ = 'Messages'
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


task_status = {}

@app.route('/callback', methods=['POST'])
def response():
    posted_data=request.data
    posted_object=json.loads(posted_data.decode('utf8'))
    # ユーザーIDの取得
    user_id_from_line = posted_object['events'][0]['source']['userId']
    # ユーザーIDがデータベースに存在するか確認
    task = Task.query.filter_by(user_id=user_id_from_line).first()
    # ユーザーが初めてアクセスした場合、状態を 'idle' に設定
    if user_id_from_line not in task_status:
        task_status[user_id_from_line] = 'idle'
    response_to_line=''
    print("=request from LINE Messaging API")
    print(request.data) ## or request.get_data()
    print("---")
    #送られてきたメッセージが一つか複数かを判定
    #送られてきたメッセージがtextかどうかを判定
    if len(posted_object['events']) > 1 or 'text' not in posted_object['events'][0]['message']:
        task_status[user_id_from_line] = 'idle'
        text = default_message+'\n'+'[メニュー] : メニューを表示'
        Message04 = Message(content='text', time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
        print('複数のメッセージかtextでないメッセージです。')
    else:
        print(posted_object['events'][0]['message']['text'])
        # CRUD操作
        with app.app_context():
            print('=========1件登録=========')
            # ユーザーからのメッセージを取得
            user_message = posted_object['events'][0]['message']['text']
            text = ""  # 返信テキスト
            # 現在のタスクの状態を確認,task_idがnoneでない場合
            current_task_id = Message.query.filter_by(user_id=user_id_from_line).order_by(Message.time.desc()).first()
            if current_task_id:
                print('current_task_id:', current_task_id.task_id)
                print(task_status[user_id_from_line])

            if user_message == 'キャンセル':
                if task_status[user_id_from_line] == 'waiting_for_task_goal':
                    #タスクの登録をキャンセル
                    print('タスクの登録をキャンセル')
                    Task.query.filter_by(task_id=current_task_id.task_id, user_id=user_id_from_line).first().enable = False
                    db.session.commit()
                task_status[user_id_from_line] = 'idle'
                text = 'キャンセルしました。\n'+'[メニュー] : メニューを表示'
                Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

            else:
                if task_status[user_id_from_line] == 'idle':  # 通常の状態

                    if user_message == 'タスク登録':
                        text = 'タスクを登録します。タスク名を入力してください。\n\n'+'現在のタスク一覧\n'
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        for task in tasks:
                            text += f'{task.task_name}: {task.daily_goal}\n'
                        text += 'キャンセルする場合は「キャンセル」と入力してください。'
                        task_status[user_id_from_line] = 'waiting_for_task_name'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == 'タスク一覧':
                        #タスク一覧を取得
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        if not tasks:
                            text = '登録されているタスクがありません。'
                        else:
                            text = 'タスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == 'タスク削除':
                        #タスク削除
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        if not tasks:
                            text = '登録されているタスクがありません。'
                        else:
                            text = '削除するタスク名を入力してください。\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += 'キャンセルする場合は「キャンセル」と入力してください。'
                            task_status[user_id_from_line] = 'waiting_for_task_delete'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == 'タスク報告':
                        #タスクの記録
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        if not tasks:
                            text = '登録されているタスクがありません。'
                        else:
                            text = 'タスクの実行を報告します。記録したいタスク名を入力してください。\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += 'キャンセルする場合は「キャンセル」と入力してください。'
                            task_status[user_id_from_line] = 'waiting_for_task_record'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == 'メニュー':
                        text = menu_message
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == '記録確認':
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        if not tasks:
                            text = '登録されているタスクがありません。'
                        else:
                            text = '今までの記録を確認します。記録を確認したいタスク名を入力してください。\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += 'キャンセルする場合は「キャンセル」と入力してください。'
                            task_status[user_id_from_line] = 'waiting_for_confilm_name'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    else:
                        #text = get_reply(user_message)+'\n'+'[メニュー] : メニューを表示'
                        text = default_message+'\n'+'[メニュー] : メニューを表示'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
                        
                elif task_status[user_id_from_line] == 'waiting_for_task_name':
                    #同じタスク名が登録されていないか確認
                    current_task_name = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    if current_task_name:
                        text = f"タスク '{user_message}' は既に登録されています。別の名前を入力してください。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
                    else:
                        # タスク名を受け取る
                        text = f"タスク名: {user_message} を受け取りました。次に、1日に達成したい目標数を入力してください。"
                        new = Task(user_id=user_id_from_line, task_name = user_message, enable=True)
                        task_status[user_id_from_line] = 'waiting_for_task_goal'
                        db.session.add(new)
                        db.session.commit()
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = new.task_id)

                elif task_status[user_id_from_line] == 'waiting_for_task_goal':
                    # タスクの目標数を受け取る
                    current_task = Task.query.filter_by(task_id=current_task_id.task_id ,user_id=user_id_from_line, enable=True).first()
                    print('current_task:', current_task)
                    try:
                        daily_goal = int(user_message)
                        current_task.daily_goal = daily_goal
                        db.session.commit()
                        text = f"タスク '{current_task.task_name}' が登録されました。目標: {daily_goal}"
                        # 状態をリセット
                        task_status[user_id_from_line]= 'idle'
                    except ValueError:
                        text = '目標数は整数で入力してください。'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id)

                elif task_status[user_id_from_line] == 'waiting_for_task_delete':
                    # タスクの削除
                    # タスク名が登録されているか確認
                    current_task_delete_name = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    if current_task_delete_name:
                        text = f"タスク '{user_message}' を削除します。本当に削除しますか？\n[はい]、[いいえ]のいずれかを入力してください。"
                        task_status[user_id_from_line] = 'waiting_for_task_delete_confirm'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task_delete_name.task_id)
                        """
                        current_task_delete_name.enable = False
                        db.session.commit()
                        text = f"タスク '{user_message}' を削除しました。"
                        """
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                elif task_status[user_id_from_line] == 'waiting_for_task_delete_confirm':
                    # タスクの削除
                    current_task_delete_name = Task.query.filter_by(task_id = current_task_id.task_id, user_id=user_id_from_line, enable=True).first()
                    if user_message == 'はい':
                        current_task_delete_name.enable = False
                        db.session.commit()
                        text = f"タスク '{current_task_delete_name.task_name}' を削除しました。"
                    elif user_message == 'いいえ':
                        text = f"タスク '{current_task_delete_name.task_name}' の削除をキャンセルしました。"
                    else:
                        text = '「はい」、「いいえ」のいずれかを入力してください。'
                    task_status[user_id_from_line] = 'idle'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task_delete_name.task_id)                        

                elif task_status[user_id_from_line] == 'waiting_for_task_record':
                    # タスクの記録
                    current_task = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    print('current_task:', current_task.task_id)
                    if current_task:
                        text = f"タスク '{user_message}' の実行を記録します。実行した数を入力してください。"
                        task_status[user_id_from_line] = 'waiting_for_task_record_number'
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id)

                elif task_status[user_id_from_line] == 'waiting_for_task_record_number':
                    # タスクの記録
                    current_task = Task.query.filter_by(task_id = current_task_id.task_id, user_id=user_id_from_line, enable=True).first()
                    try:
                        number = int(user_message)
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = number, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id)
                        text = f"タスク '{current_task.task_name}' の実行数 {number} を記録しました。"
                        current_task.time = datetime.datetime.now()
                        if number >= current_task.daily_goal:
                            text += '目標達成おめでとうございます！'
                        else:
                            text += f'目標まであと {current_task.daily_goal - number} 回届きませんでした。明日は頑張りましょう！'
                    except ValueError:
                        text = '実行数は整数で入力してください。'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
                    task_status[user_id_from_line] = 'idle'

                elif task_status[user_id_from_line] == 'waiting_for_confilm_name':
                    # タスクの記録
                    current_task = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    print('current_task:', current_task.task_id)
                    if current_task:
                        text = f"タスク '{user_message}' の記録を確認します。今までの記録を確認したい日付を入力してください。\n[合計]、[7日]、[30日]のいずれかを入力してください。"
                        task_status[user_id_from_line] = 'waiting_for_confilm_date'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id)
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                elif task_status[user_id_from_line] == 'waiting_for_confilm_date':
                    # タスクの記録
                    current_task = Task.query.filter_by(task_id = current_task_id.task_id, user_id=user_id_from_line, enable=True).first()
                    if user_message == '合計':
                        total = db.session.query(func.sum(Message.number)).filter(Message.user_id == posted_object['events'][0]['source']['userId'], Message.task_id == current_task.task_id).scalar()
                        text = f"タスク '{current_task.task_name}' の合計は {total} です。"
                    elif user_message == f'{time_short}日':
                        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=time_short)
                        total = db.session.query(func.sum(Message.number)).filter(Message.time >= seven_days_ago, Message.user_id == posted_object['events'][0]['source']['userId'], Message.task_id == current_task.task_id).scalar()
                        text = f"タスク '{current_task.task_name}' の{time_short}日間の合計は {total} です。"
                    elif user_message == f'{time_long}日':
                        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=time_long)
                        total = db.session.query(func.sum(Message.number)).filter(Message.time >= thirty_days_ago, Message.user_id == posted_object['events'][0]['source']['userId'], Message.task_id == current_task.task_id).scalar()
                        text = f"タスク '{current_task.task_name}' の{time_long}日間の合計は {total} です。"
                    else:
                        text = '日付は「合計」、「7日」、「30日」のいずれかを入力してください。'
                    task_status[user_id_from_line] = 'idle'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id)
        db.session.add(Message04)
        db.session.commit()
        print('登録 =>', Message04)
        print('=========１件取得==========')

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