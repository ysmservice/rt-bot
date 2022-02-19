[![Discord Bots](https://top.gg/api/widget/status/716496407212589087.svg)](https://top.gg/bot/716496407212589087) [![Discord Bots](https://top.gg/api/widget/servers/716496407212589087.svg)](https://top.gg/bot/716496407212589087) ![Discord](https://img.shields.io/discord/718641964672876614?label=support&logo=discord)
# RT Bot
DiscordのBotのRTのBotです。  
RTというのはこのBotだけで済むようなBotを目指す多機能で便利なBotです。  
DiscordのBotアカウントであるRTに接続してRTのサービスを開始します。  
ウェブ認証などのために`rt-backend`とWebSocketで通信も行います。  
RTについて知らない人は[ここ](https://rt-bot.com)を見てみましょう。

## LICENSE
`BSD 4-Clause License` (`LICENSE`ファイルに詳細があります。)

## Contributing
`contributing.md`をご覧ください。

## Installation
### 依存性
必要なものです。

* Python 3.10
* MySQL または MariaDB
* `requirements.txt`にあるもの全て。
* 認証等のバックエンドを必要とする機能を使う場合は`rt-backend`の実行
### 起動手順
1. 必要なものを`pip install -r requirements.txt`でインストールをします。
2. 必要なTOKENなどを`auth.template.json`を参考に`auth.json`に書き込む。
3. `rtlib`に`rt-module`リポジトリを置いてフォルダの名前を`rt_module`にする。
4. `rt-backend`リポジトリにあるプログラムを動かす。
   (これはオプションで認証等のバックエンドを必要とするものを動かしたい場合は動かす必要があります。)
5. `python3 main.py test`でテストを実行する。
   (この際TOKENは`auth.json`の`test`のキーにあるものが使用されます。)

※ もし読み上げを動かしたいのなら`cogs/tts`にある`readme.md`を読んでください。
### 本番の実行
起動コマンドは`sudo -E python3 main.py production`で`auth.json`のTOKENで`production`のTOKENが必要となります。
