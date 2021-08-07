# RT Backend
DiscordのBotのRTのバックエンドです。  
著作権表記：`(C) 2020 RT-Team`

## ライセンス
ライセンスは現在`BSD 4-Clause License`で`LICENSE`ファイルに記載されています。  

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
    },
    "oauth": {
        "test": {
            "client_id": "test用BotのOAuthクライアントID",
            "client_secret": "test用BotのOAuthクライアントシークレット"
        },
        "production": {
            "client_id": "本番用BotのOAuthクライアントID",
            "client_secret": "本番用BotのOAuthクライアントシークレット"
        }
    }
}
```
### 起動コマンド
テスト用：`sudo -E python3 main.py test`
本番用：`sudo -E python3 main.py production`