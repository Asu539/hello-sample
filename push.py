import requests
import json
import lineconfig
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, select, func
import sqlite3
import os

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

# モデル
class Message(db.Model):
    __tablename__ = 'talks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String(200), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    #ユーザーかそれ以外かを0か1で表す
    #user = db.Column(db.Integer, nullable=False, default=0)
    number = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.String(200), nullable=False)


headers={
   'Content-Type': 'application/json',
   'Authorization': "Bearer "+lineconfig.CHANNELACCESSTOKEN
}

payload={
    'to':'U4b4ca417d98f6d17369aa34174839f1c',
    'messages':[
        {
        'type':'text',
        'text':'日本語も通る?'
        }
    ]
}
response = requests.post(lineconfig.PUSHAPIURL, data=json.dumps(payload),headers=headers)
print(response.status_code) 
print(response.text) 