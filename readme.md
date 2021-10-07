[![Discord Bots](https://top.gg/api/widget/status/716496407212589087.svg)](https://top.gg/bot/716496407212589087) [![Discord Bots](https://top.gg/api/widget/servers/716496407212589087.svg)](https://top.gg/bot/716496407212589087) ![Discord](https://img.shields.io/discord/718641964672876614?label=Support&logo=discord) ![GitHub issues](https://img.shields.io/github/issues/RT-Team/rt-backend) `(C) 2020 RT Team`
# RT Backend
DiscordのBotのRTのバックエンドです。  
RTについて知らない人は[ここ](https://rt-bot.com)を見てみましょう。

## ライセンス
ライセンスは現在`BSD 4-Clause License`で`LICENSE`ファイルに記載されています。  

## コントリビューション
`contributing.md`を見てください。

### 環境
```
Python  3.8以上
MySQL   `mysql`というデータベースを使用します。
```
### 必要なモジュールをすべてインストール
`pip3 install -r requirements.txt`
### TOKEN, MySQLの設定
以下の形で`token.secret`というファイルで保存してください。
```json
{
    "token": {
        "test": "テスト用token",
	    "production": "本番用BotToken",
	    "sub": "..."
    },
    "mysql": {
        "user": "root",
    	"password": "mysqlのパスワード"
    },
    "twitter": "...",
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
もしRT Teamで開発環境を整えるのが面倒な場合はtasurenに言えば整えた状態の`rt-backend`のフォルダくれます。  
↑ですが、MySQLはもちろん自分で設定です。