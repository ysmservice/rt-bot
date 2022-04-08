<!--[![Discord Bots](https://top.gg/api/widget/status/716496407212589087.svg)](https://top.gg/bot/716496407212589087) [![Discord Bots](https://top.gg/api/widget/servers/716496407212589087.svg)](https://top.gg/bot/716496407212589087) ![Discord](https://img.shields.io/discord/718641964672876614?label=suppoFree-rt&logo=discord)-->
# Free-RT Bot
これはDiscordのボットで、無料RTです。
Discordには「RT bot」があり、tasurenへの課金に利用できますので、お金に余裕のある方はRTを使ってください。
Free RTは、ほとんどのbotが持っている機能を備えた、機能豊富なbotです。
また、他のbotにはない機能もあります。
DiscordのBotアカウントであるFree RTに接続すると、Free RTのサービスを開始することができます。
また、WebSocketでrt-backendと通信し、Web認証などを行います(ただし、現在は行っておらず、作成中です。近日中に公開予定です)。
RTについて知らない方はこちらを見てください。
Free RTについて知らない人はここを見てみましょう。(ホームページ作成中です、お待ちください)

## LICENSE
`BSD 4-Clause License` (`LICENSE`ファイルに詳細があります。)

## Contributing
(https://github.com/free-RT/rt-bot/blob/main/contributing.md)[contributing.md]をご覧ください。

## Installation
### 依存性
必要

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

