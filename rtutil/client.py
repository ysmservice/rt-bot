
# RT - Shard

import discord
from discord.ext import commands

from traceback import format_exc
from ujson import loads, dumps
from os import cpu_count
import asyncio

from sanic import Sanic

from .d import DiscordFunctions


class RTShardClient(commands.AutoShardedBot, Sanic):
    def __init__(self, *args, **kwargs):
        # 独自のkwargsを取得しておく。
        self.worker_count = kwargs.get("worker_count", cpu_count())
        self.print_error = kwargs.get("print_error", True)
        self.print_log = kwargs.get("log", False)
        sanic_args = kwargs.get("sanic_args", [])
        sanic_kwargs = kwargs.get("sanic_kwargs", {})

        # ログの出力を設定する。
        self.TITLES = {
            "rw": "RT - Websocket",
            "rc": "RT - Client"
        }
        self._print = ((lambda title, text:
                       print(f"[{self.TITLES[title]}] {text}"))
                       if self.print_log else lambda title, text: "")

        super().__init__(*args, **kwargs)
        self.dfs = DiscordFunctions(self)

        sanic_kwargs["loop"] = self.loop
        self.sanic = Sanic(*sanic_args, **sanic_kwargs)
        self.setup_websocket()

    def setup_websocket(self):
        self.queue = asyncio.Queue()

        @self.sanic.websocket("/worker")
        async def worker(self, request, ws):
            while True:
                data = loads(await ws.recv())
                new_data = {}

                # 正しい形式にデータがなっているか確認する。
                if ("event_type" in data and "args" in data
                        and "kwargs" in data):
                    # Discordに通信したいとWorkerに言われたらeventsから正しいのをとって通信する。
                    if data["event_type"] == "discord":
                        if data["args"]:
                            coro = getattr(events, data["args"][0], None)
                            await coro(*data["args"][1:], **data["kwargs"])
                            new_data = {
                                "event_type": "Ok",
                                "args": [],
                                "kwargs": {},
                                "key": data["key"]
                            }

                await ws.send(dumps(new_data))

        @self.sanic.websocket("/worker_listen")
        async def worker_listen(self, request, ws):
            # on_messageなどのイベントが呼び出された時にWorkerに通知する。
            while True:
                queue = await self.queue.get()
                data = {}

                if len(queue) == 2:
                    queue = queue + [{}]
                new_data = {
                    "event_type": queue[0],
                    "args": queue[1],
                    "kwargs": queue[2]
                }

                await ws.send(dumps(new_data))
                callback = loads(await ws.recv())
                if callback["event_type"]["error"]:
                    print(callback["kwargs"])

    async def on_message(self, message):

