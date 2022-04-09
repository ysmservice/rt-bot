# rtutilとrtlibについて
rtutilとrtlibは共にRTに関するお役立ちツールが集まったもの、と考えてください。  
freeRTにおいて何かそのようなツールを作る際には**rtutil**に作成してください。  
この2つに関しては統一を目指しています。  

## libにあるもの
* webhook_send (`channel.webhook_send`を使える機能)
* componesy (`discord.ui.View`を簡単に作るためのもの)
* mysql_manager
* data_manager
* discord.ext.tasksのタスクがデータベースの操作失敗によって止まることがないようにする機能 (標準搭載)
* sendKwargs (ctx.sendにはあるけどinteractionresponce.send_messageにはないKwargsを削除して返す関数っぽい)
* RT (AutoShardedBotを継承したサブクラス、起動時に使っている)
* @websocketデコレータ (ws通信を簡単に行う機能らしい)
* WebSocketManager (ws関連のCog)
* rtws (さっきのwebsocketとは分離されている、RT専用のws機能)
* EmbedPage (buttonを使ってページのようなことを簡単にできるようにしたもの。)
* Slash関連 (スラッシュコマンドを通常のcommands.commandと互換性を持たせた状態にするための機能)
* Cacher (キャッシュ管理)
* debug (デバッグ関連のCog)
