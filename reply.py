from flask import Flask, request
import requests
import json
import lineconfig
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
[目標変更]    : 目標数を変更
[実行記録変更]: 実行記録を変更
"""
default_message = 'タスクの登録や確認を行いたい場合はメニューを確認してください。'


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
    status = db.Column(db.String(200), nullable=False, default='idle')

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
    print("=request from LINE Messaging API")
    print(request.data) ## or request.get_data()
    print("---")
    #送られてきたメッセージが一つか複数かを判定
    #送られてきたメッセージがtextかどうかを判定
    if len(posted_object['events']) > 1 or 'text' not in posted_object['events'][0]['message']:
        task_status[user_id_from_line] = 'idle'
        text = default_message+'\n'+'[メニュー] : メニューを表示'
        Message04 = Message(content='notext', time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
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
                task_status[user_id_from_line] = current_task_id.status
                print('current_task_id:', current_task_id.task_id)
                print(task_status[user_id_from_line])
            else:
                task_status[user_id_from_line] = 'idle'

            # キャンセル処理
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
                        text += '\nキャンセルする場合は「キャンセル」と入力してください。'
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
                            text = '削除するタスク名を入力してください。\n\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += '\nキャンセルする場合は「キャンセル」と入力してください。'
                            task_status[user_id_from_line] = 'waiting_for_task_delete'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == 'タスク報告':
                        #タスクの記録
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        if not tasks:
                            text = '登録されているタスクがありません。'
                        else:
                            text = 'タスクの実行を報告します。記録したいタスク名を入力してください。\n\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += '\n'+'キャンセルする場合は「キャンセル」と入力してください。'
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
                            text = '今までの記録を確認します。\n記録を確認したいタスク名を入力してください。\n\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += '\n'+'キャンセルする場合は「キャンセル」と入力してください。'
                            task_status[user_id_from_line] = 'waiting_for_confilm_name'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == '目標変更':
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        if not tasks:
                            text = '登録されているタスクがありません。'
                        else:
                            text = '目標数を変更します。変更したいタスク名を入力してください。\n\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += '\n'+'キャンセルする場合は「キャンセル」と入力してください。'
                            task_status[user_id_from_line] = 'waiting_for_task_changegoal'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    elif user_message == '実行記録変更':
                        tasks = Task.query.filter_by(user_id=user_id_from_line, enable=True).all()
                        if not tasks:
                            text = '登録されているタスクがありません。'
                        else:
                            text = '実行記録を変更します。変更したいタスク名を入力してください。\n'+'現在のタスク一覧\n'
                            for task in tasks:
                                text += f'{task.task_name}: {task.daily_goal}\n'
                            text += '\n'+'キャンセルする場合は「キャンセル」と入力してください。'
                            task_status[user_id_from_line] = 'waiting_for_task_change_record'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])

                    else:
                        text = default_message+'\n'+'[メニュー] : メニューを表示'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
                        
                # タスク名を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_task_name':
                    #同じタスク名が登録されていないか確認
                    current_task_name = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    if current_task_name:
                        text = f"タスク '{user_message}' は既に登録されています。別の名前を入力してください。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_task_name')
                    else:
                        text = f"タスク名: {user_message} を受け取りました。次に、1日に達成したい目標数を入力してください。"
                        new = Task(user_id=user_id_from_line, start_time=datetime.datetime.now(), task_name=user_message, enable=True)
                        task_status[user_id_from_line] = 'waiting_for_task_goal'
                        db.session.add(new)
                        db.session.commit()
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number=0, user_id=posted_object['events'][0]['source']['userId'], task_id = new.task_id, status = 'waiting_for_task_goal')

                # タスクの目標数を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_task_goal':
                    current_task = Task.query.filter_by(task_id=current_task_id.task_id ,user_id=user_id_from_line, enable=True).first()
                    print('current_task:', current_task)
                    try:
                        daily_goal = int(user_message)
                        if daily_goal < 0:
                            text = '目標数は0以上の整数で入力してください。'
                        else:
                            current_task.daily_goal = daily_goal
                            db.session.commit()
                            text = f"タスク '{current_task.task_name}' が登録されました。目標: {daily_goal}"
                            # 状態をリセット
                            task_status[user_id_from_line]= 'idle'
                    except ValueError:
                        text = '目標数は整数で入力してください。'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_goal')

                # タスクの削除
                elif task_status[user_id_from_line] == 'waiting_for_task_delete':
                    # タスク名が登録されているか確認
                    current_task_delete_name = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    if current_task_delete_name:
                        text = f"タスク '{user_message}' を削除します。本当に削除しますか？\n[はい]、[いいえ]のいずれかを入力してください。"
                        task_status[user_id_from_line] = 'waiting_for_task_delete_confirm'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task_delete_name.task_id, status = 'waiting_for_task_delete')
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_task_delete')

                # タスクの削除確認
                elif task_status[user_id_from_line] == 'waiting_for_task_delete_confirm':
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
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task_delete_name.task_id, status = 'waiting_for_task_delete_confirm')                        

                # タスクの実行報告
                elif task_status[user_id_from_line] == 'waiting_for_task_record':
                    current_task = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    #print('current_task:', current_task.task_id)
                    if current_task:
                        if current_task.is_done == 1:
                            text = f"タスク '{user_message}' は既に実行されています。\n"+'実行記録を変更する場合は「実行記録変更」と入力してください。'
                            task_status[user_id_from_line] = 'idle'
                            Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_task_record')
                        else:
                            text = f"タスク '{user_message}' の実行を記録します。実行した数を入力してください。"
                            task_status[user_id_from_line] = 'waiting_for_task_record_number'
                            Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_record')
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_task_record')
                # タスクの実行数を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_task_record_number':
                    current_task = Task.query.filter_by(task_id = current_task_id.task_id, user_id=user_id_from_line, enable=True).first()
                    try:
                        number = int(user_message)
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = number, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_record_number')
                        if number < 0:
                            text = '実行数は0以上の整数で入力してください。'
                        else:
                            text = f"タスク '{current_task.task_name}' の実行数 {number} を記録しました。"
                            current_task.is_done = 1
                            current_task.report += 1
                            db.session.commit()
                            if number >= current_task.daily_goal:
                                text += '目標達成おめでとうございます！'
                            else:
                                text += f'目標まであと {current_task.daily_goal - number} 回届きませんでした。明日は頑張りましょう！'
                            task_status[user_id_from_line] = 'idle'
                    except ValueError:
                        text = '実行数は整数で入力してください。'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_record_number')

                # タスクの記録確認
                elif task_status[user_id_from_line] == 'waiting_for_confilm_name':
                    current_task = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    if current_task:
                        text = f"タスク '{user_message}' の記録を確認します。\n今までの記録を確認したい日付を入力してください。\n[合計]、[7日]、[30日]のいずれかを入力してください。"
                        task_status[user_id_from_line] = 'waiting_for_confilm_date'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_confilm_name')
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_confilm_name')

                # タスクの記録確認の日付を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_confilm_date':
                    current_task = Task.query.filter_by(task_id = current_task_id.task_id, user_id=user_id_from_line, enable=True).first()
                    if user_message == '合計':
                        total = db.session.query(func.sum(Message.number)).filter(Message.user_id == posted_object['events'][0]['source']['userId'], Message.task_id == current_task.task_id).scalar()
                        text = f"タスク '{current_task.task_name}' の合計は {total} 、"+'平均は{:.1f}です。\nこれまでの実行回数の合計は{current_task.report}回です。'.format(total/current_task.report)
                        task_status[user_id_from_line] = 'idle'
                    elif user_message == f'{time_short}日':
                        seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=time_short)
                        total = db.session.query(func.sum(Message.number)).filter(Message.time >= seven_days_ago, Message.user_id == posted_object['events'][0]['source']['userId'], Message.task_id == current_task.task_id).scalar()                        
                        text = f"タスク '{current_task.task_name}' の{time_short}日間の合計は {total} 、"+'平均は{:.1f}です。'.format(total/time_short)
                        task_status[user_id_from_line] = 'idle'
                    elif user_message == f'{time_long}日':
                        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=time_long)
                        total = db.session.query(func.sum(Message.number)).filter(Message.time >= thirty_days_ago, Message.user_id == posted_object['events'][0]['source']['userId'], Message.task_id == current_task.task_id).scalar()
                        text = f"タスク '{current_task.task_name}' の{time_long}日間の合計は {total}、"+'平均は{:.1f} です。'.format(total/time_long)
                        task_status[user_id_from_line] = 'idle'
                    else:
                        text = '日付は「合計」、「7日」、「30日」のいずれかを入力してください。'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_confilm_date')

                # 目標変更するタスク名を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_task_changegoal':
                    current_task = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    if current_task:
                        text = f"タスク '{user_message}' の目標数を変更します。新しい目標数を入力してください。"
                        task_status[user_id_from_line] = 'waiting_for_task_changegoal_number'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_changegoal')
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_task_changegoal')
                
                # 目標変更するタスクの目標数を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_task_changegoal_number':
                    current_task = Task.query.filter_by(task_id = current_task_id.task_id, user_id=user_id_from_line, enable=True).first()
                    try:
                        daily_goal = int(user_message)
                        current_task.daily_goal = daily_goal
                        db.session.commit()
                        text = f"タスク '{current_task.task_name}' の目標数を {daily_goal} に変更しました。"
                        task_status[user_id_from_line] = 'idle'
                    except ValueError:
                        text = '目標数は整数で入力してください。'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_changegoal_number')
                
                # 実行記録変更するタスク名を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_task_change_record':
                    current_task = Task.query.filter_by(user_id=user_id_from_line, task_name=user_message, enable=True).first()
                    if current_task:
                        if current_task.is_done == 0:
                            text = f"タスク '{user_message}' はまだ実行されていません。"
                            task_status[user_id_from_line] = 'idle'
                            Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_task_change_record')
                        else:
                            text = f"タスク '{user_message}' の実行記録を変更します。新しい実行数を入力してください。"
                            task_status[user_id_from_line] = 'waiting_for_task_change_record_number'
                            Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_change_record')
                    else:
                        text = f"タスク '{user_message}' は登録されていません。\n"+'[メニュー] : メニューを表示'
                        task_status[user_id_from_line] = 'idle'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], status = 'waiting_for_task_change_record')
                
                # 実行記録変更するタスクの実行数を受け取る
                elif task_status[user_id_from_line] == 'waiting_for_task_change_record_number':
                    current_task = Task.query.filter_by(task_id = current_task_id.task_id, user_id=user_id_from_line, enable=True).first()
                    try:
                        number = int(user_message)
                        #current_task.idと同じtask_idを持つMessageでnumberが0以上のものを取得して削除
                        messages_to_delete = Message.query.filter_by(task_id=current_task.task_id).filter(Message.number > 0).first()
                        bef_number = messages_to_delete.number
                        messages_to_delete.number = 0
                        db.session.commit()
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = number, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_change_record_number')
                        if number < 0:
                            text = '実行数は0以上の整数で入力してください。'
                        else:
                            text = f"タスク '{current_task.task_name}' の実行数を {bef_number}から{number} に変更しました。"
                            task_status[user_id_from_line] = 'idle'
                    except ValueError:
                        text = '実行数は整数で入力してください。'
                        Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'], task_id = current_task.task_id, status = 'waiting_for_task_change_record_number')

                else:
                    #text = get_reply(user_message)+'\n\n'
                    text = '習慣化サポートボットです。\n'
                    text += default_message+'\n'+'[メニュー] : メニューを表示'
                    Message04 = Message(content=user_message, time=datetime.datetime.now(), number = 0, user_id = posted_object['events'][0]['source']['userId'])
        
        #Mwssage04を更新
        Message04.status = task_status[user_id_from_line]
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
    Message05 = Message(content=text, time=datetime.datetime.now(), number = 0, user_id = 'line')
    db.session.add(Message05)
    db.session.commit()
    response = requests.post(lineconfig.REPLYAPIURL, data=json.dumps(payload),headers=headers)
    print("=response from LINE Messaging API")
    print(response)

    response_to_line=''
    return response_to_line
    #    print(response.status_code) 
    #    print(response.text) 



# お約束
if __name__ == '__main__':
    print("afo")
    allowed_host='0.0.0.0'
    server_port=3000
    app.debug=True
    init_db()           # DB初期化
    app.run(host=allowed_host,port=server_port)
