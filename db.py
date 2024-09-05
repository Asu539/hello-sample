import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# インスタンス生成
app = Flask(__name__)

# Flaskに対する設定
app.config['SECRET_KEY'] = os.urandom(24)
base_dir = os.path.dirname(__file__)
database = 'sqlite:///' + os.path.join(base_dir, 'data.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# db変数を使用してSQLAlchemyを操作できる
db = SQLAlchemy(app)

# モデル
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.String(200), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    #ユーザーかそれ以外かを0か1で表す
    user = db.Column(db.Integer, nullable=False, default=0)

    def __str__(self):
        return f'課題ID:{self.id} 內容:{self.content} ユーザーID:{self.user_id} 時間:{self.time} ユーザー:{self.user}'

# DB作成
def init_db():
    with app.app_context():
        print('(1)テーブルを削除してから作成')
        db.drop_all()
        db.create_all()

        # データ作成
        print('(2) データ登録:実行')
        task01 = Task(content='風呂掃除', user_id='tanaka',time=datetime.now())
        #task01のuser_idを変更
        if task01.user_id == 'tanaka':
            task01.user_id = 'yamada'
        task02 = Task(content='洗濯', user_id='suzuki', time=datetime.now())
        task03 = Task(content='買い物', user_id='katayama', time=datetime.now())
        #もしcontentが'買い物'の場合、userを1にする(全てのtaskに適用)
        if task03.content == '買い物':
            task03.user = 1
        db.session.add_all([task01, task02, task03])
        db.session.commit()

# CRUD操作
def insert():
    with app.app_context():
        print('=========1件登録=========')
        task04 = Task(content='請求書作成')
        db.session.add(task04)
        db.session.commit()
        print('登録 =>', task04)

def select_all():
    with app.app_context():
        print('=========全件取得=========')
        tasks = Task.query.all()
        for task in tasks:
            print(task)

def select_filter_pk(pk):
    with app.app_context():
        print('=========１件取得==========')
        target = Task.query.filter_by(id=pk).first()
        print('取得 =>', target)

def update(pk):
    with app.app_context():
        print('========更新実行========')
        target = Task.query.filter_by(id=pk).first()
        print('更新前 =>', target)
        target.content = '課題を変更'
        db.session.add(target)
        db.session.commit()

def delete(pk):
    with app.app_context():
        print('=========削除処理==========')
        target = Task.query.filter_by(id=pk).first()
        db.session.delete(target)
        db.session.commit()
        print('削除 =>', target)

# 実行
if __name__ == '__main__':
    init_db()           # DB初期化
    # DBの内容を条件付きで出力
    select_filter_pk(3)
    """
    insert()            # 1件登録処理
    update(1)           # 更新処理
    select_filter_pk(1) # 1件取得 (更新後の値を取得)
    delete(2)           # 削除処理
    select_all()        # 全件取得
    """
