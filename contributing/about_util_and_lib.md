# rtutilとrtlibについて
rtutilとrtlibは共にRTに関するお役立ちツールが集まったもの、と考えてください。  
freeRTにおいて何かそのようなツールを作る際には**rtutil**に作成してください。  
この2つに関してはrtutilへの統一を目指しています。

## rtlibにあるもの
* webhook_send (`channel.webhook_send`を使える機能)
* componesy (`discord.ui.View`を簡単に作るためのもの)
* mysql_manager (わからん)
* data_manager (わからん)
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
* dochelp (自動ドキュメンテーションヘルプ管理)
* on_cog_addイベント (cogの追加イベント)
* on_full_reaction_add/removeイベント (rawイベントでは通常取得できないメンバーやメッセージ情報を補ったイベント)
* on_send、on_editイベント (自分がしゃべった・編集したときに発火するイベント)

## rtutilにあるもの
* MultipleConverters (`, `によって区切っていくつかの対象を同時に取得できるコンバーター)
* data_manager (わからん、なんでこんなに種類あんの)
* markord (マークダウン変換機)
* minesweeper (マインスイーパー)
* securlAPIを叩く機能
