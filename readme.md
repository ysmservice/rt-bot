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

* Python3.8以上
* MySQL
* `requirements.txt`にあるもの全て。
  注意：`jishaku`をインストールすると依存しているdiscord.pyがインストールされます。
  ですがRTはnextcordを使っているので、jishakuをインストールした後にdiscord.pyを消してからnextcordをインストールするのを推奨します。
* 認証等のバックエンドを必要とする機能を使う場合は`rt-backend`の実行
### 起動手順
1. 必要なものを`pip install -r requirements.txt`でインストールをします。
2. 必要なTOKENなどを`auth.template.json`を参考に`auth.json`に書き込む。
3. `{}`を書き込んだ`cogs/tts/dic/dictionary.json`を作る。
4. `cogs/tts/outputs`フォルダを作る。
5. `rtlib`に`rt-module`リポジトリを置いてフォルダの名前を`rt_module`にする。
6. `rt-backend`リポジトリにあるプログラムを動かす。
7. `python3 main.py test`でテストを実行する。(この際TOKENは`test`のキーにあるものが使用されます。)
### 本番の実行
起動コマンドは`sudo -E python3 main.py production`で`auth.json`のTOKENで`production`のTOKENが必要となります。
