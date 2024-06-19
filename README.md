### HTTP クライアント
```zsh
python get.py
```

### 準備
* lineconfig-dist.py を lineconfig.py にコピーして LINE Messaging API の情報を書く
* LINE Messaging API に Webhook として https://ナントカ-ナントカ-ナントカ.free-ngrok.app/callback を登録する（教員がやっておくことが多い）
* LINE公式アカウントを友だち登録する


### 一斉送信
```zsh
python broadcast.py
```
#### 注意

* 友だち登録しただけの人にいきなりメッセージを送りつけることになるので注意. 特にプログラムが loop していたり, cron からプログラムを呼び出したりすると, 大量のメッセージを送ってしまう危険がある. 
* 上記のAPIによる送信は, 無料プランでは月間200に限られている(2024-04現在)

#### 課題
メッセージの最後に, 現在の日時(形式自由)を追加しよう(発展:日本語のいい感じの形式で, 時刻のお知らせっぽい文で)
* 文字列の連結は+
* 日時を扱うには datetime モジュール  https://docs.python.org/ja/3/library/datetime.html
```python
import datetime 
print(datetime.datetime.now().isoformat())
```

#### 課題
画像など, 他のタイプのメッセージも送ってみよう 
* クイックスタート https://developers.line.biz/ja/docs/messaging-api/message-types/
＊ リファレンス https://developers.line.biz/ja/reference/messaging-api/#message-objects


### O次郎bot(POSTにレスポンスするWebサーバ)
別ターミナルで ngrok を同時に動かしておくことが必要です．

```zsh
python reply.py
```
として起動した後，LINEアプリからメッセージを送る

#### Troubleshooting
* 定型文が返ってくる  -> Official Account Manager で応答を無効化
* 何も出力されない -> LMAからCAにリクエストが届いてない. Webhook URL 確認. LINE Messaging API 側で検証 すると200になる?
* Pythonの文法エラーが出る -> リクエストは届いてる. プログラム壊した?
* LINE Messaging APIのエラーが出る -> Reply API へのリクエスト内容が不正. Channel Access Token 書き直した?

#### 課題
送信内容を変えよう. 現在日時とか.


### 鸚鵡ボット(POSTに応じるWebサーバ)
別ターミナルで ngrok を同時に動かしておくことが必要です．

```zsh
python echo.py
```
として起動した後，LINEアプリからメッセージを送る

#### 課題
語尾に'じゃけ〜’を加えて広島弁botを作ろう.


