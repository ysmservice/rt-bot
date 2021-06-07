# RT - Shard

import discord

from traceback import format_exc
from ujson import loads, dumps
from random import randint
from time import time
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

    async def do_requests(self, data):
        # 依頼されたリクエストを処理する。。
        callback_data = {
            "type": "ok",
            "key": data["key"],
            "data": None
        }
        args = data["data"].get("args", [])
        kwargs = data["data"].get("kwargs", {})
        do_wait = data["data"].get("wait", True)
        try:
            coro = getattr(self.requests, data["data"]["type"])
        except Exception:
            # エラー時はコールバックにエラー内容を書き込んでおく。
            callback_data["data"] = format_exc()
            callback_data["type"] = "error"
        else:
            # 実行する。
            if do_wait:
                callback_data["data"] = await coro(
                    *args, **kwargs)
            else:
                asyncio.create_task(
                    coro(*args, **kwargs))

        # コールバックの取得のためのキューリストにコールバックを追加する。
        return callback_data

    async def worker_request(self, ws, path):
        # workerからのリクエストをリクエストキューに入れるためのwebsocket。
        self.request_ws = ws
        LOG_TITLE = "(Worker Request Thread) "
        while True:
            self.logger.info(LOG_TITLE + "Waiting worker's request...")
            data = loads(await ws.recv())
            self.logger.info(LOG_TITLE + "Received worker's request!")

            self.logger.info(LOG_TITLE + "Do worker's request.")
            if data["type"] == "discord":
                callback_data = await self.do_request(data)

            self.logger.info(LOG_TITLE + "Send callback_data to worker.")
            await ws.send(dumps(callback_data))

    async def worker(self, ws, path):
        while True:
            self.logger.info("Waiting event...")
            queue = await self.queue.get()
            self.logger.info("Received event!")

            # イベントでそのイベントでのWorkerとの通信が始まる。
            data = {
                "type": "start",
                "data": queue,
                "me": self.user.id
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
                            pass
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
                if isinstance(error, str):
                    self.logger.debug(error)
                    channel = self.get_channel(842744343911596062)
                    content = "\n```\n" + error + "\n```"
                    content = "すみませんが処理中にエラーが発生したようです。" + content
                    await channel.send(content)

            # 通信を終わらせたという合図を送信する。
            callback_data = {
                "type": "end",
                "data": {}
            }
            await ws.send(dumps(callback_data))

            self.logger.info("End event communication.")
