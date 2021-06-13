# RT - Shard 

import discord
from sanic import Sanic, response

from sanic.exceptions import abort

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
                 host: str = "localhost", port: int = 3000, **kwargs):
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
        server = websockets.serve(self._worker, host, str(port))
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


class RTSanicServer:
    """
    Sanicを使用したウェブサーバーです。
    これはとても便利です。
    Workerとの通信をするのでWorkerがルーティングを取得することができます。
    デフォルトでは`templates`にあるhtml,xml,tplのファイルを返すことができます。
    しかもJinja2テンプレートエンジンを搭載し、マークダウンも使用することができます。
    マークダウンはファイルに`{{ % filter markdown % }}`から
    `{{ % endfilter % }}`と囲んだところが自動的に装飾されます。

    Parameters
    ----------
    *args : Union[list, tuple], default ()
        ウェブサーバーのベースであるsanic.Sanicに渡す下のname以外の引数です。
    name : str, default __name__
        ウェブサーバーの名前です。
    ws_uri : str, default "/webserver"
        Workerとの通信に使うWebsocketのアドレスです。
    template_exts: Union[List[str], Tuple[str]], default (".html", ".xml")
        テンプレートエンジンを使用して返すファイルのリストです。
    folder : str, default "templates"
        返すことのできるファイルがあるフォルダのパスです。
        例としてhello.htmlがあったとします。
        それがfolderのパスのフォルダにあるとします。
        その場合`http://アドレス/hello.html`でこのファイルは返されます。
        これの返すことのできるファイルのリストは上のsupport_extsに渡されるリストです。
        **Warning!!**
        TOKENが記載されているファイルがあるフォルダーを設定してしまうとTOKEN流出の恐れがあります。
    max_length : int, default 100
        扱うことのできるuriの長さです。
    flask_misaka : dict, default {"autolink": True, "wrap": True}
        テンプレートエンジンで使うことのできるフィルターの`markdown`での追加設定です。
        何の追加設定に対応しているかはflask-misakaを参照してください。
    logging_level : int, default logging.ERROR
        loggingのレベルです。
    **kwargs : dict, default {}
        ウェブサーバーんぼベースであるsanic.Sanicに渡すキーワード引数です。

    Attributes
    ----------
    app : sanic.Sanic
        Sanicです。
    folder : str
        返すことのできるファイルがあるフォルダのパスです。
    logger
        loggingのloggerです。
    stop : bool
        停止するかしないかです。
    wss : dict
        接続しているWebsocketGatewayの辞書です。
        {"ID": {"ws": WebsocketGateway, "queue": queue_count}}
    """

    DEFAULT_EXTS = (".html", ".xml")

    def __init__(self, name: str, *args, ws_uri: str = "/webserver",
                 template_exts: Union[List[str], Tuple[str]] = DEFAULT_EXTS,
                 folder: str = "templates",
                 max_length: int = 100,
                 flask_misaka: dict = {"autolink": True, "wrap": True},
                 logging_level: int = logging.ERROR,
                 **kwargs):
        self.app = Sanic(name, *args, **kwargs)
        self.folder = folder
        self.max_length = max_length

        self.logger = logging.getLogger("rt.web")
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )

        # Jinja2 Template Engine, Flask-Misaka
        self.env = Environment(
            loader=FileSystemLoader(folder),
            autoescape=select_autoescape(template_exts),
            enable_async=True
        )
        self.env.filters.setdefault(
            "markdown", Misaka(autolink=True, wrap=True).render)

        # 通信の準備をする。
        self.wss, self._ready = {}, asyncio.Event()
        self.stop = False
        self.support_exts = template_exts
        self.__setup_route(ws_uri)

    async def request(self, data: dict) -> dict:
        """
        接続しているWorkerにRTSanicServerから処理のリクエストします。
        ルーティングされているURLが開かれた際などに使われています。
        **普通は使いません。内部で使用しているものです。**

        Parameters
        -----------
        data : dict
            渡すもの。

        Returns
        -------
        callback : dict
        """
        # Workerへルーティングなどの処理をリクエストする。
        if self.wss:
            self.logger.info("Requesting...")
            # 一番リクエストのキューが少ないとされるWorkerにリクエストを実行する。
            before = -1
            now = None
            for number in self.wss:
                if self.wss[number]["queue"] < before or before == -1:
                    before = self.wss[number]["queue"]
                    now = number
            self.wss[now]["queue"] += 1
            # リクエストするWorkerに
            self.logger.info("  Selected worker " + now + ".")
            await self.wss[now]["ws"].send(dumps(data))
            self.logger.info("  Requested.")
            callback = loads(await self.wss[now]["ws"].recv())
            # リクエストのコールバックを返す。
            self.logger.info("Received! Done.")
            self.wss[now]["queue"] -= 1
            return callback
        else:
            BT = "まだ準備が完了していません。"
            return {
                "type": "end",
                "data": {
                    "type": "abort",
                    "args": [503, f"{BT}またはWorkerへの接続に失敗しています。"],
                    "kwargs": {}
                }
            }

    def __setup_route(self, ws_uri: str):
        app = self.app

        @app.websocket(ws_uri if ws_uri else "/")
        async def backend(request, ws):
            number = make_session_id()
            self.wss[number] = {
                "ws": ws,
                "queue": 0
            }
            self.logger.info("Connected worker. (" + number + ")")
            if not self.wss:
                self._ready.set()
            # Workerとのwebserver用の通信を時間を作る。
            while not self.stop or not self.wss.closed:
                await asyncio.sleep(0.01)
            self.logger.info("Finished worker. (" + number + ")")
            del self.wss[number]
            if not self.wss:
                self._ready.clear()

        @app.listener('after_server_stop')
        async def notify_server_stopping(app, loop):
            self.stop = True

        @app.route("/")
        async def return_index(request):
            if exists(self.folder + "/index.html"):
                return await self.template("index.html")

        @app.route("/<path:path>")
        async def return_file(request, path: str):
            if len(path) > self.max_length:
                return abort(414)
            # なにかアクセスがあったならそれに対応する対応をする。
            true_path = self.folder + "/" + path
            if path.endswith(self.support_exts):
                # もしファイルへのアクセスならファイルを返す。
                # ここで返すファイルは決められたファイルのみ。
                if exists(true_path):
                    return await self.template(path)
                else:
                    return abort(404)
            elif exists(true_path):
                # ファイルを返す。
                # ダウンロードなど。
                return await response.file(true_path)
            else:
                # もしファイル返却じゃない場合はWorkerにルーティング実行のリクエストをする。
                data = {
                    "type": "access",
                    "data": {
                        "content_type": request.content_type,
                        "ip": request.ip,
                        "host": request.host,
                        "port": request.port,
                        "url": request.url,
                        "uri": path
                    }
                }
                callback = await self.request(data)
                # コールバックがもしエラーならエラーの出力をする。
                if callback["type"] == "error":
                    callback["type"] = "text"
                    callback["args"] = ("エラーが発生したため処理を実行することができませんでした。: \n"
                                        + callback["data"],)
                    callback["kwargs"] = {}
                    print(callback["data"])
                else:
                    callback = callback["data"]
                # もしファイルやJSONなどを返すようにコールバックに書いてあるならその通りにする。
                if callback["type"] == "template":
                    res = self.template
                elif callback["type"] == "abort":
                    res = self.__abort
                else:
                    try:
                        res = getattr(response, callback["type"])
                    except AttributeError:
                        return abort(500, f"{callback['type']}は使用できません。")
                if asyncio.iscoroutinefunction(request):
                    return await res(
                        *callback["args"], **callback["kwargs"])
                else:
                    print(res)
                    return res(
                        *callback["args"], **callback["kwargs"])

    def __abort(self, status_code: int, message: str = None):
        return abort(status_code, message)

    async def template(self, tpl, **kwargs):
        """
        Jinja2テンプレートエンジンです。
        Worker側が使うために作られたものですがbackend側でも使えます。

        Parameters
        -----------
        tpl : str
            使うテンプレート(ファイル)のパスです。
        **kwargs : dict, default {}
            テンプレートで交換するものを入れます。
        """
        template = self.env.get_template(tpl)
        content = await template.render_async(kwargs)
        return response.html(content)

    async def wait_until_ready(self):
        """
        WorkerのWebsocketに一つでも接続している状態になるまで待ちます。
        """
        await self._ready.wait()
