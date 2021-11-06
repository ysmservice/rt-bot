# RT Lib - WebSocket

from typing import (
    TYPE_CHECKING, Callable, Coroutine, TypedDict, Literal, Iterator,
    Union, Optional, Any, Tuple, Dict
)

from discord.ext import commands

from inspect import iscoroutinefunction
from ujson import loads, dumps
import websockets

if TYPE_CHECKING:
    from .typed import RT


WEBSOCKET_URI_BASE = "ws://localhost"


def _set_websocket_data(func, uri, event_type="on_connect", kwargs={}):
    if not uri.startswith(("ws://", "wss://")):
        uri = f"{WEBSOCKET_URI_BASE}{uri if uri[0] == '/' else f'/{uri}'}"
    func._websocket = (uri, event_type, kwargs)
    return func


def websocket(uri: str, auto_connect: bool = False, **kwargs) -> Callable:
    """WebSocket通信を行いたいコルーチン関数に付けるデコレータです。

    Examples
    --------
    ```python
    @websocket("/wstest", auto_connect=False)
    async def ws_test(self, ws: WebSocket, _):
        await ws.send("print", "From bot")
        await ws.send("ping")

    @ws_test.event("ping")
    async def ping(self, ws: WebSocket, data: PacketData):
        print("From backend:", data)

    @commands.command()
    async def start(self, ctx: commands.Context):
        await ctx.trigger_typing()
        await ctx.reply("...")
    ```"""
    if auto_connect:
        kwargs["auto_connect"] = auto_connect
    def decorator(func, uri=uri):
        func = _set_websocket_data(func, uri, kwargs=kwargs)

        def _event(event_type: str) -> Callable:
            def decorator(func):
                func = _set_websocket_data(func, uri, event_type)
                return func
            return decorator

        func.event = _event
        return func
    return decorator


PacketData = Union[str, dict]
class Packet(TypedDict):
    "WebSocketで通信するデータの辞書の型です。"
    event_type: str
    data: PacketData


class WebSocket:
    """簡単にWebSocketの通信をするためのクラスです。  
    これを使うなら`websocket`のデコレータをコグの関数に付けてください。  
    もし`ws://...`を省略した場合は自動で`WEBSOCKET_URI_BASE`(`ws://localhost`)が最初に付けられます。"""

    uri: str
    event_handlers: Dict[str, Callable[..., Coroutine]]
    cog: commands.Cog
    running: Literal["ok", "closed", "error"] = "ok"
    ws: websockets.WebSocketClientProtocol

    def __new__(
        cls, cog: commands.Cog, uri: str,
        event_handlers: Dict[str, Callable[..., Coroutine]], **kwargs
    ) -> Tuple["WebSocket", Coroutine]:
        self = super().__new__(cls)
        self.uri, self.event_handlers, self._kwargs = uri, event_handlers, kwargs
        self.cog = cog
        return self, self._connect()

    def print(self, *args, **kwargs) -> None:
        "ログ出力をします。"
        self.cog.bot.print(
            f"[{self.cog.__cog_name__}]", f"[WebSocket:{self.uri}]", *args, **kwargs
        )

    async def run_event(self, event_type: str, *args, **kwargs) -> Any:
        "WebSocketに登録されているイベントハンドラを実行します。内部で使用されています。"
        return await self.event_handlers[event_type](self, *args, **kwargs)

    async def _connect(self):
        # WebSocketに接続して通信を開始する。
        self.ws = await websockets.connect(
            self.uri, **self._kwargs
        )
        del self._kwargs
        # 接続した際にもし「on_connect」があるならそれを実行する。
        if "on_connect" in self.event_handlers:
            await self.run_event("on_connect", {})
        # メインの通信を開始する。
        while not self.cog.bot.is_closed():
            data = await self.recv()

            if data["event_type"] in self.event_handlers:
                # イベントハンドラを実行してもしデータを返されたならそれを送り返す。
                if (return_data := await self.run_event(
                    data["event_type"], data["data"])
                ):
                    await self.send(data["event_type"], return_data)
            else:
                # もしイベントが見つからなかったのならWebSocketを切断する。
                self.print(
                    f"Disconnected from bot because bot gave me an event that dosen't exists : {data['event_type']}"
                )
                await self.close(1003, "そのイベントが見つかりませんでした。")

    async def send(self, event_type: str, data: PacketData = "") -> None:
        "データを送信します。"
        await self._wrap_error(
            self.ws.send(dumps({"event_type": event_type, "data": data}))
        )

    async def recv(self) -> Optional[Packet]:
        "データを受信します。もし切断された場合は何も返されません。"
        if (data := await self._wrap_error(self.ws.recv())):
            return loads(data)

    async def _wrap_error(self, coro: Coroutine) -> Any:
        # コルーチンを接続エラーをラップして実行する関数です。
        try:
            data = await coro
        except websockets.ConnectoinClosedOK:
            self.running = "closed"
        except websockets.ConnectionClosedError:
            self.running = "error"
            self.print("Disconnected from websocket by some error")
        else:
            return data

    def is_closed(self) -> bool:
        "WebSocketが閉じているかどうかを確認します。"
        return self.running != "ok"

    async def close(self, code: int = 1000, reason: str = ""):
        "WebSocket通信を終了します。"
        self.running = "ok" if code in (1000, 1001) else "error"
        await self.ws.close(code, reason)


class WebSocketManager(commands.Cog):
    def __init__(self, bot: "RT"):
        self.bot = bot

    def websockets(self, cog: commands.Cog) -> Iterator[Callable[..., Coroutine]]:
        # コグにあるWebSocketの関数をひとつづつ取り出す。
        for name in dir(cog):
            if (iscoroutinefunction(func := getattr(cog, name))
                    and hasattr(func, "_websocket")):
                yield func

    @commands.Cog.listener()
    async def on_cog_add(self, cog: commands.Cog):
        # コグが追加された際にwebsocketデコレータが付いている関数をまとめる。
        websockets = {}
        for func in self.websockets(cog):
            uri, event_type, kwargs = func._websocket
            if uri not in cog.websockets:
                websockets[uri] = {}
            websockets[uri][event_type] = func
            if kwargs:
                cog.websocket_kwargs = kwargs
        else:
            # 見つけたWebSocketの関数の通信を開始する。
            for uri in websockets:
                websocket, coro = WebSocket(
                    cog, uri, websockets[uri],
                    getattr(cog, "websocket_kwargs", {}).get(uri, {})
                )
                cog.bot.loop.create_task(coro)
                # コグの関数からWebSocketにアクセスするためにコグに保存しておく。
                if not hasattr(cog, "websockets"):
                    cog.websockets = {}
                cog.websockets[uri] = websocket
            del websockets

    @commands.Cog.listener()
    async def on_cog_remove(self, cog: commands.Cog):
        # もしコグが削除された際にそのコグにWebSocketの関数があるなら通信を終了させる。
        for func in self.websockets(cog):
            if hasattr(func, "_websocket"):
                await cog.websockets[func._websocket[0]].close(
                    reason="コグの削除による切断です。"
                )
        else:
            if hasattr(cog, "websockets"):
                del cog.websockets


def setup(bot):
    bot.add_cog(WebSocketManager(bot))