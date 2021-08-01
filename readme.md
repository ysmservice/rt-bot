# RT Backend
RTのバックエンドです。  
(C) 2020 RT-Team

## ライセンスについて
ライセンスは現在`BSD 4-Clause License`で`LICENSE`ファイルに記載されています。  
著作権表記：`(C) 2020 RT-Team`

## 起動方法
Python 3.8以上、MySQLを用意します。
### 必要なモジュールをすべてインストール
`pip3 install -r requirements.txt`
### TOKEN, MySQLの設定
以下の形で`token.secret`というファイルで保存してください。
```json
{
    "token": {
        "test": "テスト用token",
	"production": "本番用BotToken"
    },
    "mysql": {
        "user": "root",
	"password": "mysqlのパスワード"
    }
}
```
### 起動コマンド
テスト用：`sudo -E python3 main.py test`
本番用：`sudo -E python3 main.py production`
