# RT - Shard 

import discord

from traceback import format_exc
from ujson import loads, dumps
from copy import copy
import websockets
import asyncio
import logging

from .discord_requests import DiscordRequests
from .utils import make_session_id


ON_SOME_EVENT = """def !event_type!(data):
    event_type = '!event_type!'
    data = {"type": event_type, "data": data}
    guild_id = data["data"].get("guild_id")
    if guild_id:
        data["data"]["guild"] = self.requests.get_guild_noasync(guild_id)
    channel_id = data["data"].get("channel_id")
    if channel_id:
        data["data"]["channel"] = self.requests.get_channel_noasync(channel_id)
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
        self.logger = logging.getLogger("rt.backend")

        # その他色々設定する。
        super().__init__(*args, **kwargs)
        self.workers: List[int] = []
        self.requests: DiscordRequests = DiscordRequests(self)

        # Event Injection
        self.logger.info("Injecting the event queue putters to discord.py ...")
        self.default_parsers = copy(self._connection.parsers)
        for parser_name in self._connection.parsers:
            self.logger.info("  " + parser_name)
            parser_name_lowered = parser_name.lower()
            exec(ON_SOME_EVENT.replace("!event_type!", parser_name_lowered))
            self._connection.parsers[parser_name] = eval(parser_name_lowered)
        globals()["self"] = self
        self.logger.info("Injected putters")

        # Workerの初期設定をする。
        self.queue = asyncio.Queue()
        self.logger.info("Creating websockets server.")
        server = websockets.serve(self.worker, "localhost", str(port))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server)
        self.logger.info("Complete!")

    async def worker(self, ws, path):
        number = make_session_id()
        self.workers.append(number)
        while True:
            try:
                queue = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            else:
                # もしイベントが呼び出されたらイベントをWorkerに伝える。
                self.logger.info("Received event.")
                data = {
                    "type": "start",
                    "data": queue,
                    "me": self.user.id
                }
                data = dumps(data)
                await ws.send(data)
                self.logger.debug("  Backend > " + data)
                self.logger.info("Sended event to worker!")
                self.queue.task_done()
            try:
                data = loads(await asyncio.wait_for(ws.recv(), timeout=0.01))
            except asyncio.TimeoutError:
                pass
            except websockets.exceptions.ConnectionClosedOK:
                pass
            else:
                # Workerに何かリクエストされた場合はそれを実行する。
                callback_data = {
                    "type": "ok",
                    "data": None
                }
                if data["type"] == "request":
                    # Discordに何かリクエストするやつ。
                    args = data["data"].get("args", [])
                    kwargs = data["data"].get("kwargs", {})
                    do_wait = data["data"].get("wait", True)
                    try:
                        coro = getattr(self.requests, data["data"]["type"])
                    except AttributeError:
                        event_type = data['data']['type']
                        if event_type == "get_worker_number":
                            callback_data["data"] = {
                                "id": number,
                                "index": self.workers.index(number)
                            }
                        else:
                            callback_data["type"] = "error"
                            callback_data["data"] = f"{event_type}が見つかりませんでした。"
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
            await asyncio.sleep(0.01)
        self.workers.remove(number)
