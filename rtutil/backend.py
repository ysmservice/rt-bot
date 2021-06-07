# RT - Shard 

import discord

from traceback import format_exc
from ujson import loads, dumps
from copy import copy
import websockets
import asyncio
import logging

from .discord_requests import DiscordRequests


ON_SOME_EVENT = """def !event_type!(data):
    event_type = '!event_type!'
    data = {"type": event_type, "data": data}
    asyncio.create_task(self.queue.put(data))
    self.default_parsers[event_type.upper()](data['data'])"""


class RTShardFrameWork(discord.AutoShardedClient):
    def __init__(self, *args, logging_level=logging.DEBUG,
                 port=3000, **kwargs):
        # ログの出力を設定する。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("RT - Client")

        # その他色々設定する。
        super().__init__(*args, **kwargs)
        self.requests = DiscordRequests(self)

        # Event Injection
        self.default_parsers = copy(self._connection.parsers)
        for parser_name in self._connection.parsers:
            parser_name_lowered = parser_name.lower()
            exec(ON_SOME_EVENT.replace("!event_type!", parser_name_lowered))
            self._connection.parsers[parser_name] = eval(parser_name_lowered)
        globals()["self"] = self

        # Workerの初期設定をする。
        self.queue = asyncio.Queue()
        self.logger.info("Creating websockets server.")
        server = websockets.serve(self.worker, "localhost", str(port))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server)
        self.logger.info("Started websockets server!")

    async def worker(self, ws, path):
        while True:
            queue = self.queue.get_nowait()
            if isinstance(queue, asyncio.QueueEmpty):
                try:
                    data = await asyncio.wait_for(ws.recv(), timeout=0.01)
                except asyncio.TimeoutError:
                    continue
                else:
                    # Workerに何かリクエストされた場合はそれを実行する。
                    callback_data = {
                        "type": "ok",
                        "data": None
                    }
                    if data["type"] == "discord":
                        # Discordに何かリクエストするやつ。
                        args = data["data"].get("args", [])
                        kwargs = data["data"].get("kwargs", {})
                        do_wait = data["data"].get("wait", True)
                        try:
                            coro = getattr(self.requests, data["data"]["type"])
                        except AttributeError:
                            callback_data["type"] = "ok but error"
                            callback_data["data"] = (f"{data['data']['type']}"
                                                     + "が見つかりませんでした。")
                        else:
                            try:
                                if do_wait:
                                    callback_data["data"] = await coro(
                                        *args, **kwargs)
                                else:
                                    asyncio.create_task(
                                        coro(*args, **kwargs))
                            except Exception:
                                callback_data["type"] = "error"
                                callback_data["data"] = format_exc()
                        # コールバックを送信する。
                        await ws.send(dumps(callback_data))
            else:
                # もしイベントが呼び出されたらイベントをWorkerに伝える。
                data = {
                    "type": "start",
                    "data": queue,
                    "me": self.user.id
                }
                await ws.send(dumps(data))
                loads(await ws.recv())
                self.queue.task_done()
