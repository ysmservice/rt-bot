# RT Backend
DiscordのBotのRTのバックエンドです。  
著作権表記：`(C) 2020 RT-Team`

## ライセンス
ライセンスは現在`BSD 4-Clause License`で`LICENSE`ファイルに記載されています。  

## 翻訳の協力
RTが返信を使いメッセージを送信する際は返信先(コマンドの実行者)に設定されてる言語に対応するメッセージを送ろうとします。  
この時日本語以外を送るには`data/replies.json`に言語データが存在しなければいけません。  
`dsata/replies.json`は以下のようにします。  
```json
{
    "送信内容": {
        "言語コード (例：en)": "翻訳結果 (例：content)"
    },
    "テスト": {
        "en": "test"
    }
}
```
例えば`await ctx.reply("テスト")`とあったとします。  
そしてこれが実行されるコマンドを実行した人は言語設定を`en`(英語)に設定しています。  
この場合は`data/replies.json`の`テスト`にある`en`にあるものに`テスト`が交換されて送信されます。  
この`data/replies.json`の`en`版の作成の協力者を探しています。  
もしRTの翻訳の協力をしてくださる方は[このDiscordグループ]まで来てください。  
そこで翻訳してほしい文を送信します。  
翻訳をする際はForkをしてこの`data/replies.json`を編集してPRを出してください。

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