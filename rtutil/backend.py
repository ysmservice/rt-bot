# RT - Shard

import discord

from traceback import format_exc
from ujson import loads, dumps
from copy import copy
import websockets
import asyncio
import logging

from .driver import DiscordDriver


ON_SOME_EVENT = """def !event_type!(data):
    event_type = '!event_type!'
    data = {"type": event_type, "data": data}
    asyncio.create_task(self.queue.put(data))
    self.default_parsers[event_type.upper()](data['data'])"""


class RTShardFrameWork(discord.AutoShardedClient):
    def __init__(self, *args, logging_level=logging.DEBUG, **kwargs):
        # ログの出力を設定する。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("RT - Client")

        # その他色々設定する。
        super().__init__(*args, **kwargs)
        self.driver = DiscordDriver(self)

        # Event Injection
        self.default_parsers = copy(self._connection.parsers)
        for parser_name in self._connection.parsers:
            parser_name_lowered = parser_name.lower()
            exec(ON_SOME_EVENT.replace("!event_type!", parser_name_lowered))
            self._connection.parsers[parser_name] = eval(parser_name_lowered)
        globals()["self"] = self

        # Setup worker
        self.queue = asyncio.Queue()
        self.logger.info("Creating websockets server.")
        server = websockets.serve(self.worker, "localhost", "3000")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server)
        self.logger.info("Started websockets server!")

    async def worker(self, ws, path):
        while True:
            self.logger.info("Waiting event...")
            queue = await self.queue.get()
            self.logger.info("Received event!")

            # イベントでそのイベントでのWorkerとの通信が始まる。
            data = {
                "type": "start",
                "data": queue
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
                            func = getattr(
                                self.driver, data["data"]["type"], None)
                            args = data["data"].get("args", [])
                            kwargs = data["data"].get("kwargs", {})
                            if func:
                                # ドライバー処理する。
                                # このシステムは実行を動的にする。
                                # その動的にするときに使うものを定義するためのものがドライバーです。
                                if asyncio.iscoroutinefunction(func):
                                    await func(*args, **kwargs)
                                else:
                                    func(*args, **kwargs)
                            else:
                                # 上に書いてある動的に実行するやつです。
                                coro = eval(data["data"]["coro"])( # noqa
                                    *args, **kwargs)
                                exec(
                                    "asyncio.create_task(coro)",
                                    globals(), self.driver.box
                                )
                            if data["data"]["type"] == "send":
                                message = await queue["channel"].send(
                                    *args, **kwargs)
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
