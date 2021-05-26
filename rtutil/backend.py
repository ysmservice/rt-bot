
# RT - Shard

import discord

from traceback import format_exc
from ujson import loads, dumps
import websockets
import asyncio
import logging
import sys


class RTShardClient(discord.AutoShardedClient):
    def __init__(self, *args, logging_level=logging.DEBUG, **kwargs):
        # ログの出力を設定する。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("RT - Client")
        super().__init__(*args, **kwargs)

        # Event Injection
        for parser_name in self._connections.parsers:
            parser_name_lower = parser_name.lower()
            setattr(self, parser_name_lower, self.on_some_event_template)
            self._connections.parsers[parser_name] = getattr(self, parser_name_lower)

        # Setup worker
        self.queue = asyncio.Queue()
        self.logger.info("Creating websockets server.")
        server = websockets.serve(self.worker, "localhost", "3000")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server)
        self.logger.info("Started websockets server!")

    def on_some_event_template(self, data):
        asyncio.create_task(self.queue.put({"data": {"type": sys._getframe().f_code.co_name, "data": data}})

    async def worker(self, ws, path):
        while True:
            self.logger.info("Waiting event...")
            queue = await self.queue.get()
            self.logger.info("Received event!")

            # イベントでそのイベントでのWorkerとの通信が始まる。
            data = {
                "type": "start",
                "data": queue["data"]
            }
            # Workerにイベント内容を伝える。
            await ws.send(dumps(data))

            # このイベントでの通信を開始する。
            # 通信する理由はDiscordを操作することがあった際に簡単にするためです。
            # Start -> worker do task -> worker want to send message to discord
            # -> Websocket server do -> callback to worker -> worker say end
            error = False
            self.logger.info("Start event communication.")
            while True:
                # Workerからのコールバックを待つ。
                self.logger.info("Waiting worker callback...")
                try:
                    data = loads(await asyncio.wait_for(ws.recv(), timeout=5))
                except asyncio.TimeoutError:
                    # もしWorkerからコールバックが来ない場合はイベントでのWorkerとの通信を終了する。
                    error = True
                else:
                    # Workerから何をしてほしいか受け取ったらその通りにやってあげる。
                    callback_data = {
                        "type": "ok",
                        "data": {}
                    }
                    try:
                        if data["type"] == "discord":
                            if data["data"]["type"] == "send":
                                message = await queue["channel"].send(
                                    *data["data"].get("args", {}),
                                    **data["data"].get("kwargs", {})
                                )
                                i = message.id
                                callback_data["data"]["message_id"] = i
                        elif data["type"] == "end":
                            # もしこのイベントでの通信を終わりたいと言われたら終わる。
                            # 上二も同じものがあるがこれは仕様です。
                            break
                        else:
                            # もしコールバックがエラーかtypeが不明だったらこのイベントでの通信を終わらす。
                            error = (data["data"]["content"]
                                     if data["type"] == "error" else "エラー不明")
                            print(error)
                            break
                    except Exception:
                        error = format_exc()
                        print(error)
                        break

                    # コールバックを送る。
                    await ws.send(dumps(callback_data))

            # エラー落ちによるイベントの通信でコールバックチャンネルがあるなら通知しておく。
            if error:
                if queue["channel"]:
                    content = "すみませんが処理中にエラーが発生したようです。"
                    if isinstance(error, str):
                        content += "\n```\n" + error + "\n```"
                    await queue["channel"].send(content)

            # 通信を終わらせたという合図を送信する。
            callback_data = {
                "type": "end",
                "data": {}
            }
            await ws.send(dumps(callback_data))

            self.logger.info("End event communication.")

    async def on_message(self, message):
        data = {
            "cache": {"message": message},
            "data": {
                "type": "on_message",
                "content": message.content
            }
        }
        await self.queue.put(data)
