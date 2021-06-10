# RT - Shard 

import discord

from sanic.response import file, html, json, redirect
from sanic.exceptions import abort
from sanic import Sanic

from jinja2 import Environment, FileSystemLoader, select_autoescape
from flask_misaka import Misaka

from typing import Union, Tuple, List
from traceback import format_exc
from ujson import loads, dumps
from os.path import exists
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
    self._default_parsers[event_type.upper()](data['data'])"""


class RTBackend(discord.AutoShardedClient):
    """
    Workerとの通信をするバックエンドのクラスです。

    Parameters
    ----------
    *args : tuple, optional
        親クラスのdiscord.AutoShardedClientに渡す引数です。
    logging_level : int, default logging.ERROR
        loggingのレベルです。
    port : int, default 3000
        Workerとの通信に使うWebsocketのポートです。
    **kwargs : dict, optional
        親クラスのdiscord.AutoShardedClientに渡すキーワード引数です。

    Attributes
    ----------
    logger
        loggingのloggerです。
    worker : list
        つないでいるWorkerのIDのリストです。
    """
    def __init__(self, *args, logging_level: int = logging.ERROR,
                 port: int = 3000, **kwargs):
        # ログの出力を設定する。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("rt.backend")

        # その他色々設定する。
        super().__init__(*args, **kwargs)
        self.workers = []
        self.requests = DiscordRequests(self)

        # Event Injection
        self.logger.info("Injecting the event queue putters to discord.py ...")
        self._default_parsers = copy(self._connection.parsers)
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
        server = websockets.serve(self._worker, "localhost", str(port))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server)
        self.logger.info("Complete!")

    async def _worker(self, ws, path):
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


    async def


class RTSanicServer(Sanic):
    """
    Sanicを使用したウェブサーバーです。

    Parameters
    ----------
    name : str, default __name__
        ウェブサーバーの名前です。

    Attributes
    ----------
    app : sanic.Sanic
        Sanicです。
    """

    DEFAULT_EXTS = (".html", ".xml", ".tpl")

    def __init__(self, ws_host: str, ws_port: int, *args, name: str = __name__,
                  support_exts: Union[List[str], Tuple[str]] = DEFAULT_EXTS,
                  folder: str = "templates",
                  flask_misaka: dict = {"autolink": True, "wrap": True},
                  **kwargs):
        super().__init__(name)
        self.events = []

        # Jinja2 Template Engine, Flask-Misaka
        self.env = Environment(
            loader=FileSystemLoader("static/website/html"),
            autoescape=select_autoescape(support_exts),
            enable_async=True
        )
        self.env.filters.setdefault(
            "markdown", Misaka(autolink=True, wrap=True).render)

        # 通信の準備をする。
        self.ws, self._ready = None, asyncio.Event()
        self.queue = asyncio.Queue()
        self.worker_count = 0
        self.support_exts = support_exts
        self.__setup_route(ws_host, ws_port)

    def event(self, coro, event_name: str = None):
        """
        WebServerのイベント登録用のデコレータです。

        Parameters
        -----------
        coro : Callable
            登録するイベントのコルーチンです。　
        event_name : str, default None
            登録するイベントの種類です。
        """
        def _decorator(coro):
            self.add_event(coro, event_name=event_name)
            return coro
        return _decorator

    def add_event(self, coro, event_name: str = None):
        """
        WebServerのイベント登録用関数です。
        イベント例：`on_before_return`

        Parameters
        -----------
        coro : Callable
            登録するイベントのコルーチンです。　
        event_name : str, default None
            登録するイベントの種類です。
        """
        coro.__event_name = event_name if event_name else coro.__name__
        self.events.append(coro)

    async def template(self, tpl, **kwargs):
        """
        Jinja2テンプレートエンジンです。

        Parameters
        -----------
        tpl : str
            使うテンプレート(ファイル)のパスです。
        **kwargs : dict, default {}
            テンプレートで交換するものを入れます。
        """
        template = self.env.get_template(tpl)
        content = await template.render_async(kwargs)
        return html(content)

    def __setup_route(self, host: str, port: int):
        @self.websocket("/webserver")
        async def backend(request, ws):
            self.ws = ws
            if not self.worker_count:
                self._ready.set()
            self.worker_count += 1
            while True:
                data = await self.queue.get()
                await ws.send(dumps(data))
            self.worker_count -= 1
            if not self.worker_count:
                self._ready.clear()

        @self.route("/<path:path>")
        async def return_file(self, request, path: str):
            if path.endswith(self.support_exts):
                if exists(path):
                    return await self.template(path)
                else:
                    return abort(404)
            else:
                data = {
                    "content_type": request.content_type,
                    "ip": request.ip,
                    "host": request.host,
                    "port": request.port,
                    "url": request.url,
                    "uri": path
                }
                self.queue.put(data)

    async def wait_until_ready(self):
        """
        Websocketのサーバーに一つでもWorkerが接続している状態になるまで待ちます。
        """
        await self._ready.wait()
