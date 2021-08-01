# rtlib - Backend

from typing import Union, Optional, Callable, Any

from discord.ext import commands
from copy import copy
import sanic

from .web_manager import WebManager
from . import libs


class Mixer:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BackendBase(Mixer):
    def __init__(self, *args, on_init_bot: Callable[
                    [object], Any] = lambda bot: None,
                 name: str = "rt.backend", log: bool = True,
                 web_manager_kwargs: dict = {},
                 **kwargs):
        self._on_init_bot: Callable[[object], Any] = on_init_bot
        self.name: str = name
        self.log: bool = log

        # デフォルトのcloseをこちらが用意したcloseにオーバーライドする。
        self._default_close: Callable = copy(self.close)
        self.close: Callable = self._close_backend
        # sanicとdiscord.pyのセットアップをする。
        self.web: sanic.Sanic = sanic.Sanic(name)
        self.__args, self.__kwargs = args, kwargs

        # Routeなど色々セットアップする。
        self.web.register_listener(self._before_server_stop,
                                   "before_server_stop")
        self.web.register_listener(self._after_server_start,
                                   "after_server_start")
        self.web.add_route(self._hello_route, "/hello")
        self.web_manager = WebManager(self, **web_manager_kwargs)

    def print(self, *args, title: Optional[str] = None, **kwargs) -> None:
        """簡単にログ出力をするためのもの。

        Parameters
        ----------
        *args
            `print`に渡す引数です。
        title : Optional[str], default None
            ログのタイトルです。  
            デフォルトはBackendの定義時に引数であるnameに渡した文字列が使用されます。""" # noqa
        if self.log:
            if title is None:
                title = self.name
            print(f"[{title}]", *args, **kwargs)

    async def _on_ready(self):
        self.print("Connected to discord.")

    async def _before_server_stop(self, _, __):
        await self._default_close()

    async def _after_server_start(self, _, loop):
        # discord.pyをセットアップする。
        self.__kwargs["loop"] = loop
        super().__init__(*self.__args, **self.__kwargs)
        self.add_listener(self._on_ready, "on_ready")
        self._on_init_bot(self)
        # Botに接続する。
        loop.create_task(self.start(self.__token, reconnect=self.__reconnect))

    async def _hello_route(self, _):
        return sanic.response.text("Hi, I'm" + self.user.name + ".")

    def run(self, token: str, *args, reconnect: bool = True, **kwargs) -> None:
        """BackendをDiscordに接続させて動かします。

        Parameters
        ----------
        token : str
            接続するBotのtokenです。  
        *args
            `sanic.Sanic.run`に渡す引数です。
        reconnect : bool, default True
            接続したBotから切断された際に再接続をするかどうかです。
        **kwargs
            `sanic.Sanic.run`に渡すキーワード引数です。""" # noqa
        self.__token, self.__reconnect = token, reconnect
        self.print("Connecting to discord and running sanic...")
        self.web.run(*args, **kwargs)
        self.print("Bye")

    async def _close_backend(self) -> None:
        # discord.pyのクライアントのcloseにオーバーライドする関数です。
        self.web.stop()


class Backend(BackendBase, commands.Bot):
    """`sanic.Sanic`と`discord.ext.commands.Bot` をラップしたクラスです。  
    `discord.ext.commands.Bot`を継承しています。  
    sanicによるウェブサーバーとDiscordのBotを同時に手軽に動かすことができます。

    Notes
    -----
    このクラスの定義時に`rtlib.WebManager`も定義されます。  
    もしウェブサイトを同時に立てたい場合はそちらのクラスのリファレンスも読みましょう。  
    デフォルトの設定ではアクセスされた際は`templates`フォルダにあるファイルを返すようになっています。

    Parameters
    ----------
    *args
        `discord.ext.commands.Bot`に渡す引数です。
    on_init_bot : Callable[[object], Any], default lambda bot:None
        `discord.ext.commands.Bot`の定義後に呼び出されます。  
        sanicとの兼用をするのにこのBackend定義時に定義することができないためこれがあります。  
        なのでもし`load_extension`などを使う際はそれを実行する関数をここに入れてください。  
        ここに渡した関数は呼ばれる際にBackendのインスタンスが渡されます。
    name : str, default "rt.backend"
        `sanic.Sanic`の引数nameに渡すものです。  
        また、Backend内にあるログ出力機能でのタイトルにデフォルトで使用されます。
    log : bool, default True
        ログをコンソールに出力するかどうかです。
    web_manager_kwargs : Union[list, tuple], default ()
        このクラスの定義時にウェブサーバーの管理に便利な`rtlib.WebManager`を定義します。  
        その`rtlib.WebManager`の定義時に渡すキーワード引数です。
    **kwargs
        `discord.ext.commands.Bot`に渡すキーワード引数です。

    Attributes
    ----------
    web : sanic.Sanic
        `sanic.Sanic`のインスタンス、ウェブサーバーです。 

    Examples
    --------
    import rtlib

    def on_init(bot):
        bot.load_extension("cogs.music")
        bot.load_extension("on_full_reaction")

        @bot.event
        async def on_full_reaction_add(payload):
           print(payload.message.content)

    bot = rtlib.Backend(commands_prefix=">", on_init_bot=on_init)

    bot.run("TOKEN")""" # noqa
    pass

class AutoShardedBackend(BackendBase, commands.AutoShardedBot):
    """Backendの自動シャード版です。  
    `discord.ext.commands.Bot`ではなく`discord.ext.commands.AutoShardedBot`を継承しています。  
    引数など説明は基本Backendと同じです。"""
    pass
