# rtutilとrtlibについて
rtutilとrtlibは共にRTに関するお役立ちツールが集まったもの、と考えてください。  
freeRTにおいて何かそのようなツールを作る際には**rtutil**に作成してください。  
rtutilへの統一作業中です。完全に作業が終わるまでの間は基本的には新機能の追加は控えてほしいです。

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
* その他

# data_managerについて
ここでは3つのDataBaseManagerを統一し、1つのManagerにした時にどのような仕様になるかを解説しています。  
元々rtutil.DatabaseManagerだったものをそのまま使用する予定です。  
他の種類のDBManagerについては解説されないのでご注意ください。

## data_managerを使ったコード例
```python
from rtutil import DatabaseManager
from mysql import Pool, Cursor

class DataManager(DatabaseManager):

    TABLE = "テーブル名"
    
    def __init__(self, cog: "cog名"):
        self.cog = cog
        self.pool: Pool = self.cog.bot.mysql.pool
        self.cog.bot.loop.create_task(self.prepare_table())
    
    async def prepare_table(self, cursor: Cursor = None) -> None:
        "テーブルを準備する。"
        await cursor.execute(
            f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                ChannelID BIGINT
            );"""
        )

    async def write(
        self, channel_id: int, cursor: Cursor = None
    ) -> None:
        "データを書き込みます。"
        await cursor.execute(
            f"""INSERT INTO {self.TABLE} VALUES (%s)""",
            (channel_id)
        )
```
