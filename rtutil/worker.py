# RT - Worker

from typing import Union, Tuple, List
from importlib import import_module
from traceback import format_exc
from websockets import connect
from ujson import loads, dumps
import logging
import asyncio

from .converter import add_converter
from .errors import NotConnected, NotFound


def if_connected(function):
    async def _function(self, *args, **kwargs):
        if self.ws:
            return await function(self, *args, **kwargs)
        else:
            raise NotConnected("まだWebSocketに接続できていないので処理を実行できません。")
    return _function


class Worker:
    """
    Workerのインスタンスを作成します。

    Parameters
    ----------
    prefixes: Union[str, Tuple[str], List[str]]
        Botが反応するコマンドの接頭詞です。
        接頭詞の例：`prefixes="rt!"` -> `rt!help` に反応する。
        tupleかリストを使うことで複数の接頭詞を設定することができます。
    loop: asyncio.ProactorEventLoop, default None
        使うイベントループを指定することができます。
        デフォルトではasyncio.get_event_loop()によって取得されます。
        普通に使う場合は指定しなくてもよいです。
    logging_level: int, default logging.ERROR
        loggingのレベルを設定します。
        デフォルトではlogging.ERRORになっています。
        普通は変えなくても良いです。
    print_extension_name: Union[bool, str], default False
        エクステンションのロード時にロードしたエクステンションの名前をprintするかです。
        文字列を入れるとその文字列 + 名前でprintされます。
    ignore_me: bool, default True
        自分(Bot自身)のメッセージを無視するかどうかです。
    retry_connect : int, default 5
        Workerとの通信に使うWebsocketが理由なしに切断された際に接続しなおす回数です。
        デフォルトでは五回です。

    Attributes
    ----------
    events : Dict[str, List[Callable]]
        登録されているイベント一覧の辞書です。
    commands : Dict[str, Callable]
        登録されているコマンド一覧の辞書です。
    cogs : Dict[str, object]
        登録されているコグ一覧の辞書です。
    extensions : Dict[str, object]
        登録されているエクステンション一覧の辞書です。
    routes : Dict[str, Callable]
        登録されているルーティング一覧の辞書です。
    ws
        動いているWorkerが親のBackendと通信に使っているWebsocketのGatewayです。
        DiscordからのイベントをBackendから受け取ったりなどしたりします。
    web_ws
        動いているWorkerがRTSanicServerと通信に使っているWebsocketのGatewayです。
    prefixes : tuple
        Botの接頭詞のタプルです。
    """
    def __init__(self, prefixes: Union[List[str], Tuple[str], str], *,
                 loop=None, logging_level: int = logging.ERROR,
                 print_extension_name: bool = False, ignore_me: bool = True,
                 retry_connect: int = 3):
        self.print_extension_name = print_extension_name
        self.ignore_me = ignore_me

        self.loop = loop if loop else asyncio.get_event_loop()
        self.events = {}
        self.commands = {}
        self.cogs = {}
        self.extensions = {}
        self.routes = {}

        self.ws, self.web_ws = None, None
        self._number = None
        self.queue = asyncio.Queue()
        self._event = asyncio.Event()
        self._request = asyncio.Event()
        self._ready = asyncio.Event()
        self._web_ready = asyncio.Event()
        self._request_queue_count = 0

        # プリフィックスを設定する。
        if isinstance(prefixes, list):
            self.prefixes = tuple(prefixes)
        elif isinstance(prefixes, tuple):
            self.prefixes = prefixes
        elif isinstance(prefixes, str):
            self.prefixes = (prefixes,)
        else:
            raise TypeError("プリフィックスはタプルかリストか文字列にする必要があります。")

        # ログ出力の設定をする。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("rt.worker")

        # コマンドフレームワークのコマンドを走らせるためにon_messageイベントを登録しておく。
        self.add_event(self.__on_message, "message_create")

        super().__init__()

    def run(self, web: bool = False,
            ws_url: str = "ws://localhost/webserver"):
        """
        Workerを起動させます。

        Parameters
        ----------
        web : bool, default False
            RTSanicServerを動かしている場合のみ使用してください。
            これはWebServerと連携するかどうかです。
        host : str, default "ws://localhost/webserver"
            RTSanicServerのWebsocketに設定しているhostを入れてください。
            特にhostを設定していない場合はデフォルトのままで大丈夫です。
        port : int, default 80
            RTSanicServerのWebsocketに設定しているportを入れてください。
            特にportを設定していない場合はデフォルトのままで大丈夫です。
        """
        self.logger.info("Starting worker...")
        try:
            self.loop.run_until_complete(
                asyncio.gather(
                    self.webserver(ws_url),
                    self.worker(),
                    return_exceptions=True
                )
            )
        except KeyboardInterrupt:
            pass
        finally:
            self.loop.stop()
            self.loop.close()
        self.logger.info("Worker is closed by user KeyboardInterrupt!")

    async def close(self):
        """
        Workerを正常に停止させます。
        """
        self.logger.info("Closing worker...")
        await self.ws.close(reason="Don't worry, It is true end!")
        if self.web_ws:
            await self.web_ws.close(reason="Don't worry, It is true end!")
        self.logger.info("  Websocket is closed.")
        self.loop.stop()
        self.loop.close()
        self.logger.info("  Loop is closed.")
        self.logger.info("Worker is closed.")

    async def webserver(self, ws_url: str):
        """
        RTSanicServerと通信をするプログラムです。
        普通はこれを呼び出しません。
        なのでこの説明は無視してもかまいません。
        これを呼び出す場合はrunをキーワード引数にweb=Trueと設定して実行してください。

        See Also
        --------
        run : Workerを起動させます。
        """
        self.web_logger = logging.getLogger("rt.web")
        connect_count = 0
        while True:
            self.web_logger.info("Connecting to RTSanicServer websocket...")
            try:
                connect_count += 1
                ws = await connect(ws_url)
                self.web_ws = ws
                self._web_ready.set()
                while True:
                    self.web_logger.info("Waiting event...")
                    data = loads(await ws.recv())
                    try:
                        self.web_logger.info("  Received event!\n  Sending callback.")
                        callback = {
                            "type": "end",
                            "data": await self.run_route(data["type"], data)
                        }
                    except Exception:
                        callback = {
                            "type": "error",
                            "data": format_exc()
                        }
                    await ws.send(dumps(callback))
                    self.web_logger.info("Finished event.")
            except websockets.exceptions.ConnectionClosedOK:
                self.web_logger.warning("Broken Websocket Gateway")
            except ConnectionRefusedError:
                self.web_logger.warning("Broken Websocket Gateway")
            finally:
                if ws.close_reason:
                    break
                else:
                    self.web_logger.warning("Reconnect after 3 seconds...")
                    await asyncio.sleep(3)
        self.web_logger.info("Closed websocket.")

    async def run_route(self, uri: str, data: dict = {}):
        """
        指定されたuriのルーティングを実行します。

        Parameters
        ----------
        uri : str
            実行するルーティングのuriです。
        data : dict, default {}
            ルーティングに渡すデータです。
        """
        # 一致するルーティングを探す。
        splited = iter(uri.split("/"))
        for key in self.routes:
            args, kwargs, ok = [], {}, True
            self.web_logger.debug("~ " + key + " ~")
            for value in key.split("/"):
                if value:
                    if value[0] == "<" and value[-1] == ">":
                        # もし<>に囲まれているならその部分を引数に追加する。
                        args.append(value[1:-1])
                    elif value[0] == "?":
                        # クエリパラメータをキーワード引数に入れる。
                        i = value.find("=")
                        kwargs[value[1:i]] = value[i + 1:]
                    elif not value == next(splited):
                        # 一致しないところがあるならルーティングが違うということでやめる。
                        ok = False
                        break
                else:
                    break
            if ok:
                return await self.routes[key](data, *args)
        return None

    def route(self, coro, uri: str = "/"):
        """
        ルーティングを設定しURLとコルーチンを紐づけるデコレ―タです。

        Parameters
        ----------
        coro : Callable
            紐づけるコルーチンです。
        uri : str, default "/"
            ルーティングで設定するuriです。

        Examples
        --------
        @worker.route("/ping")
        async def ping(data):
            return worker.web("template", path="pong.html")
        """
        def _route(coro):
            self.add_route(coro, uri)
            return coro
        return _route

    def add_route(self, coro, uri: str = "/"):
        """
        ルーティングを設定しURLとコルーチンを紐づける関数です。

        Parameters
        ----------
        coro : Callable
            紐づけるコルーチンです。
        uri : str, default "/"
            ルーティングで設定するuriです。
        """
        self.routes[uri] = coro

    def remove_route(self, uri: str):
        """
        登録したルーティングを削除します。

        Parameters
        ----------
        uri : str
            削除するルーティングのuriです。
        """
        del self.routes[uri]

    def web(self, event_type: str, *args: tuple, **kwargs: dict) -> dict:
        """
        RTSanicServerに返すコールバックを楽に作るためのものです。

        Parameters
        ----------
        event_type : str
            コールバックの種類を入れます。
        **kwargs : dict, default {}
            コールバックに入れる引数です。

        Returns
        -------
        data : dict
            引数にそって作ったコールバックデータです。

        Examples
        --------
        @worker.route("/ping")
        async def index(self, data):
            return worker.web("json", {"code": "pong!"})
        """
        data = {"type": event_type}
        data.update({"args": args, "kwargs": kwargs})
        return data

    async def worker(self):
        """
        Workerのプログラムです。
        普通はこれを呼びだしません。
        なのでこの説明は無視してかまいません。
        Workerを動かす際はこれを呼び出すのではなくWorker.runを呼び出してください。

        See Also
        --------
        run : Workerを起動させます。
        """
        self.logger.info("Connecting to websocket...")
        # 親のDiscordからのイベントを受け取るmain.pyと通信をする。
        # イベントを受け取ったらそのイベントでの通信を開始する。
        ws = await connect("ws://localhost:3000")
        self.ws = ws
        self._ready.set()
        self.logger.info("Started worker.")
        while True:
            try:
                data = loads(await asyncio.wait_for(ws.recv(), timeout=0.01))
            except asyncio.TimeoutError:
                pass
            else:
                # イベント呼び出しならそれ専用のことをする。
                self.logger.info("Received event.")
                callback_data = {
                    "type": "ok",
                    "data": {}
                }
                try:
                    event_type = data['data']['type']
                    if (event_type in self.events
                            and data["type"] == "start"):
                        # 登録されているイベントを呼び出すものならそのイベントを呼び出す。
                        new_data = data["data"]["data"]
                        new_data["callback_template"] = callback_data
                        # イベントの実行をする。
                        self.logger.info(f"  Runnning {event_type} events...")
                        for coro in self.events[data["data"]["type"]]:
                            self.logger.info(f"    {coro.__name__}")
                            asyncio.create_task(coro(ws, new_data))
                        self.logger.info("Runned events.")
                except Exception:
                    error = format_exc()
                    callback_data["type"] = "error"
                    callback_data["data"] = error
                    self.logger.error("Exception in event:\n" + error)
            if self._request_queue_count != 0:
                self._request.clear()
            self._event.set()
            await self._request.wait()
            await asyncio.sleep(0.01)

    @if_connected
    async def me(self, n: int = 0) -> bool:
        """
        指定した番号が動いてるWorkerの番号と一致するか確かめます。
        1つだけのWorkerにだけやらせたい処理などに使えます。
        discord.ext.tasksと兼用する際などを使う際が特に便利です。
        実行にはwebsocketsの準備ができている必要があります。

        Examples
        --------
        # 動いてるWorkerが0番目のWorkerか確認する。
        if await worker.me(0):
            # 0番目のWorkerのみにやらせたい処理。
            # いわば1つのWorkerにのみやらせたい処理。

        Parameters
        ----------
        n: int, default 0
            Workerがn番目に動いているか確認します。
            未指定で0となります。

        Returns
        -------
        n_is_worker_index: bool
            Workerがn番目に動いているかを示すbool値。

        Raises
        -------
        rtutil.NotConnected
            Websocketの準備ができてない際に発生します。
        """
        return (await self.number())["index"] == n

    @if_connected
    async def number(self) -> dict:
        """
        動いているWorkerの番号を取得とIDを取得します。
        実行にはwebsocketsの準備ができている必要があります。

        Returns
        --------
        number: dict
            {
                "id": "WorkerのID",
                "index": "Workerの番号"
            }

        Raises
        -------
        rtutil.NotConnected
            Websocketの準備ができてない際に発生します。
        """
        return await self.discord("get_worker_number")

    @if_connected
    async def discord(self, event_type: str, *args, wait=True, **kwargs):
        """
        Discordにリクエストを送信します。
        ※Discordに限ることではありません。
        event_typeの例としてはメッセージを送信するsendやステータス変更のchange_presenceなどがあります。
        使えるリクエストはrtutil.discord_requests.DiscordRequests。
        実行にはwebsocketsの準備ができている必要があります。

        Parameters
        -----------
        event_type : str
            何をするかです。
        *args : tuple, optional
            そのイベントに渡す引数です。
        wait : bool, default True
            コールバックを待つかどうかです。
            時間をかかる処理をリクエストする際にリクエストの結果を取得しない場合などに使えます。
            デフォルトではTrueで待ちます。
            例えばメッセージを送る際にメッセージの情報が普通コールバックとして返されます。
            その時別にメッセージの情報などいらんという場合に、wait=Falseにすることで無駄な待機時間をなくすことができます。
        **kwargs : dict, optional
            そのイベントに渡すキーワード引数です。

        Returns
        --------
        callback : Any
            リクエスト結果です。
            例えばメッセージ送信をリクエストした場合は送ったメッセージの情報が返されます。
            引数であるwaitにFalseを入れた場合は何も返されません。

        Examples
        ---------
        await worker.discord("send", channel["id"], テストメッセージ")
        # channelにテストメッセージが送信される。

        Raises
        -------
        rtutil.NotConnected
            Websocketの準備ができてない際に発生します。
        """
        self.logger.info(f"Requesting {event_type} ...")
        self._request_queue_count += 1
        await self._event.wait()
        # Discordに何かリクエストしてもらう。
        self.logger.info("  Sending request to backend...")
        data = {
            "type": "request",
            "data": {
                "type": event_type,
                "args": args,
                "kwargs": kwargs
            }
        }
        if "wait" in kwargs:
            wait = kwargs["wait"]
            data["data"]["wait"] = wait
            del kwargs["wait"]
        await self.ws.send(dumps(data))
        self.logger.info("    Sended request.")
        data = loads(await self.ws.recv())
        self.logger.info("  Received request callback.")
        self.logger.debug("    Worker < " + str(data))
        if data["type"] == "error":
            raise Exception(" in request:\n" + data["data"])
            self.logger.error("The request failed.")
        self._request.set()
        self._event.clear()
        self._request_queue_count -= 1
        self.logger.info("Requested " + event_type + "!")
        return data["data"]

    async def wait_until_ready(self):
        """
        Websocketの準備が整うまで待ちます。
        """
        await self._ready.wait()

    def event(self, event_name: str = None):
        """
        イベントを登録するためのデコレータです。
        コルーチンにつけます。
        イベントの例としてmessage_create(メッセージ送信)などがああります。

        Parameters
        ------------
        event_name : str, default None
            取得するイベントの名前です。
            デフォルトではNoneで指定しない場合はコルーチンの名前が使われます。

        Examples
        ---------
        @worker.event("message_create")
        async def on_message(ws, message):
            print(message["content"])
            # YEEEEEEAAAAAAHHHHH
        """
        # イベント登録用のデコレ―タ。
        def _event(coro):
            self.add_event(coro, event_name)
        return _event

    def add_event(self, coro, event_name: str = None):
        """
        動作内容はデコレータのeventと同じです。
        これはデコレータじゃないバージョンです。

        Parameters
        -----------
        coro : Callable
            イベントを登録するコルーチンです。
        event_name : str, default None
            取得するイベントの名前です。
            デフォルトではNoneで指定しない場合は渡されたコルーチンの名前が使われます。

        Examples
        ---------
        async def on_message(ws, message):
            print(message["content"])
            # お前はもう死んでいる。
        worker.add_event(on_message, "message_create")

        Raises
        -------
        TypeError
            登録しようとしているイベントがコルーチン出ない場合発生します。
        """
        # イベント登録用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンである必要があります。")
        event_name = event_name if event_name else coro.__name__
        if event_name not in self.events:
            self.events[event_name] = []
        self.events[event_name].append(coro)
        self.logger.info(f"Added event {event_name}.")

    def remove_event(self, coro, event_name: str = None):
        """
        イベントで登録されているコルーチンをイベント呼び出しリストから削除します。
        いわゆるadd_eventの逆です。

        Raises
        -------
        ValueError
            登録されていないイベントを指定された際に発生します。
        TypeError
            削除しようとしているイベントがコルーチン出ない場合発生します。
        """
        # イベント削除用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("削除するイベントはコルーチンである必要があります。")
        event_name = event_name if event_name else coro.__name__
        if event_name in self.events:
            i = -1
            for check_coro in self.events[event_name]:
                i += 1
                if check_coro == coro:
                    del self.events[event_name][i]
                    self.logger.info(f"Removed event {event_name}.")
                    return
        raise ValueError("そのコルーチンはイベントとして登録されていません。")

    def run_event(self, event_name: str, data: dict, ws=None):
        """
        イベントを実行します。

        Parameters
        ----------
        event_name : str
            実行するイベントの名前です。
        data : dict
            イベントに渡すデータです。
        ws, default Worker.ws
            イベントに渡すWebsocketGatewayです。
            デフォルトはDiscord用です。
        """
        for coro in self.events.get(event_name, []):
            asyncio.create_task(coro(ws if ws else self.ws, data))

    async def run_event_with_wait(self, event_name: str, data: dict, ws=None):
        """
        イベントを実行します。
        実行が終了するまで待ちます。

        Parameters
        ----------
        event_name : str
            実行するイベントの名前です。
        data : dict
            イベントに渡すデータです。
        ws, default Worker.ws
            イベントに渡すWebsocketGatewayです。
            デフォルトはDiscord用です。
        """
        for coro in self.events.get(event_name, []):
            await coro(ws if ws else self.ws, data)

    def command(self, command_name: str = None):
        """
        コマンドを登録します。

        Parameters
        -----------
        command_name : str, default None
            コマンド名です。
            デフォルトはNoneで未指定の場合コマンドとして登録するコルーチンの名前が使われます。

        Examples
        ---------
        @worker.command()
        async def help(ws, data, ctx):
            await ctx.send("yey")
        """
        # コマンド登録用のデコレ―タ。
        def _command(coro):
            # converter.pyにあるやつでコンバーターをコマンドのコルーチンに追加する。
            self.add_command(coro, command_name)
        return _command

    def add_command(self, coro, command_name: str = None):
        """
        動作内容はcommandと同じです。
        デコレータではありません。

        Parameters
        -----------
        coro : Callable
            コマンドを登録するコルーチンを入れます。
        command_name : str, default None
            追加するコマンドの名前を入れます。
            デフォルトは渡されたコルーチンの名前です。

        Examples
        ---------
        async def help(ws, data, ctx):
            await ctx.send("yey")
        add_command(help)

        Notes
        -----
        これを実行すると独自イベントの`on_command_add`が呼び出されます。
        これの引数であるdataには`{"coro": coro, "name": command_name}`が渡されます。
        """
        # コマンド登録用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するコマンドはコルーチンである必要があります。")
        command_name = command_name if command_name else coro.__name__
        self.commands[command_name] = coro
        # コマンド作成イベントを実行する。
        self.run_event(
            "on_command_add", {"coro": coro, "name": command_name})
        self.logger.info(f"Added command {command_name}")

    def remove_command(self, command_name):
        """
        add_commandの逆です。
        コマンドを名前指定で削除します。

        Parameters
        -----------
        command_name : Union[str, Callable]
            削除するコマンドの名前を入れます。
            コマンドとして登録されているコルーチンを入れた場合は、そのコルーチンの名前が使われます。

        Notes
        -----
        これを実行すると独自イベントの`on_command_remove`が呼び出されます。
        これの引数であるdataには`{"name": command_name}`が渡されます。
        """
        # コマンド削除用の関数。
        if asyncio.iscoroutine(command_name):
            command_name = command_name.__name__
        del self.commands[command_name]
        self.run_event(
            "on_command_remove", {"name": command_name})
        self.logger.info(f"Removed command {command_name}")

    async def process_commands(self, ws, data: dict):
        """
        コマンドを走らせます。
        デフォルトでイベントである`message_create`呼び出し時にこれは実行されます。
        ですので普通は使わないです。

        Parameters
        -----------
        ws
            動いているWorkerのWebsocketGatewayです。
        data : dict
            イベントの`message_create`で取得できるデータです。

        Returns
        --------
        command_name : Union[str, None]
            実行されるコマンド名です。
            もしコマンドではないのなら`None`が返されます。
        """
        # コマンドを走らせる。
        if data["content"].startswith(self.prefixes):
            for command_name in self.commands:
                for prefix in self.prefixes:
                    start = prefix + command_name
                    if data["content"].startswith(start):
                        # コマンドの準備をする。
                        # 引数を取り出してからコンバーターをコマンドのプログラムにつけて実行する。
                        args = self.parse_args(
                            data["content"].replace(start, ""))
                        cmd = add_converter(
                            self.commands[command_name], ws, data, None, *args)
                        asyncio.create_task(cmd)
                        return command_name

    async def __on_message(self, ws, data):
        await self.process_commands(ws, data)

    def parse_args(self, content: str) -> list:
        """
        渡された文字列を引数のリストにして返します。
        `"`で囲めば空白も一つの引数に含まれます。

        Parameters
        -----------
        content : str
            引数を取り出す元となる文字列です。

        Returns
        --------
        args : List[str]
            取り出した引数のリストです。
        """
        # 引数を取り出す。
        args, raw_arg = [], ""
        now_split_char = False
        for c in content:
            if c in (" ", "　", "\t", "\n") and not now_split_char:
                if raw_arg:
                    args.append(raw_arg)
                    raw_arg = ""
            elif c in ("'", '"'):
                now_split_char = False if now_split_char else True
            else:
                raw_arg += c
        if raw_arg:
            args.append(raw_arg)
        return args

    def add_cog(self, cog_class):
        """
        コグを追加します。

        Parameters
        -----------
        cog_class : class
            追加するコグのクラスのインスタンスを入れます。
        """
        # コグを追加する。
        name = cog_class.__class__.__name__
        self.cogs[name] = cog_class
        self.logger.info("Added cog " + name)

    def remove_cog(self, name: str):
        """
        コグを削除します。

        Parameters
        -----------
        name : str
            削除するコグのクラスの名前です。

        Raises
        -------
        rtutil.NotFound
            コグが見つからない場合発生します。
        """
        # コグを削除する。
        # この時コグで登録されたコマンドを削除しておく。
        if name in self.cogs:
            for command_name in self.commands:
                cog_name = getattr(
                    "__cog_name", "ThisIsNotCogYeahAndImTasuren_-")
                if cog_name == name:
                    self.remove_command(command_name)
            cog_unload = getattr(self.cogs[name], "cog_unload", None)
            if cog_unload:
                cog_unload()
            del self.cogs[name]
            self.logger.info("Removed cog " + name)
        else:
            raise NotFound(f"{name}というコグが見つからないためコグの削除ができません。")

    def load_extension(self, path: str):
        """
        エクステンションをロードします。

        Parameters
        -----------
        path : str
            読み込むエクステンションのパスです。
        """
        # エクステンションのロードをする。
        path = path.replace("/", ".").replace(".py", "")
        self.extensions[path] = import_module(path)
        return_data = self.extensions[path].setup(self)
        text = "Loaded extension " + path
        if self.print_extension_name:
            if isinstance(self.print_extension_name, str):
                text = self.print_extension_name + path
            print(text)
        self.logger.info(text)
        return return_data

    def unload_extension(self, path: str):
        """
        エクステンションをアンロードします。

        Parameters
        -----------
        path : str
            アンロードするエクステンションのパスです。
        """
        # エクステンションのアンロードをする。
        # アンロードする前にコグを外しておく。
        if path in self.extensions:
            for key in self.cogs:
                if self.cogs[key].get_filename() == path:
                    self.remove_cog(key)
            del self.extensions[path]
            self.logger.info("Unloaded extension " + path)
        else:
            raise NotFound(f"{path}のエクステンションが見つからないためアンロードすることができません。")

    def reload_extension(self, path: str):
        """
        指定されたエクステンションをリロードします。

        Parameters
        -----------
        path : str
            リロードするエクステンションのパスです。
        """
        # エクステンションをリロードする。
        self.unload_extension(path)
        self.load_extension(path)
        self.logger.info("Reloaded extension " + path)

    def reload_all_extensions(self):
        """
        読み込んでいるエクステンションのすべてをリロードします。
        """
        # 全てのエクステンションをリロードする。
        for path in [path for path in self.extensions]:
            # 内包表記でわざわざリストにしているのは反復中にself.extensionsに変更が入るから。
            self.unload_extension(path)
            self.load_extension(path)
        self.logger.info("Reloaded all extensions")


if __name__ == "__main__":
    worker = Worker()
    worker.run()
